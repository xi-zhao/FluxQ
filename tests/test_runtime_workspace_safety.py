from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

import quantum_runtime.runtime.executor as executor_module
from quantum_runtime.errors import WorkspaceConflictError, WorkspaceRecoveryRequiredError
from quantum_runtime.runtime.executor import ExecResult, execute_intent


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class _ThreadOutcome:
    result: ExecResult | None = None
    error: BaseException | None = None


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text())


def _load_jsonl(path: Path) -> list[dict[str, object]]:
    payloads: list[dict[str, object]] = []
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line:
            continue
        payloads.append(json.loads(line))
    return payloads


def _write_intent(path: Path, *, title: str, goal: str) -> Path:
    path.write_text(
        f"""---
title: {title}
---

{goal}
"""
    )
    return path


def _history_paths(revision: str) -> dict[str, Path]:
    return {
        "intent_markdown": Path("intents/history") / f"{revision}.md",
        "intent_json": Path("intents/history") / f"{revision}.json",
        "plan_json": Path("plans/history") / f"{revision}.json",
        "qspec": Path("specs/history") / f"{revision}.json",
        "qiskit": Path("artifacts/history") / revision / "qiskit" / "main.py",
        "qasm": Path("artifacts/history") / revision / "qasm" / "main.qasm",
        "diagram_txt": Path("artifacts/history") / revision / "figures" / "circuit.txt",
        "diagram_png": Path("artifacts/history") / revision / "figures" / "circuit.png",
        "report": Path("reports/history") / f"{revision}.json",
        "manifest": Path("manifests/history") / f"{revision}.json",
        "events": Path("events/history") / f"{revision}.jsonl",
        "trace": Path("trace/history") / f"{revision}.ndjson",
    }


def _assert_current_aliases_match_revision(workspace: Path, revision: str) -> None:
    history_paths = _history_paths(revision)

    assert (workspace / "intents" / "latest.md").read_text() == (workspace / history_paths["intent_markdown"]).read_text()
    assert (workspace / "intents" / "latest.json").read_text() == (workspace / history_paths["intent_json"]).read_text()
    assert (workspace / "plans" / "latest.json").read_text() == (workspace / history_paths["plan_json"]).read_text()
    assert (workspace / "specs" / "current.json").read_text() == (workspace / history_paths["qspec"]).read_text()
    assert (workspace / "artifacts" / "qiskit" / "main.py").read_text() == (workspace / history_paths["qiskit"]).read_text()
    assert (workspace / "artifacts" / "qasm" / "main.qasm").read_text() == (workspace / history_paths["qasm"]).read_text()
    assert (workspace / "figures" / "circuit.txt").read_text() == (workspace / history_paths["diagram_txt"]).read_text()
    assert (workspace / "figures" / "circuit.png").read_bytes() == (workspace / history_paths["diagram_png"]).read_bytes()
    assert (workspace / "reports" / "latest.json").read_text() == (workspace / history_paths["report"]).read_text()
    assert (workspace / "manifests" / "latest.json").read_text() == (workspace / history_paths["manifest"]).read_text()


def _run_exec(workspace: Path, intent_path: Path, outcome: _ThreadOutcome) -> None:
    try:
        outcome.result = execute_intent(
            workspace_root=workspace,
            intent_file=intent_path,
        )
    except BaseException as exc:  # pragma: no cover - assertions inspect the captured error
        outcome.error = exc


