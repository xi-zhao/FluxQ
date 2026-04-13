"""Typer-based CLI entrypoint for Quantum Runtime."""

from __future__ import annotations

from pathlib import Path

import typer

from quantum_runtime import __version__
from quantum_runtime.diagnostics import run_structural_benchmark
from quantum_runtime.diagnostics.benchmark import BenchmarkReport, persist_benchmark_report
from quantum_runtime.errors import WorkspaceConflictError, WorkspaceRecoveryRequiredError
from quantum_runtime.qspec import QSpec
from quantum_runtime.runtime import (
    ComparePolicy,
    ImportReference,
    ImportResolution,
    ImportSourceError,
    build_execution_plan,
    intent_resolution_from_prompt,
    ReportImportError,
    resolve_runtime_object,
    schema_contract,
    show_run,
    compare_import_resolutions,
    compare_workspace_baseline,
    persist_compare_result,
    execute_intent,
    execute_intent_json,
    execute_intent_text,
    execute_qspec,
    execute_report,
    export_artifact,
    export_artifact_from_resolution,
    inspect_workspace,
    inspect_pack_bundle,
    pack_revision,
    list_backends,
    resolve_import_reference,
    resolve_workspace_baseline,
    run_doctor,
    workspace_status,
)
from quantum_runtime.runtime.policy import BenchmarkPolicy, apply_benchmark_policy
from quantum_runtime.runtime.contracts import (
    ErrorPayload,
    dump_schema_payload,
    ensure_schema_payload,
    remediation_for_error,
    workspace_conflict_error_payload,
    workspace_recovery_required_error_payload,
)
from quantum_runtime.runtime.exit_codes import (
    exit_code_for_benchmark,
    exit_code_for_compare,
    exit_code_for_control_plane,
    exit_code_for_doctor,
    exit_code_for_exec,
    exit_code_for_export,
    exit_code_for_inspect,
    exit_code_for_workspace_safety,
)
from quantum_runtime.runtime.observability import JsonlEvent
from quantum_runtime.runtime.observability import phase_for_event_type
from quantum_runtime.runtime.observability import (
    workspace_conflict_observability,
    workspace_recovery_required_observability,
)
from quantum_runtime.workspace import (
    WorkspaceBaseline,
    WorkspaceLockConflict,
    WorkspaceManager,
    WorkspaceManifest,
    WorkspacePaths,
    clear_workspace_baseline,
    save_workspace_baseline,
)


app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Deterministic quantum runtime CLI for agent hosts.",
)
backend_app = typer.Typer(add_completion=False, help="Backend discovery helpers.")
baseline_app = typer.Typer(add_completion=False, help="Workspace baseline helpers.")
app.add_typer(backend_app, name="backend")
app.add_typer(baseline_app, name="baseline")


def _emit_json_payload(payload: object, *, exit_code: int) -> None:
    typer.echo(dump_schema_payload(payload))
    raise typer.Exit(code=exit_code)


def _json_error(reason: str) -> None:
    _emit_json_payload(
        ErrorPayload(
            reason=reason,
            error_code=reason,
            remediation=remediation_for_error(reason),
        ),
        exit_code=3,
    )


def _workspace_safety_payload(
    error: WorkspaceConflictError | WorkspaceRecoveryRequiredError,
) -> object:
    if isinstance(error, WorkspaceConflictError):
        observability = workspace_conflict_observability()
        return workspace_conflict_error_payload(
            workspace=str(error.details["workspace"]),
            lock_path=str(error.details["lock_path"]),
            holder=dict(error.details.get("holder", {})),
            reason_codes=list(observability["reason_codes"]),
            next_actions=list(observability["next_actions"]),
            gate=dict(observability["gate"]),
        )
    observability = workspace_recovery_required_observability()
    last_valid_revision = error.details.get("last_valid_revision")
    return workspace_recovery_required_error_payload(
        workspace=str(error.details["workspace"]),
        pending_files=[str(item) for item in error.details.get("pending_files", [])],
        last_valid_revision=str(last_valid_revision) if last_valid_revision is not None else None,
        reason_codes=list(observability["reason_codes"]),
        next_actions=list(observability["next_actions"]),
        gate=dict(observability["gate"]),
    )


def _handle_workspace_safety_error(
    error: WorkspaceConflictError | WorkspaceRecoveryRequiredError,
    *,
    json_output: bool,
    jsonl_output: bool = False,
    event_sink=None,
) -> None:
    payload = _workspace_safety_payload(error)
    exit_code = exit_code_for_workspace_safety(error.code)
    if json_output:
        _emit_json_payload(payload, exit_code=exit_code)
    if jsonl_output and event_sink is not None:
        event_sink(
            "run_completed",
            ensure_schema_payload(payload),
            status="error",
        )
        raise typer.Exit(code=exit_code)
    typer.echo(error.message)
    raise typer.Exit(code=exit_code)


def _echo_json(payload: object, *, exclude_none: bool = False) -> None:
    typer.echo(dump_schema_payload(payload, exclude_none=exclude_none))


def _validate_output_modes(*, json_output: bool, jsonl_output: bool) -> None:
    if json_output and jsonl_output:
        _json_error("output_mode_conflict")


def _make_jsonl_emitter(*, workspace: Path):
    workspace_str = str(workspace.resolve())

    def emit(event_type: str, payload: dict[str, object], revision: str | None = None, status: str = "ok") -> None:
        error_code = str(payload.get("error_code")) if isinstance(payload, dict) and payload.get("error_code") is not None else None
        event = JsonlEvent(
            event_type=event_type,
            phase=phase_for_event_type(event_type),
            workspace=workspace_str,
            revision=revision,
            status=status,
            error_code=error_code,
            remediation=remediation_for_error(error_code) if error_code is not None else None,
            payload=ensure_schema_payload(payload) if isinstance(payload, dict) and "status" in payload else payload,
        )
        typer.echo(event.model_dump_json())

    return emit


