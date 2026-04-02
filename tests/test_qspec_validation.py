from __future__ import annotations

import json
from pathlib import Path

import pytest

from quantum_runtime.qspec import (
    Constraints,
    MeasureNode,
    PatternNode,
    QSpec,
    QSpecValidationError,
    Register,
    normalize_qspec,
    validate_qspec,
)
from quantum_runtime.runtime.executor import execute_qspec
from quantum_runtime.workspace import WorkspaceManifest, WorkspaceManager


def _make_qspec() -> QSpec:
    return QSpec(
        program_id="  prog_ghz_4  ",
        title="  GHZ runtime  ",
        goal="  Generate a 4-qubit GHZ circuit and measure all qubits.  ",
        entrypoint="  main  ",
        registers=[
            Register(kind="qubit", name="  q  ", size=4),
            Register(kind="cbit", name="  c  ", size=4),
        ],
        body=[
            PatternNode(pattern="ghz", args={"register": "q", "size": 4}),
            MeasureNode(
                qubits=["q[0]", "q[1]", "q[2]", "q[3]"],
                cbits=["c[0]", "c[1]", "c[2]", "c[3]"],
            ),
        ],
        constraints=Constraints(
            basis_gates=[" h ", "cx", "h", ""],
            connectivity_map=[(0, 1), (1, 2)],
            shots=1024,
            optimization_level=2,
        ),
        backend_preferences=[" qiskit-local ", "", "classiq", "qiskit-local"],
        metadata={"source": "intent"},
    )


def test_normalize_qspec_strips_and_deduplicates_runtime_metadata() -> None:
    raw = _make_qspec()

    normalized = normalize_qspec(raw)

    assert normalized is not raw
    assert raw.program_id == "  prog_ghz_4  "
    assert normalized.program_id == "prog_ghz_4"
    assert normalized.title == "GHZ runtime"
    assert normalized.goal == "Generate a 4-qubit GHZ circuit and measure all qubits."
    assert normalized.entrypoint == "main"
    assert [register.name for register in normalized.registers] == ["q", "c"]
    assert normalized.constraints.basis_gates == ["h", "cx"]
    assert normalized.backend_preferences == ["qiskit-local", "classiq"]


def test_validate_qspec_rejects_incomplete_measurement_pattern() -> None:
    invalid = _make_qspec()
    invalid.body[1] = MeasureNode(qubits=["q[0]"], cbits=["c[0]"])

    with pytest.raises(QSpecValidationError) as exc:
        validate_qspec(invalid)

    assert exc.value.code == "invalid_qspec"
    assert "measure" in str(exc.value).lower()


def test_execute_qspec_normalizes_before_persisting_artifacts(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"
    handle = WorkspaceManager.load_or_init(workspace)
    qspec_path = tmp_path / "raw-qspec.json"
    execution_qspec = _make_qspec()
    execution_qspec.backend_preferences = [" qiskit-local ", "qiskit-local"]
    qspec_path.write_text(execution_qspec.model_dump_json(indent=2))

    result = execute_qspec(workspace_root=workspace, qspec_file=qspec_path)

    assert result.status == "ok"
    saved = json.loads((workspace / "specs" / "current.json").read_text())
    assert saved["program_id"] == "prog_ghz_4"
    assert saved["title"] == "GHZ runtime"
    assert saved["backend_preferences"] == ["qiskit-local"]
    assert (workspace / "reports" / "latest.json").exists()
    assert (workspace / "artifacts" / "qiskit" / "main.py").exists()
    manifest = WorkspaceManifest.load(workspace / "workspace.json")
    assert manifest.current_revision == result.revision