def test_concurrent_exec_yields_one_winner_one_workspace_conflict_without_mixed_aliases(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / ".quantum"
    ghz_intent = PROJECT_ROOT / "examples" / "intent-ghz.md"
    bell_intent = _write_intent(
        tmp_path / "intent-bell.md",
        title="Bell intent",
        goal="Create a Bell pair and measure both qubits.",
    )
    original_run_local_simulation = executor_module.run_local_simulation
    original_write_diagrams = executor_module.write_diagrams
    first_simulation_started = threading.Event()
    release_first_simulation = threading.Event()
    call_count = 0
    call_lock = threading.Lock()

    def _blocking_run_local_simulation(*args: object, **kwargs: object):
        nonlocal call_count
        with call_lock:
            call_count += 1
            is_first_call = call_count == 1
        if is_first_call:
            first_simulation_started.set()
            assert release_first_simulation.wait(timeout=5), "timed out waiting for overlapping exec"
        return original_run_local_simulation(*args, **kwargs)

    def _thread_safe_write_diagrams(*args: object, **kwargs: object):
        workspace_handle = kwargs.get("workspace", args[1] if len(args) > 1 else None)
        assert workspace_handle is not None
        text_path = workspace_handle.root / "figures" / "circuit.txt"
        png_path = workspace_handle.root / "figures" / "circuit.png"
        text_path.parent.mkdir(parents=True, exist_ok=True)
        png_path.parent.mkdir(parents=True, exist_ok=True)
        text_path.write_text("thread-safe diagram\n")
        png_path.write_bytes(b"thread-safe-png")
        return SimpleNamespace(text_path=text_path, png_path=png_path)

    monkeypatch.setattr(executor_module, "run_local_simulation", _blocking_run_local_simulation)
    monkeypatch.setattr(executor_module, "write_diagrams", _thread_safe_write_diagrams)

    first_outcome = _ThreadOutcome()
    second_outcome = _ThreadOutcome()
    first_thread = threading.Thread(target=_run_exec, args=(workspace, ghz_intent, first_outcome))
    second_thread = threading.Thread(target=_run_exec, args=(workspace, bell_intent, second_outcome))

    first_thread.start()
    assert first_simulation_started.wait(timeout=5), "first exec never entered the simulated overlap window"
    second_thread.start()
    second_thread.join(timeout=10)
    release_first_simulation.set()
    first_thread.join(timeout=10)

    assert first_outcome.result is not None or first_outcome.error is not None
    assert second_outcome.result is not None or second_outcome.error is not None

    results = [item.result for item in (first_outcome, second_outcome) if item.result is not None]
    errors = [item.error for item in (first_outcome, second_outcome) if item.error is not None]

    assert len(results) == 1
    assert len(errors) == 1
    assert isinstance(errors[0], WorkspaceConflictError)

    winner = results[0]
    assert winner is not None
    _assert_current_aliases_match_revision(workspace, winner.revision)

    latest_report = _load_json(workspace / "reports" / "latest.json")
    latest_manifest = _load_json(workspace / "manifests" / "latest.json")
    assert latest_report["revision"] == winner.revision
    assert latest_manifest["revision"] == winner.revision
    assert latest_report["qspec"]["path"].endswith(f"specs/history/{winner.revision}.json")
    assert latest_report["artifacts"]["qiskit_code"].endswith(f"artifacts/history/{winner.revision}/qiskit/main.py")
    assert latest_report["artifacts"]["qasm3"].endswith(f"artifacts/history/{winner.revision}/qasm/main.qasm")
    assert latest_report["diagnostics"]["diagram"]["text_path"].endswith(
        f"artifacts/history/{winner.revision}/figures/circuit.txt"
    )
    assert latest_report["diagnostics"]["diagram"]["png_path"].endswith(
        f"artifacts/history/{winner.revision}/figures/circuit.png"
    )
    assert latest_manifest["events"]["events_jsonl"]["path"].endswith(f"events/history/{winner.revision}.jsonl")
    assert latest_manifest["events"]["trace_ndjson"]["path"].endswith(f"trace/history/{winner.revision}.ndjson")


def test_exec_history_snapshots_are_coherent_for_one_reserved_revision(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"
    result = execute_intent(
        workspace_root=workspace,
        intent_file=PROJECT_ROOT / "examples" / "intent-ghz.md",
    )

    history_paths = _history_paths(result.revision)
    for relative_path in history_paths.values():
        assert (workspace / relative_path).exists(), f"missing history artifact: {relative_path}"

    manifest = _load_json(workspace / history_paths["manifest"])
    report = _load_json(workspace / history_paths["report"])
    event_history = _load_jsonl(workspace / history_paths["events"])
    trace_history = _load_jsonl(workspace / history_paths["trace"])

    assert manifest["revision"] == result.revision
    assert report["revision"] == result.revision
    assert report["qspec"]["path"].endswith(f"specs/history/{result.revision}.json")
    assert report["artifacts"]["report"].endswith(f"reports/history/{result.revision}.json")
    assert manifest["qspec"]["path"].endswith(f"specs/history/{result.revision}.json")
    assert manifest["report"]["path"].endswith(f"reports/history/{result.revision}.json")
    assert manifest["intent"]["path"].endswith(f"intents/history/{result.revision}.json")
    assert manifest["plan"]["path"].endswith(f"plans/history/{result.revision}.json")
    assert manifest["events"]["events_jsonl"]["path"].endswith(f"events/history/{result.revision}.jsonl")
    assert manifest["events"]["trace_ndjson"]["path"].endswith(f"trace/history/{result.revision}.ndjson")
    assert event_history
    assert trace_history
    assert all(item["revision"] == result.revision for item in event_history)
    assert all(item["revision"] == result.revision for item in trace_history)


def test_interrupted_commit_keeps_previous_current_revision_authoritative(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    workspace = tmp_path / ".quantum"
    bell_intent = _write_intent(
        tmp_path / "intent-bell.md",
        title="Bell intent",
        goal="Create a Bell pair and measure both qubits.",
    )
    baseline = execute_intent(
        workspace_root=workspace,
        intent_file=PROJECT_ROOT / "examples" / "intent-ghz.md",
    )
    before_paths = {
        "intent_markdown": workspace / "intents" / "latest.md",
        "intent_json": workspace / "intents" / "latest.json",
        "plan_json": workspace / "plans" / "latest.json",
        "qspec": workspace / "specs" / "current.json",
        "qiskit": workspace / "artifacts" / "qiskit" / "main.py",
        "qasm": workspace / "artifacts" / "qasm" / "main.qasm",
        "diagram_txt": workspace / "figures" / "circuit.txt",
        "diagram_png": workspace / "figures" / "circuit.png",
        "report": workspace / "reports" / "latest.json",
        "manifest": workspace / "manifests" / "latest.json",
        "events": workspace / "events.jsonl",
        "trace": workspace / "trace" / "events.ndjson",
    }
    before_text = {
        name: path.read_bytes()
        for name, path in before_paths.items()
    }

    def _boom(*args: object, **kwargs: object):
        raise RuntimeError("simulated commit failure")

    monkeypatch.setattr(executor_module, "write_run_manifest", _boom)

    with pytest.raises(RuntimeError, match="simulated commit failure"):
        execute_intent(
            workspace_root=workspace,
            intent_file=bell_intent,
        )

    for name, path in before_paths.items():
        assert path.read_bytes() == before_text[name], f"{name} changed after interrupted commit"

    _assert_current_aliases_match_revision(workspace, baseline.revision)

    assert all(isinstance(item, dict) for item in _load_jsonl(workspace / "events.jsonl"))
    assert all(isinstance(item, dict) for item in _load_jsonl(workspace / "trace" / "events.ndjson"))


def test_exec_blocks_when_interrupted_write_temp_files_require_recovery(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"
    bell_intent = _write_intent(
        tmp_path / "intent-bell.md",
        title="Bell intent",
        goal="Create a Bell pair and measure both qubits.",
    )
    execute_intent(
        workspace_root=workspace,
        intent_file=PROJECT_ROOT / "examples" / "intent-ghz.md",
    )
    pending_report = workspace / "reports" / "latest.json.tmp"
    pending_manifest = workspace / "manifests" / "latest.json.tmp"
    pending_report.write_text("pending")
    pending_manifest.write_text("pending")

    with pytest.raises(WorkspaceRecoveryRequiredError) as exc_info:
        execute_intent(
            workspace_root=workspace,
            intent_file=bell_intent,
        )

    error = exc_info.value
    assert error.details["workspace"] == str(workspace.resolve())
    assert sorted(error.details["pending_files"]) == sorted([str(pending_manifest), str(pending_report)])
    assert error.details["last_valid_revision"] == "rev_000001"