def _resolve_report_import(
    *,
    workspace: Path,
    report_file: Path | None,
    revision: str | None,
) -> ImportResolution | None:
    if report_file is None and revision is None:
        return None
    if report_file is not None and revision is not None:
        raise ReportImportError("report_source_conflict")

    reference = (
        ImportReference(workspace_root=workspace, report_file=report_file)
        if report_file is not None
        else ImportReference(workspace_root=workspace, revision=revision)
    )
    try:
        return resolve_import_reference(reference)
    except ImportSourceError as exc:
        if report_file is None or exc.code != "workspace_root_required_for_report_file":
            raise
        return resolve_import_reference(
            ImportReference(workspace_root=workspace, report_file=report_file)
        )


def _resolve_runtime_input(
    *,
    workspace: Path,
    report_file: Path | None,
    revision: str | None,
) -> ImportResolution:
    if report_file is None and revision is None:
        return resolve_import_reference(ImportReference(workspace_root=workspace))
    resolution = _resolve_report_import(
        workspace=workspace,
        report_file=report_file,
        revision=revision,
    )
    assert resolution is not None
    return resolution


def _default_benchmark_backends(qspec: QSpec) -> list[str]:
    resolved = ["qiskit-local"]
    requested = [str(name) for name in qspec.backend_preferences if name]

    backend_provider = qspec.constraints.backend_provider
    if backend_provider == "classiq":
        requested.append("classiq")
    if backend_provider == "qiskit":
        requested.append("qiskit-local")

    backend_name = qspec.constraints.backend_name
    if backend_name in {"classiq", "qiskit-local"}:
        requested.append(backend_name)

    for backend in requested:
        if backend not in resolved:
            resolved.append(backend)
    return resolved


def _benchmark_backends(qspec: QSpec, requested_backends: str | None) -> list[str]:
    if requested_backends is None:
        return _default_benchmark_backends(qspec)
    return [item.strip() for item in requested_backends.split(",") if item.strip()]


def _build_benchmark_policy(
    *,
    baseline_mode: bool,
    require_comparable: bool,
    forbid_status_regressions: bool,
    max_width_regression: int | None,
    max_depth_regression: int | None,
    max_two_qubit_regression: int | None,
    max_measure_regression: int | None,
) -> BenchmarkPolicy | None:
    policy_requested = baseline_mode or any(
        value
        for value in (
            require_comparable,
            forbid_status_regressions,
        )
    ) or any(
        value is not None
        for value in (
            max_width_regression,
            max_depth_regression,
            max_two_qubit_regression,
            max_measure_regression,
        )
    )
    if not policy_requested:
        return None
    if not baseline_mode:
        raise ValueError("benchmark policy requires --baseline in this phase")
    return BenchmarkPolicy.model_validate(
        {
            "baseline": baseline_mode,
            "require_comparable": require_comparable,
            "forbid_status_regressions": forbid_status_regressions,
            "max_width_regression": max_width_regression,
            "max_depth_regression": max_depth_regression,
            "max_two_qubit_regression": max_two_qubit_regression,
            "max_measure_regression": max_measure_regression,
        }
    )


def _load_saved_baseline_benchmark(*, workspace: Path, baseline_revision: str) -> BenchmarkReport:
    benchmark_path = workspace / "benchmarks" / "history" / f"{baseline_revision}.json"
    if not benchmark_path.exists():
        raise FileNotFoundError(str(benchmark_path))
    return BenchmarkReport.model_validate_json(benchmark_path.read_text())


@app.command("init")
def init_command(
    workspace: Path = typer.Option(
        Path(".quantum"),
        "--workspace",
        file_okay=False,
        dir_okay=True,
        writable=True,
        resolve_path=False,
        help="Workspace directory to initialize.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit a machine-readable JSON result.",
    ),
) -> None:
    """Initialize the workspace skeleton and default config."""
    existed = workspace.exists()
    result = WorkspaceManager.init_workspace(workspace)
    result.created = not existed
    if json_output:
        _echo_json(result)
        return

    typer.echo(f"Initialized workspace at {result.workspace}")


@app.command("version")
def version_command() -> None:
    """Print the package version."""
    typer.echo(__version__)


@app.command("prompt")
def prompt_command(
    text: str = typer.Argument(..., help="Natural-language prompt to normalize into a machine intent."),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit a machine-readable JSON result.",
    ),
) -> None:
    """Normalize a natural-language prompt without planning or execution."""
    try:
        result = intent_resolution_from_prompt(text)
    except ImportSourceError as exc:
        if json_output:
            _json_error(exc.code)
        raise typer.BadParameter(f"Invalid prompt input: {exc.code}") from exc
    if json_output:
        _echo_json(result)
        raise typer.Exit(code=0)

    typer.echo(result.intent.get("goal", ""))


@app.command("resolve")
def resolve_command(
    workspace: Path = typer.Option(
        Path(".quantum"),
        "--workspace",
        file_okay=False,
        dir_okay=True,
        writable=True,
        resolve_path=False,
        help="Workspace directory to inspect for defaults and baseline context.",
    ),
    intent_file: Path | None = typer.Option(
        None,
        "--intent-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=False,
        help="Markdown intent file to normalize.",
    ),
    intent_json_file: Path | None = typer.Option(
        None,
        "--intent-json-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=False,
        help="Structured JSON intent file to normalize.",
    ),
    qspec_file: Path | None = typer.Option(
        None,
        "--qspec-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=False,
        help="Serialized QSpec JSON file to normalize.",
    ),
    report_file: Path | None = typer.Option(
        None,
        "--report-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=False,
        help="Previously generated report JSON file to normalize.",
    ),
    revision: str | None = typer.Option(
        None,
        "--revision",
        help="Workspace report history revision to normalize.",
    ),
    intent_text: str | None = typer.Option(
        None,
        "--intent-text",
        "--prompt-text",
        help="Inline intent text to normalize.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit a machine-readable JSON result.",
    ),
) -> None:
    """Resolve runtime ingress into canonical intent, qspec, and plan objects."""
    try:
        result = resolve_runtime_object(
            workspace_root=workspace,
            intent_file=intent_file,
            intent_json_file=intent_json_file,
            qspec_file=qspec_file,
            report_file=report_file,
            revision=revision,
            intent_text=intent_text,
        )
    except ImportSourceError as exc:
        if json_output:
            _json_error(exc.code)
        raise typer.BadParameter(f"Invalid resolve input: {exc.code}") from exc
    except ReportImportError as exc:
        if json_output:
            _json_error(exc.reason)
        raise typer.BadParameter(f"Invalid resolve input: {exc.reason}") from exc
    except ValueError as exc:
        if json_output:
            _json_error(str(exc))
        raise typer.BadParameter(str(exc)) from exc

    if json_output:
        _echo_json(result)
        raise typer.Exit(code=exit_code_for_control_plane(result))

    typer.echo(
        f"resolve status: {result.status}; pattern={result.qspec.get('pattern', 'unknown')}; "
        f"workload_id={result.qspec.get('workload_id', 'unknown')}"
    )
    raise typer.Exit(code=exit_code_for_control_plane(result))


