"""Typer-based CLI entrypoint for Quantum Runtime."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from quantum_runtime import __version__
from quantum_runtime.diagnostics import run_structural_benchmark
from quantum_runtime.qspec import QSpec
from quantum_runtime.runtime import (
    ComparePolicy,
    CompareResult,
    ImportReference,
    ImportResolution,
    ImportSourceError,
    ReportImportError,
    compare_import_resolutions,
    execute_intent,
    execute_intent_text,
    execute_qspec,
    execute_report,
    export_artifact,
    export_artifact_from_report,
    inspect_workspace,
    list_backends,
    resolve_import_reference,
    run_doctor,
)
from quantum_runtime.runtime.exit_codes import (
    exit_code_for_benchmark,
    exit_code_for_compare,
    exit_code_for_doctor,
    exit_code_for_exec,
    exit_code_for_export,
    exit_code_for_inspect,
)
from quantum_runtime.workspace import WorkspaceManager


app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Deterministic quantum runtime CLI for agent hosts.",
)
backend_app = typer.Typer(add_completion=False, help="Backend discovery helpers.")
app.add_typer(backend_app, name="backend")


def _json_error(reason: str) -> None:
    typer.echo(json.dumps({"status": "error", "reason": reason}))
    raise typer.Exit(code=3)


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
        ImportReference(report_file=report_file)
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
        typer.echo(result.model_dump_json(indent=2))
        return

    typer.echo(f"Initialized workspace at {result.workspace}")


@app.command("version")
def version_command() -> None:
    """Print the package version."""
    typer.echo(__version__)


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
    backends: str = typer.Option(
        "qiskit-local,classiq",
        "--backends",
        help="Comma-separated backend list for structural benchmarking.",
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
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit a machine-readable JSON result.",
    ),
) -> None:
    """Run structural backend benchmarks against the current QSpec."""
    handle = WorkspaceManager.load_or_init(workspace)
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

    benchmark = run_structural_benchmark(
        qspec,
        handle,
        [item.strip() for item in backends.split(",") if item.strip()],
    )

    if json_output:
        typer.echo(benchmark.model_dump_json(indent=2))
        raise typer.Exit(code=exit_code_for_benchmark(benchmark))

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
            result = export_artifact_from_report(
                workspace_root=workspace,
                report_file=import_resolution.report_path,
                output_format=output_format,
            )
        else:
            qspec_path = workspace / "specs" / "current.json"
            if not qspec_path.exists():
                if json_output:
                    _json_error("missing_qspec")
                raise typer.BadParameter(f"Missing QSpec at {qspec_path}")
            result = export_artifact(workspace_root=workspace, output_format=output_format)
    except ImportSourceError as exc:
        if json_output:
            _json_error(exc.code)
        raise typer.BadParameter(f"Invalid report input: {exc.code}") from exc
    except ReportImportError as exc:
        if json_output:
            _json_error(exc.reason)
        raise typer.BadParameter(f"Invalid report input: {exc.reason}") from exc

    if json_output:
        typer.echo(result.model_dump_json(indent=2))
        raise typer.Exit(code=exit_code_for_export(result))

    typer.echo(result.path or result.reason or result.status)
    raise typer.Exit(code=exit_code_for_export(result))


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
) -> None:
    """Execute an intent file through the deterministic runtime pipeline."""
    inputs_provided = sum(
        value is not None
        for value in (intent_file, qspec_file, report_file, revision, intent_text)
    )
    if inputs_provided != 1:
        if json_output:
            typer.echo('{"status":"error","reason":"expected_exactly_one_input"}')
            raise typer.Exit(code=3)
        raise typer.BadParameter(
            "Provide exactly one of --intent-file, --qspec-file, --report-file, --revision, or --intent-text."
        )

    try:
        if intent_file is not None:
            result = execute_intent(workspace_root=workspace, intent_file=intent_file)
        elif report_file is not None or revision is not None:
            import_resolution = _resolve_report_import(
                workspace=workspace,
                report_file=report_file,
                revision=revision,
            )
            assert import_resolution is not None
            result = execute_report(
                workspace_root=workspace,
                report_file=import_resolution.report_path,
            )
        elif intent_text is not None:
            result = execute_intent_text(workspace_root=workspace, intent_text=intent_text)
        else:
            assert qspec_file is not None
            result = execute_qspec(workspace_root=workspace, qspec_file=qspec_file)
    except ImportSourceError as exc:
        if json_output:
            _json_error(exc.code)
        raise typer.BadParameter(f"Invalid report input: {exc.code}") from exc
    except ReportImportError as exc:
        if json_output:
            _json_error(exc.reason)
        raise typer.BadParameter(f"Invalid report input: {exc.reason}") from exc
    if json_output:
        typer.echo(result.model_dump_json(indent=2))
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
        typer.echo(report.model_dump_json(indent=2))
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
    expect: str | None = typer.Option(
        None,
        "--expect",
        help="Optional compare policy expectation: same-subject, different-subject, same-qspec, different-qspec, same-report, different-report.",
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
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit a machine-readable JSON result.",
    ),
) -> None:
    """Compare two runtime inputs and answer whether they describe the same workload."""
    if left_report_file is not None and left_revision is not None:
        if json_output:
            _json_error("left_source_conflict")
        raise typer.BadParameter("Provide at most one of --left-report-file or --left-revision.")
    if right_report_file is not None and right_revision is not None:
        if json_output:
            _json_error("right_source_conflict")
        raise typer.BadParameter("Provide at most one of --right-report-file or --right-revision.")

    try:
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
    except ImportSourceError as exc:
        if json_output:
            _json_error(exc.code)
        raise typer.BadParameter(f"Invalid compare input: {exc.code}") from exc
    except ReportImportError as exc:
        if json_output:
            _json_error(exc.reason)
        raise typer.BadParameter(f"Invalid compare input: {exc.reason}") from exc

    try:
        policy = ComparePolicy.model_validate({
            "expect": expect,
            "allow_report_drift": allow_report_drift,
            "forbid_backend_regressions": forbid_backend_regressions,
        }) if (
            expect is not None
            or not allow_report_drift
            or forbid_backend_regressions
        ) else None
    except Exception as exc:
        if json_output:
            _json_error("invalid_compare_policy")
        raise typer.BadParameter("Invalid compare policy.") from exc

    result: CompareResult = compare_import_resolutions(left, right, policy=policy)
    if json_output:
        typer.echo(result.model_dump_json(indent=2))
        raise typer.Exit(code=exit_code_for_compare(result))

    highlight = result.highlights[0] if result.highlights else "no_highlights"
    verdict_summary = result.verdict.get("summary", "No compare policy requested.") if isinstance(result.verdict, dict) else "No compare policy requested."
    typer.echo(
        f"{result.status}; left={result.left.revision}; right={result.right.revision}; "
        f"same_qspec={str(result.same_qspec).lower()}; same_report={str(result.same_report).lower()}; "
        f"policy={verdict_summary}; highlight={highlight}"
    )
    raise typer.Exit(code=exit_code_for_compare(result))


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
) -> None:
    """Check runtime dependencies and workspace health."""
    report = run_doctor(workspace_root=workspace, fix=fix)
    if json_output:
        typer.echo(report.model_dump_json(indent=2))
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
        typer.echo(report.model_dump_json(indent=2))
        return
    typer.echo(", ".join(sorted(report.backends)))


def main() -> None:
    """Run the Typer application."""
    app()


if __name__ == "__main__":
    main()
