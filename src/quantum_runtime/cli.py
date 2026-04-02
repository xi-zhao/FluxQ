"""Typer-based CLI entrypoint for Quantum Runtime."""

from __future__ import annotations

from pathlib import Path

import typer

from quantum_runtime import __version__
from quantum_runtime.diagnostics import run_structural_benchmark
from quantum_runtime.qspec import QSpec
from quantum_runtime.runtime import (
    ReportImportError,
    execute_intent,
    execute_intent_text,
    execute_qspec,
    execute_report,
    export_artifact,
    export_artifact_from_report,
    inspect_workspace,
    list_backends,
    load_qspec_from_report,
    run_doctor,
)
from quantum_runtime.runtime.exit_codes import (
    exit_code_for_benchmark,
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
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit a machine-readable JSON result.",
    ),
) -> None:
    """Run structural backend benchmarks against the current QSpec."""
    handle = WorkspaceManager.load_or_init(workspace)
    try:
        if report_file is not None:
            qspec = load_qspec_from_report(report_file)
        else:
            qspec_path = handle.root / "specs" / "current.json"
            if not qspec_path.exists():
                if json_output:
                    typer.echo('{"status":"error","reason":"missing_qspec"}')
                    raise typer.Exit(code=3)
                raise typer.BadParameter(f"Missing QSpec at {qspec_path}")
            qspec = QSpec.model_validate_json(qspec_path.read_text())
    except ReportImportError as exc:
        if json_output:
            typer.echo(f'{{"status":"error","reason":"{exc.reason}"}}')
            raise typer.Exit(code=3) from exc
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
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit a machine-readable JSON result.",
    ),
) -> None:
    """Re-export one artifact from the current workspace QSpec."""
    try:
        if report_file is not None:
            result = export_artifact_from_report(
                workspace_root=workspace,
                report_file=report_file,
                output_format=output_format,
            )
        else:
            qspec_path = workspace / "specs" / "current.json"
            if not qspec_path.exists():
                if json_output:
                    typer.echo('{"status":"error","reason":"missing_qspec"}')
                    raise typer.Exit(code=3)
                raise typer.BadParameter(f"Missing QSpec at {qspec_path}")
            result = export_artifact(workspace_root=workspace, output_format=output_format)
    except ReportImportError as exc:
        if json_output:
            typer.echo(f'{{"status":"error","reason":"{exc.reason}"}}')
            raise typer.Exit(code=3) from exc
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
        for value in (intent_file, qspec_file, report_file, intent_text)
    )
    if inputs_provided != 1:
        if json_output:
            typer.echo('{"status":"error","reason":"expected_exactly_one_input"}')
            raise typer.Exit(code=3)
        raise typer.BadParameter(
            "Provide exactly one of --intent-file, --qspec-file, --report-file, or --intent-text."
        )

    try:
        if intent_file is not None:
            result = execute_intent(workspace_root=workspace, intent_file=intent_file)
        elif report_file is not None:
            result = execute_report(workspace_root=workspace, report_file=report_file)
        elif intent_text is not None:
            result = execute_intent_text(workspace_root=workspace, intent_text=intent_text)
        else:
            assert qspec_file is not None
            result = execute_qspec(workspace_root=workspace, qspec_file=qspec_file)
    except ReportImportError as exc:
        if json_output:
            typer.echo(f'{{"status":"error","reason":"{exc.reason}"}}')
            raise typer.Exit(code=3) from exc
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