@app.command("plan")
def plan_command(
    workspace: Path = typer.Option(
        Path(".quantum"),
        "--workspace",
        file_okay=False,
        dir_okay=True,
        writable=True,
        resolve_path=False,
        help="Workspace directory to inspect for baseline and default export context.",
    ),
    intent_file: Path | None = typer.Option(
        None,
        "--intent-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=False,
        help="Markdown intent file to resolve into a dry-run plan.",
    ),
    intent_json_file: Path | None = typer.Option(
        None,
        "--intent-json-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=False,
        help="Structured JSON intent file to resolve into a dry-run plan.",
    ),
    qspec_file: Path | None = typer.Option(
        None,
        "--qspec-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=False,
        help="Serialized QSpec JSON file to inspect without execution.",
    ),
    report_file: Path | None = typer.Option(
        None,
        "--report-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=False,
        help="Previously generated report JSON file to re-import for planning.",
    ),
    revision: str | None = typer.Option(
        None,
        "--revision",
        help="Workspace report history revision to re-import for planning.",
    ),
    intent_text: str | None = typer.Option(
        None,
        "--intent-text",
        help="Inline intent text to normalize without executing it.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit a machine-readable JSON result.",
    ),
) -> None:
    """Resolve a runtime input into a dry-run execution plan."""
    try:
        result = build_execution_plan(
            workspace_root=workspace,
            intent_file=intent_file,
            intent_json_file=intent_json_file,
            qspec_file=qspec_file,
            report_file=report_file,
            revision=revision,
            intent_text=intent_text,
        )
    except ImportSourceError as exc:
        if json_output:
            _json_error(exc.code)
        raise typer.BadParameter(f"Invalid plan input: {exc.code}") from exc
    except ReportImportError as exc:
        if json_output:
            _json_error(exc.reason)
        raise typer.BadParameter(f"Invalid plan input: {exc.reason}") from exc
    except ValueError as exc:
        if json_output:
            _json_error(str(exc))
        raise typer.BadParameter(str(exc)) from exc

    if json_output:
        _echo_json(result)
        raise typer.Exit(code=exit_code_for_control_plane(result))

    typer.echo(
        f"plan status: {result.status}; pattern={result.qspec.get('pattern', 'unknown')}; "
        f"backends={','.join(result.execution.get('selected_backends', []))}"
    )
    raise typer.Exit(code=exit_code_for_control_plane(result))


@app.command("status")
def status_command(
    workspace: Path = typer.Option(
        Path(".quantum"),
        "--workspace",
        file_okay=False,
        dir_okay=True,
        readable=True,
        resolve_path=False,
        help="Workspace directory to summarize for agents and CI.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit a machine-readable JSON result.",
    ),
) -> None:
    """Return a thin workspace status summary."""
    result = workspace_status(workspace_root=workspace)
    if json_output:
        _echo_json(result)
        raise typer.Exit(code=exit_code_for_control_plane(result))
    typer.echo(
        f"status={result.status}; revision={result.current_revision or 'unknown'}; "
        f"latest_run={result.latest_run_status or 'missing'}"
    )
    raise typer.Exit(code=exit_code_for_control_plane(result))


@app.command("show")
def show_command(
    workspace: Path = typer.Option(
        Path(".quantum"),
        "--workspace",
        file_okay=False,
        dir_okay=True,
        readable=True,
        resolve_path=False,
        help="Workspace directory that provides the default latest run.",
    ),
    revision: str | None = typer.Option(
        None,
        "--revision",
        help="Specific workspace revision to show instead of the latest run.",
    ),
    latest: bool = typer.Option(
        True,
        "--latest/--no-latest",
        help="Show the latest workspace run when no revision is supplied.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit a machine-readable JSON result.",
    ),
) -> None:
    """Show one resolved run plus baseline relation details."""
    if revision is not None and not latest:
        if json_output:
            _json_error("show_source_conflict")
        raise typer.BadParameter("Use either --revision or --latest.")
    try:
        result = show_run(workspace_root=workspace, revision=revision if revision is not None else None)
    except ImportSourceError as exc:
        if json_output:
            _json_error(exc.code)
        raise typer.BadParameter(f"Invalid show input: {exc.code}") from exc

    if json_output:
        _echo_json(result)
        raise typer.Exit(code=exit_code_for_control_plane(result))

    typer.echo(
        f"revision={result.revision}; pattern={result.qspec_summary.get('pattern', 'unknown')}; "
        f"baseline_match={result.baseline_relation.get('matches_baseline')}"
    )
    raise typer.Exit(code=exit_code_for_control_plane(result))


@app.command("schema")
def schema_command(
    name: str = typer.Argument(..., help="One of: qspec, report, manifest, compare, plan, status."),
) -> None:
    """Return the JSON Schema for one public runtime contract."""
    try:
        result = schema_contract(name)
    except ValueError as exc:
        _json_error(str(exc))
    _echo_json(result)


