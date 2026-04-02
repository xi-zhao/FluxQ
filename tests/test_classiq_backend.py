from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from quantum_runtime.backends.classiq_backend import run_classiq_backend
from quantum_runtime.intent.parser import parse_intent_file
from quantum_runtime.intent.planner import plan_to_qspec
from quantum_runtime.workspace import WorkspaceManager


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_run_classiq_backend_returns_dependency_missing_when_sdk_unavailable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    intent = parse_intent_file(PROJECT_ROOT / "examples" / "intent-ghz.md")
    qspec = plan_to_qspec(intent)
    qspec.backend_preferences.append("classiq")
    handle = WorkspaceManager.load_or_init(tmp_path / ".quantum")

    def raise_missing() -> object:
        raise ModuleNotFoundError("No module named 'classiq'")

    monkeypatch.setattr(
        "quantum_runtime.backends.classiq_backend._load_classiq_module",
        raise_missing,
    )

    report = run_classiq_backend(qspec, handle)

    assert report.status == "dependency_missing"
    assert report.reason == "classiq_not_installed"
    assert report.code_path is not None
    assert report.code_path.exists()
    assert report.results_path is None
    assert report.program_id is None


def test_run_classiq_backend_synthesizes_with_fake_sdk(
    tmp_path: Path,
    monkeypatch,
) -> None:
    intent = parse_intent_file(PROJECT_ROOT / "examples" / "intent-ghz.md")
    qspec = plan_to_qspec(intent)
    qspec.backend_preferences.append("classiq")
    qspec.constraints.max_width = 4
    qspec.constraints.backend_provider = "fake-cloud"
    qspec.constraints.backend_name = "fake-backend"
    qspec.constraints.optimization_level = 1
    handle = WorkspaceManager.load_or_init(tmp_path / ".quantum")

    fake_classiq = _build_fake_classiq_module()
    monkeypatch.setattr(
        "quantum_runtime.backends.classiq_backend._load_classiq_module",
        lambda: fake_classiq,
    )

    report = run_classiq_backend(qspec, handle)

    assert report.status == "ok"
    assert report.reason is None
    assert report.code_path is not None
    assert report.code_path.exists()
    assert report.results_path is not None
    assert report.results_path.exists()
    assert report.program_id == "fake-program"
    assert report.synthesis_metrics == {
        "width": 4,
        "depth": 6,
        "two_qubit_gates": 3,
        "measure_count": 4,
    }
    assert report.warnings == ["synthetic warning"]
    assert json.loads(report.results_path.read_text()) == {
        "program_id": "fake-program",
        "warnings": ["synthetic warning"],
        "width": 4,
        "depth": 6,
        "two_qubit_gates": 3,
        "measure_count": 4,
    }
    assert report.details["synthesis_source"].endswith("synthesis.json")
    assert report.details["synthesis_metrics"] == report.synthesis_metrics
    assert fake_classiq.last_constraints.max_width == 4
    assert fake_classiq.last_preferences.backend_service_provider == "fake-cloud"
    assert fake_classiq.last_preferences.backend_name == "fake-backend"
    assert fake_classiq.last_preferences.optimization_level == 1


def _build_fake_classiq_module() -> SimpleNamespace:
    class FakeConstraints:
        def __init__(self, **kwargs: object) -> None:
            self.__dict__.update(kwargs)

    class FakePreferences:
        def __init__(self, **kwargs: object) -> None:
            self.__dict__.update(kwargs)

    class FakeQuantumProgram:
        def __init__(self) -> None:
            self.program_id = "fake-program"
            self.synthesis_warnings = ["synthetic warning"]

        def save_results(self, filename: str | Path | None = None) -> None:
            assert filename is not None
            path = Path(filename)
            path.write_text(
                json.dumps(
                    {
                        "program_id": self.program_id,
                        "warnings": self.synthesis_warnings,
                        "width": 4,
                        "depth": 6,
                        "two_qubit_gates": 3,
                        "measure_count": 4,
                    }
                )
            )

    def qfunc(fn):
        return fn

    fake_module = SimpleNamespace(
        Output=object,
        QArray=object,
        QBit=object,
        CX=lambda *args, **kwargs: None,
        H=lambda *args, **kwargs: None,
        RX=lambda *args, **kwargs: None,
        RY=lambda *args, **kwargs: None,
        RZ=lambda *args, **kwargs: None,
        allocate=lambda *args, **kwargs: None,
        create_model=lambda entry_point, constraints=None, preferences=None: {
            "entry_point": entry_point,
            "constraints": constraints,
            "preferences": preferences,
        },
        qft=lambda *args, **kwargs: None,
        qfunc=qfunc,
        Constraints=FakeConstraints,
        Preferences=FakePreferences,
    )

    def synthesize(model, constraints=None, preferences=None):
        fake_module.last_model = model
        fake_module.last_constraints = constraints
        fake_module.last_preferences = preferences
        return FakeQuantumProgram()

    fake_module.synthesize = synthesize
    fake_module.last_model = None
    fake_module.last_constraints = None
    fake_module.last_preferences = None
    return fake_module
