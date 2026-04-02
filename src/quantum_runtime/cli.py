"""Typer-based CLI entrypoint for Quantum Runtime."""

from __future__ import annotations

from pathlib import Path

import typer

from quantum_runtime import __version__
from quantum_runtime.diagnostics import run_structural_benchmark
from quantum_runtime.qspec import QSpec
from quantum_runtime.runtime import execute_intent, execute_qspec, inspect_workspace, run_doctor
from quantum_runtime.workspace import WorkspaceManager


app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Deterministic quantum runtime CLI for agent hosts.",
)


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
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit a machine-readable JSON result.",
    ),
) -> None:
    """Run structural backend benchmarks against the current QSpec."""
    handle = WorkspaceManager.load_or_init(workspace)
    qspec_path = handle.root / "specs" / "current.json"

    if not qspec_path.exists():
        if json_output:
            typer.echo('{"status":"error","reason":"missing_qspec"}')
            raise typer.Exit(code=3)
        raise typer.BadParameter(f"Missing QSpec at {qspec_path}")

    qspec = QSpec.model_validate_json(qspec_path.read_text())
    benchmark = run_structural_benchmark(
        qspec,
        handle,
        [item.strip() for item in backends.split(",") if item.strip()],
    )

    if json_output:
        typer.echo(benchmark.model_dump_json(indent=2))
        return

    typer.echo(f"Benchmark status: {benchmark.status}")


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
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit a machine-readable JSON result.",
    ),
) -> None:
    """Execute an intent file through the deterministic runtime pipeline."""
    if (intent_file is None) == (qspec_file is None):
        if json_output:
            typer.echo('{"status":"error","reason":"expected_exactly_one_input"}')
            raise typer.Exit(code=3)
        raise typer.BadParameter("Provide exactly one of --intent-file or --qspec-file.")

    if intent_file is not None:
        result = execute_intent(workspace_root=workspace, intent_file=intent_file)
    else:
        assert qspec_file is not None
        result = execute_qspec(workspace_root=workspace, qspec_file=qspec_file)
    if json_output:
        typer.echo(result.model_dump_json(indent=2))
        return

    typer.echo(result.summary)


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
        return
    typer.echo(f"revision={report.revision}")


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
        return
    typer.echo(f"doctor status: {report.status}")


def main() -> None:
    """Run the Typer application."""
    app()


if __name__ == "__main__":
    main()