@baseline_app.command("set")
def baseline_set_command(
    workspace: Path = typer.Option(
        Path(".quantum"),
        "--workspace",
        file_okay=False,
        dir_okay=True,
        writable=True,
        resolve_path=False,
        help="Workspace directory that contains the baseline target.",
    ),
    report_file: Path | None = typer.Option(
        None,
        "--report-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=False,
        help="Specific report file to persist as the workspace baseline.",
    ),
    revision: str | None = typer.Option(
        None,
        "--revision",
        help="Workspace report history revision to persist as the baseline.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit a machine-readable JSON result.",
    ),
) -> None:
    """Persist one runtime input as the workspace baseline."""
    try:
        resolution = _resolve_runtime_input(
            workspace=workspace,
            report_file=report_file,
            revision=revision,
        )
    except ImportSourceError as exc:
        if json_output:
            _json_error(exc.code)
        raise typer.BadParameter(f"Invalid baseline input: {exc.code}") from exc
    except ReportImportError as exc:
        if json_output:
            _json_error(exc.reason)
        raise typer.BadParameter(f"Invalid baseline input: {exc.reason}") from exc

    baseline = WorkspaceBaseline.from_import_resolution(resolution)
    try:
        save_workspace_baseline(workspace_root=workspace, baseline=baseline)
    except (WorkspaceConflictError, WorkspaceRecoveryRequiredError) as exc:
        _handle_workspace_safety_error(exc, json_output=json_output)

    if json_output:
        _echo_json(baseline)
        return

    typer.echo(f"Set workspace baseline to {baseline.revision}")


@baseline_app.command("show")
def baseline_show_command(
    workspace: Path = typer.Option(
        Path(".quantum"),
        "--workspace",
        file_okay=False,
        dir_okay=True,
        writable=True,
        resolve_path=False,
        help="Workspace directory that contains the persisted baseline.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit a machine-readable JSON result.",
    ),
) -> None:
    """Show the currently persisted workspace baseline."""
    paths = WorkspacePaths(root=workspace)
    baseline_path = paths.baseline_current_json
    if not baseline_path.exists():
        if json_output:
            _json_error("baseline_missing")
        typer.echo(f"No baseline set at {baseline_path}")
        raise typer.Exit(code=3)

    baseline = WorkspaceBaseline.load(baseline_path)
    if json_output:
        _echo_json(baseline)
        return

    typer.echo(f"Workspace baseline: {baseline.revision}")


@baseline_app.command("clear")
def baseline_clear_command(
    workspace: Path = typer.Option(
        Path(".quantum"),
        "--workspace",
        file_okay=False,
        dir_okay=True,
        writable=True,
        resolve_path=False,
        help="Workspace directory that contains the persisted baseline.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit a machine-readable JSON result.",
    ),
) -> None:
    """Clear the currently persisted workspace baseline."""
    try:
        baseline_path, cleared = clear_workspace_baseline(workspace_root=workspace)
    except (WorkspaceConflictError, WorkspaceRecoveryRequiredError) as exc:
        _handle_workspace_safety_error(exc, json_output=json_output)

    payload = {
        "status": "ok",
        "cleared": cleared,
        "path": str(baseline_path),
    }
    if json_output:
        _echo_json(payload)
        return

    typer.echo("Cleared workspace baseline." if cleared else "No baseline set.")


@app.command("bench")
def bench_command(
    workspace: Path = typer.Option(
        Path(".quantum"),
        "--workspace",
        file_okay=False,
        dir_okay=True,
        writable=True,
        resolve_path=False,
        help="Workspace directory that contains specs/current.json.",
    ),
    backends: str | None = typer.Option(
        None,
        "--backends",
        help="Comma-separated backend list for structural benchmarking. Defaults to qiskit-local plus backends requested by the active QSpec.",
    ),
    report_file: Path | None = typer.Option(
        None,
        "--report-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=False,
        help="Previously generated report JSON file to re-import for benchmarking.",
    ),
    revision: str | None = typer.Option(
        None,
        "--revision",
        help="Workspace report history revision to re-import for benchmarking.",
    ),
    baseline_mode: bool = typer.Option(
        False,
        "--baseline",
        help="Evaluate the current benchmark against the saved workspace baseline benchmark history.",
    ),
    require_comparable: bool = typer.Option(
        False,
        "--require-comparable",
        help="Fail benchmark policy when backend comparability metadata is false on either side.",
    ),
    forbid_status_regressions: bool = typer.Option(
        False,
        "--forbid-status-regressions",
        help="Fail benchmark policy when backend status regresses from the saved baseline.",
    ),
    max_width_regression: int | None = typer.Option(
        None,
        "--max-width-regression",
        min=0,
        help="Maximum allowed width increase relative to the saved baseline benchmark.",
    ),
    max_depth_regression: int | None = typer.Option(
        None,
        "--max-depth-regression",
        min=0,
        help="Maximum allowed depth increase relative to the saved baseline benchmark.",
    ),
    max_two_qubit_regression: int | None = typer.Option(
        None,
        "--max-two-qubit-regression",
        min=0,
        help="Maximum allowed two-qubit gate increase relative to the saved baseline benchmark.",
    ),
    max_measure_regression: int | None = typer.Option(
        None,
        "--max-measure-regression",
        min=0,
        help="Maximum allowed measurement-count increase relative to the saved baseline benchmark.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit a machine-readable JSON result.",
    ),
    jsonl_output: bool = typer.Option(
        False,
        "--jsonl",
        help="Emit newline-delimited machine-readable benchmark events.",
    ),
) -> None:
    """Run structural backend benchmarks against the current QSpec."""
    _validate_output_modes(json_output=json_output, jsonl_output=jsonl_output)
    try:
        handle = WorkspaceManager.load_or_init(workspace)
    except WorkspaceLockConflict as exc:
        _handle_workspace_safety_error(
            WorkspaceConflictError(
                workspace=workspace.resolve(),
                lock_path=Path(exc.lock_path),
                holder=exc.holder.model_dump(mode="json"),
            ),
            json_output=json_output,
            jsonl_output=jsonl_output,
        )
    try:
        policy = _build_benchmark_policy(
            baseline_mode=baseline_mode,
            require_comparable=require_comparable,
            forbid_status_regressions=forbid_status_regressions,
            max_width_regression=max_width_regression,
            max_depth_regression=max_depth_regression,
            max_two_qubit_regression=max_two_qubit_regression,
            max_measure_regression=max_measure_regression,
        )
    except Exception as exc:
        if json_output:
            _json_error("invalid_benchmark_policy")
        raise typer.BadParameter("Invalid benchmark policy.") from exc
    try:
        import_resolution = _resolve_report_import(
            workspace=handle.root,
            report_file=report_file,
            revision=revision,
        )
        if import_resolution is not None:
            qspec = import_resolution.load_qspec()
        else:
            qspec_path = handle.root / "specs" / "current.json"
            if not qspec_path.exists():
                if json_output:
                    _json_error("missing_qspec")
                raise typer.BadParameter(f"Missing QSpec at {qspec_path}")
            qspec = QSpec.model_validate_json(qspec_path.read_text())
    except ImportSourceError as exc:
        if json_output:
            _json_error(exc.code)
        raise typer.BadParameter(f"Invalid report input: {exc.code}") from exc
    except ReportImportError as exc:
        if json_output:
            _json_error(exc.reason)
        raise typer.BadParameter(f"Invalid report input: {exc.reason}") from exc

    source_kind = import_resolution.source_kind if import_resolution is not None else "workspace_current"
    source_revision = import_resolution.revision if import_resolution is not None else handle.manifest.current_revision
    requested_backends = _benchmark_backends(qspec, backends)

    baseline_resolution = None
    baseline_benchmark = None
    if policy is not None:
        try:
            baseline_resolution = resolve_workspace_baseline(handle.root)
            baseline_benchmark = _load_saved_baseline_benchmark(
                workspace=handle.root,
                baseline_revision=baseline_resolution.record.revision,
            )
        except ImportSourceError as exc:
            if json_output:
                _json_error(exc.code)
            raise typer.BadParameter(f"Invalid benchmark baseline: {exc.code}") from exc
        except FileNotFoundError as exc:
            if json_output:
                _json_error("baseline_benchmark_missing")
            raise typer.BadParameter(
                f"Missing saved baseline benchmark history for {baseline_resolution.record.revision}."
            ) from exc
        except Exception as exc:
            if json_output:
                _json_error("invalid_benchmark_policy")
            raise typer.BadParameter("Invalid saved baseline benchmark.") from exc

    event_sink = _make_jsonl_emitter(workspace=handle.root) if jsonl_output else None
    if event_sink is not None:
        event_sink(
            "benchmark_started",
            {"backends": requested_backends},
            source_revision,
            "ok",
        )
    try:
        benchmark = run_structural_benchmark(
            qspec,
            handle,
            requested_backends,
            event_sink=event_sink,
            source_kind=source_kind,
            source_revision=source_revision,
        )
    except (WorkspaceConflictError, WorkspaceRecoveryRequiredError) as exc:
        _handle_workspace_safety_error(exc, json_output=json_output, jsonl_output=jsonl_output, event_sink=event_sink)

    if policy is not None:
        assert baseline_resolution is not None
        assert baseline_benchmark is not None
        benchmark = apply_benchmark_policy(
            report=benchmark,
            baseline_report=baseline_benchmark,
            baseline_revision=baseline_resolution.record.revision,
            policy=policy,
        )

    try:
        persist_benchmark_report(
            workspace_root=handle.root,
            report=benchmark,
            revision=benchmark.source_revision,
        )
    except (WorkspaceConflictError, WorkspaceRecoveryRequiredError) as exc:
        _handle_workspace_safety_error(exc, json_output=json_output, jsonl_output=jsonl_output, event_sink=event_sink)

    if json_output:
        _echo_json(benchmark)
        raise typer.Exit(code=exit_code_for_benchmark(benchmark))
    if event_sink is not None:
        event_sink(
            "benchmark_completed",
            benchmark.model_dump(mode="json"),
            benchmark.source_revision,
            benchmark.status,
        )
        raise typer.Exit(code=exit_code_for_benchmark(benchmark))

    verdict_status = None
    if isinstance(benchmark.verdict, dict):
        verdict_status = benchmark.verdict.get("status")
    if verdict_status and verdict_status != "not_requested":
        typer.echo(f"Benchmark status: {benchmark.status}; verdict={verdict_status}")
    else:
        typer.echo(f"Benchmark status: {benchmark.status}")
    raise typer.Exit(code=exit_code_for_benchmark(benchmark))


@app.command("export")
def export_command(
    workspace: Path = typer.Option(
        Path(".quantum"),
        "--workspace",
        file_okay=False,
        dir_okay=True,
        writable=True,
        resolve_path=False,
        help="Workspace directory that contains specs/current.json.",
    ),
    output_format: str = typer.Option(
        ...,
        "--format",
        help="One of: qiskit, qasm3, classiq-python.",
    ),
    profile: str | None = typer.Option(
        None,
        "--profile",
        help="Named export profile such as qiskit-native or qasm3-generic.",
    ),
    report_file: Path | None = typer.Option(
        None,
        "--report-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=False,
        help="Previously generated report JSON file to re-import for export.",
    ),
    revision: str | None = typer.Option(
        None,
        "--revision",
        help="Workspace report history revision to re-import for export.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit a machine-readable JSON result.",
    ),
) -> None:
    """Re-export one artifact from the current workspace QSpec."""
    try:
        import_resolution = _resolve_report_import(
            workspace=workspace,
            report_file=report_file,
            revision=revision,
        )
        if import_resolution is not None:
            result = export_artifact_from_resolution(
                workspace_root=workspace,
                resolution=import_resolution,
                output_format=output_format,
                profile=profile,
            )
        else:
            qspec_path = workspace / "specs" / "current.json"
            if not qspec_path.exists():
                if json_output:
                    _json_error("missing_qspec")
                raise typer.BadParameter(f"Missing QSpec at {qspec_path}")
            result = export_artifact(workspace_root=workspace, output_format=output_format, profile=profile)
    except ImportSourceError as exc:
        if json_output:
            _json_error(exc.code)
        raise typer.BadParameter(f"Invalid report input: {exc.code}") from exc
    except ReportImportError as exc:
        if json_output:
            _json_error(exc.reason)
        raise typer.BadParameter(f"Invalid report input: {exc.reason}") from exc
    except (WorkspaceConflictError, WorkspaceRecoveryRequiredError) as exc:
        _handle_workspace_safety_error(exc, json_output=json_output)

    if json_output:
        _echo_json(result)
        raise typer.Exit(code=exit_code_for_export(result))

    typer.echo(result.path or result.reason or result.status)
    raise typer.Exit(code=exit_code_for_export(result))


@app.command("pack")
def pack_command(
    workspace: Path = typer.Option(
        Path(".quantum"),
        "--workspace",
        file_okay=False,
        dir_okay=True,
        writable=True,
        resolve_path=False,
        help="Workspace directory that contains the revision to pack.",
    ),
    revision: str | None = typer.Option(
        None,
        "--revision",
        help="Workspace revision to package. Defaults to the current revision.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit a machine-readable JSON result.",
    ),
) -> None:
    """Package one revision into a portable runtime bundle."""
    try:
        if revision is not None:
            target_revision = revision
        else:
            paths = WorkspacePaths(root=workspace)
            if paths.workspace_json.exists():
                target_revision = WorkspaceManifest.load(paths.workspace_json).current_revision
            else:
                target_revision = WorkspaceManager.load_or_init(workspace).manifest.current_revision
        result = pack_revision(workspace_root=workspace, revision=target_revision)
    except WorkspaceLockConflict as exc:
        _handle_workspace_safety_error(
            WorkspaceConflictError(
                workspace=workspace.resolve(),
                lock_path=Path(exc.lock_path),
                holder=exc.holder.model_dump(mode="json"),
            ),
            json_output=json_output,
        )
    except (WorkspaceConflictError, WorkspaceRecoveryRequiredError) as exc:
        _handle_workspace_safety_error(exc, json_output=json_output)
    if json_output:
        _echo_json(result)
        raise typer.Exit(code=0 if result.status == "ok" else 3)
    typer.echo(result.pack_root)
    raise typer.Exit(code=0 if result.status == "ok" else 3)


@app.command("pack-inspect")
def pack_inspect_command(
    pack_root: Path = typer.Option(
        ...,
        "--pack-root",
        file_okay=False,
        dir_okay=True,
        readable=True,
        resolve_path=False,
        help="Pack bundle directory to inspect.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit a machine-readable JSON result.",
    ),
) -> None:
    """Inspect a portable runtime bundle for required files."""
    inspection = inspect_pack_bundle(pack_root)
    if json_output:
        _echo_json(inspection)
        raise typer.Exit(code=0 if inspection.status == "ok" else 3)
    typer.echo(f"pack inspection: {inspection.status}")
    raise typer.Exit(code=0 if inspection.status == "ok" else 3)


@app.command("exec")
def exec_command(
    workspace: Path = typer.Option(
        Path(".quantum"),
        "--workspace",
        file_okay=False,
        dir_okay=True,
        writable=True,
        resolve_path=False,
        help="Workspace directory to initialize or reuse.",
    ),
    intent_file: Path | None = typer.Option(
        None,
        "--intent-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=False,
        help="Markdown intent file to execute.",
    ),
    intent_json_file: Path | None = typer.Option(
        None,
        "--intent-json-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=False,
        help="Structured JSON intent file to execute.",
    ),
    qspec_file: Path | None = typer.Option(
        None,
        "--qspec-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=False,
        help="Serialized QSpec JSON file to execute.",
    ),
    report_file: Path | None = typer.Option(
        None,
        "--report-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=False,
        help="Previously generated report JSON file to re-import and execute.",
    ),
    revision: str | None = typer.Option(
        None,
        "--revision",
        help="Workspace report history revision to re-import and execute.",
    ),
    intent_text: str | None = typer.Option(
        None,
        "--intent-text",
        help="Inline intent text to execute directly.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit a machine-readable JSON result.",
    ),
    jsonl_output: bool = typer.Option(
        False,
        "--jsonl",
        help="Emit newline-delimited machine-readable events instead of a single JSON payload.",
    ),
) -> None:
    """Execute an intent file through the deterministic runtime pipeline."""
    _validate_output_modes(json_output=json_output, jsonl_output=jsonl_output)
    inputs_provided = sum(
        value is not None
        for value in (intent_file, intent_json_file, qspec_file, report_file, revision, intent_text)
    )
    if inputs_provided != 1:
        if json_output:
            _json_error("expected_exactly_one_input")
        raise typer.BadParameter(
            "Provide exactly one of --intent-file, --intent-json-file, --qspec-file, --report-file, --revision, or --intent-text."
        )

    try:
        event_sink = _make_jsonl_emitter(workspace=workspace) if jsonl_output else None
        if intent_file is not None:
            if event_sink is not None:
                result = execute_intent(workspace_root=workspace, intent_file=intent_file, event_sink=event_sink)
            else:
                result = execute_intent(workspace_root=workspace, intent_file=intent_file)
        elif intent_json_file is not None:
            if event_sink is not None:
                result = execute_intent_json(
                    workspace_root=workspace,
                    intent_json_file=intent_json_file,
                    event_sink=event_sink,
                )
            else:
                result = execute_intent_json(
                    workspace_root=workspace,
                    intent_json_file=intent_json_file,
                )
        elif report_file is not None or revision is not None:
            import_resolution = _resolve_report_import(
                workspace=workspace,
                report_file=report_file,
                revision=revision,
            )
            assert import_resolution is not None
            if event_sink is not None:
                result = execute_report(
                    workspace_root=workspace,
                    report_file=import_resolution.report_path,
                    event_sink=event_sink,
                )
            else:
                result = execute_report(
                    workspace_root=workspace,
                    report_file=import_resolution.report_path,
                )
        elif intent_text is not None:
            if event_sink is not None:
                result = execute_intent_text(workspace_root=workspace, intent_text=intent_text, event_sink=event_sink)
            else:
                result = execute_intent_text(workspace_root=workspace, intent_text=intent_text)
        else:
            assert qspec_file is not None
            if event_sink is not None:
                result = execute_qspec(workspace_root=workspace, qspec_file=qspec_file, event_sink=event_sink)
            else:
                result = execute_qspec(workspace_root=workspace, qspec_file=qspec_file)
    except ImportSourceError as exc:
        if json_output:
            _json_error(exc.code)
        raise typer.BadParameter(f"Invalid report input: {exc.code}") from exc
    except ReportImportError as exc:
        if json_output:
            _json_error(exc.reason)
        raise typer.BadParameter(f"Invalid report input: {exc.reason}") from exc
    except (WorkspaceConflictError, WorkspaceRecoveryRequiredError) as exc:
        _handle_workspace_safety_error(
            exc,
            json_output=json_output,
            jsonl_output=jsonl_output,
            event_sink=event_sink,
        )
    if json_output:
        _echo_json(result)
        raise typer.Exit(code=exit_code_for_exec(result))
    if jsonl_output:
        raise typer.Exit(code=exit_code_for_exec(result))

    typer.echo(result.summary)
    raise typer.Exit(code=exit_code_for_exec(result))


@app.command("inspect")
def inspect_command(
    workspace: Path = typer.Option(
        Path(".quantum"),
        "--workspace",
        file_okay=False,
        dir_okay=True,
        readable=True,
        resolve_path=False,
        help="Workspace directory to inspect.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit a machine-readable JSON result.",
    ),
) -> None:
    """Inspect the current workspace revision, artifacts, and diagnostics."""
    report = inspect_workspace(workspace)
    if json_output:
        _echo_json(report)
        raise typer.Exit(code=exit_code_for_inspect(report))
    if report.status == "ok":
        typer.echo(f"revision={report.revision}")
    else:
        typer.echo(f"inspect status: {report.status}; revision={report.revision}")
    raise typer.Exit(code=exit_code_for_inspect(report))


@app.command("compare")
def compare_command(
    workspace: Path = typer.Option(
        Path(".quantum"),
        "--workspace",
        file_okay=False,
        dir_okay=True,
        readable=True,
        resolve_path=False,
        help="Workspace directory that provides the default current revision side.",
    ),
    left_report_file: Path | None = typer.Option(
        None,
        "--left-report-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=False,
        help="Left-side report JSON input. Defaults to current workspace state when omitted.",
    ),
    left_revision: str | None = typer.Option(
        None,
        "--left-revision",
        help="Left-side workspace report history revision.",
    ),
    right_report_file: Path | None = typer.Option(
        None,
        "--right-report-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=False,
        help="Right-side report JSON input. Defaults to current workspace state when omitted.",
    ),
    right_revision: str | None = typer.Option(
        None,
        "--right-revision",
        help="Right-side workspace report history revision.",
    ),
    baseline_mode: bool = typer.Option(
        False,
        "--baseline",
        help="Compare the saved workspace baseline against the current workspace state.",
    ),
    expect: str | None = typer.Option(
        None,
        "--expect",
        help="Optional compare policy expectation: same-subject, different-subject, same-qspec, different-qspec, same-report, different-report.",
    ),
    fail_on: str | None = typer.Option(
        None,
        "--fail-on",
        help="Comma-separated compare gate failures: subject_drift,qspec_drift,report_drift,backend_regression,replay_integrity_regression.",
    ),
    allow_report_drift: bool = typer.Option(
        True,
        "--allow-report-drift/--forbid-report-drift",
        help="Whether report and diagnostic drift is allowed under the compare policy.",
    ),
    forbid_backend_regressions: bool = typer.Option(
        False,
        "--forbid-backend-regressions",
        help="Fail compare when backend availability regresses on the right side.",
    ),
    forbid_replay_integrity_regressions: bool = typer.Option(
        False,
        "--forbid-replay-integrity-regressions",
        help="Fail compare when replay trust regresses on the right side.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit a machine-readable JSON result.",
    ),
    jsonl_output: bool = typer.Option(
        False,
        "--jsonl",
        help="Emit newline-delimited machine-readable compare events.",
    ),
    detail: bool = typer.Option(
        False,
        "--detail",
        help="Emit a more detailed human-readable compare summary.",
    ),
) -> None:
    """Compare two runtime inputs and answer whether they describe the same workload."""
    _validate_output_modes(json_output=json_output, jsonl_output=jsonl_output)
    if baseline_mode and any(
        value is not None
        for value in (left_report_file, left_revision, right_report_file, right_revision)
    ):
        if json_output:
            _json_error("baseline_mode_conflict")
        raise typer.BadParameter(
            "--baseline cannot be combined with explicit left/right compare inputs."
        )

    if left_report_file is not None and left_revision is not None:
        if json_output:
            _json_error("left_source_conflict")
        raise typer.BadParameter("Provide at most one of --left-report-file or --left-revision.")
    if right_report_file is not None and right_revision is not None:
        if json_output:
            _json_error("right_source_conflict")
        raise typer.BadParameter("Provide at most one of --right-report-file or --right-revision.")

    try:
        fail_on_items = [item.strip() for item in fail_on.split(",") if item.strip()] if fail_on else []
        policy = ComparePolicy.model_validate({
            "expect": expect,
            "fail_on": fail_on_items,
            "allow_report_drift": allow_report_drift,
            "forbid_backend_regressions": forbid_backend_regressions,
            "forbid_replay_integrity_regressions": forbid_replay_integrity_regressions,
        }) if (
            expect is not None
            or bool(fail_on_items)
            or not allow_report_drift
            or forbid_backend_regressions
            or forbid_replay_integrity_regressions
        ) else None
    except Exception as exc:
        if json_output:
            _json_error("invalid_compare_policy")
        raise typer.BadParameter("Invalid compare policy.") from exc

    event_sink = _make_jsonl_emitter(workspace=workspace) if jsonl_output else None
    try:
        if baseline_mode:
            if event_sink is not None:
                baseline_resolution = resolve_workspace_baseline(workspace)
                current_resolution = _resolve_runtime_input(
                    workspace=workspace,
                    report_file=None,
                    revision=None,
                )
                event_sink("compare_started", {"mode": "baseline"}, current_resolution.revision, "ok")
                event_sink(
                    "left_resolved",
                    {
                        "revision": baseline_resolution.resolution.revision,
                        "source_kind": baseline_resolution.resolution.source_kind,
                    },
                    baseline_resolution.resolution.revision,
                    "ok",
                )
                event_sink(
                    "right_resolved",
                    {
                        "revision": current_resolution.revision,
                        "source_kind": current_resolution.source_kind,
                    },
                    current_resolution.revision,
                    "ok",
                )
            result = compare_workspace_baseline(workspace, policy=policy)
        else:
            left = _resolve_runtime_input(
                workspace=workspace,
                report_file=left_report_file,
                revision=left_revision,
            )
            right = _resolve_runtime_input(
                workspace=workspace,
                report_file=right_report_file,
                revision=right_revision,
            )
            if event_sink is not None:
                event_sink("compare_started", {"mode": "explicit"}, None, "ok")
                event_sink(
                    "left_resolved",
                    {"revision": left.revision, "source_kind": left.source_kind},
                    left.revision,
                    "ok",
                )
                event_sink(
                    "right_resolved",
                    {"revision": right.revision, "source_kind": right.source_kind},
                    right.revision,
                    "ok",
                )
            result = compare_import_resolutions(left, right, policy=policy)
    except ImportSourceError as exc:
        if json_output:
            _json_error(exc.code)
        raise typer.BadParameter(f"Invalid compare input: {exc.code}") from exc
    except ReportImportError as exc:
        if json_output:
            _json_error(exc.reason)
        raise typer.BadParameter(f"Invalid compare input: {exc.reason}") from exc

    try:
        persist_compare_result(workspace_root=workspace, result=result)
    except (WorkspaceConflictError, WorkspaceRecoveryRequiredError) as exc:
        _handle_workspace_safety_error(exc, json_output=json_output, jsonl_output=jsonl_output, event_sink=event_sink)

    if json_output:
        _echo_json(result, exclude_none=True)
        raise typer.Exit(code=exit_code_for_compare(result, structured=True))
    if jsonl_output:
        assert event_sink is not None
        event_sink(
            "compare_completed",
            result.model_dump(mode="json"),
            None,
            "ok" if result.status == "same_subject" else "degraded",
        )
        raise typer.Exit(code=exit_code_for_compare(result, structured=True))

    highlight = result.highlights[0] if result.highlights else "no_highlights"
    verdict_summary = result.verdict.get("summary", "No compare policy requested.") if isinstance(result.verdict, dict) else "No compare policy requested."
    if detail:
        typer.echo(
            "\n".join(
                [
                    f"status: {result.status}",
                    f"left: {result.left.revision}",
                    f"right: {result.right.revision}",
                    f"same_qspec: {str(result.same_qspec).lower()}",
                    f"same_report: {str(result.same_report).lower()}",
                    f"policy: {verdict_summary}",
                    f"differences: {', '.join(result.differences) if result.differences else 'none'}",
                    f"reason_codes: {', '.join(result.reason_codes) if result.reason_codes else 'none'}",
                    f"highlight: {highlight}",
                ]
            )
        )
    else:
        typer.echo(
            f"{result.status}; left={result.left.revision}; right={result.right.revision}; "
            f"same_qspec={str(result.same_qspec).lower()}; same_report={str(result.same_report).lower()}; "
            f"policy={verdict_summary}; highlight={highlight}"
        )
    raise typer.Exit(code=exit_code_for_compare(result, structured=False))


@app.command("doctor")
def doctor_command(
    workspace: Path = typer.Option(
        Path(".quantum"),
        "--workspace",
        file_okay=False,
        dir_okay=True,
        resolve_path=False,
        help="Workspace directory to validate.",
    ),
    fix: bool = typer.Option(
        False,
        "--fix",
        help="Repair missing workspace directories and manifest if needed.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit a machine-readable JSON result.",
    ),
    jsonl_output: bool = typer.Option(
        False,
        "--jsonl",
        help="Emit newline-delimited machine-readable doctor events.",
    ),
) -> None:
    """Check runtime dependencies and workspace health."""
    _validate_output_modes(json_output=json_output, jsonl_output=jsonl_output)
    event_sink = _make_jsonl_emitter(workspace=workspace) if jsonl_output else None
    if event_sink is not None:
        event_sink("doctor_started", {"fix": fix}, None, "ok")
    try:
        report = (
            run_doctor(workspace_root=workspace, fix=fix, event_sink=event_sink)
            if event_sink is not None
            else run_doctor(workspace_root=workspace, fix=fix)
        )
    except (WorkspaceConflictError, WorkspaceRecoveryRequiredError) as exc:
        _handle_workspace_safety_error(exc, json_output=json_output, jsonl_output=jsonl_output, event_sink=event_sink)
    if json_output:
        _echo_json(report)
        raise typer.Exit(code=exit_code_for_doctor(report))
    if event_sink is not None:
        event_sink("doctor_completed", report.model_dump(mode="json"), None, report.status)
        raise typer.Exit(code=exit_code_for_doctor(report))
    typer.echo(f"doctor status: {report.status}")
    raise typer.Exit(code=exit_code_for_doctor(report))


@backend_app.command("list")
def backend_list_command(
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit a machine-readable JSON result.",
    ),
) -> None:
    """List known runtime backends and their availability."""
    report = list_backends()
    if json_output:
        _echo_json(report)
        return
    typer.echo(", ".join(sorted(report.backends)))


def main() -> None:
    """Run the Typer application."""
    app()


if __name__ == "__main__":
    main()
