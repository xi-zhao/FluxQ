from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from quantum_runtime.cli import app


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNNER = CliRunner()


def test_qrun_init_json_creates_manifest_layout_and_schema_version(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    result = RUNNER.invoke(
        app,
        ["init", "--workspace", str(workspace), "--json"],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "0.3.0"
    assert payload["status"] == "ok"
    assert (workspace / "manifests").is_dir()
    assert (workspace / "manifests" / "history").is_dir()


def test_qrun_exec_json_writes_manifest_artifact_and_schema_versions(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(workspace),
            "--intent-file",
            str(PROJECT_ROOT / "examples" / "intent-ghz.md"),
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    revision = payload["revision"]
    assert payload["schema_version"] == "0.3.0"
    assert payload["artifacts"]["manifest"].endswith(f"manifests/history/{revision}.json")

    qspec_payload = json.loads((workspace / "specs" / "current.json").read_text())
    report_payload = json.loads((workspace / "reports" / "latest.json").read_text())
    manifest_payload = json.loads((workspace / "manifests" / "latest.json").read_text())

    assert qspec_payload["schema_version"] == "0.3.0"
    assert qspec_payload["version"] == "0.1"
    assert report_payload["schema_version"] == "0.3.0"
    assert manifest_payload["schema_version"] == "0.3.0"
    assert manifest_payload["revision"] == revision
    assert manifest_payload["qspec"]["path"] == report_payload["qspec"]["path"]
    assert manifest_payload["report"]["path"] == str(workspace / "reports" / "history" / f"{revision}.json")
    assert manifest_payload["artifacts"]["qiskit_code"]["path"].endswith(
        f"artifacts/history/{revision}/qiskit/main.py"
    )
    assert manifest_payload["artifacts"]["qasm3"]["path"].endswith(
        f"artifacts/history/{revision}/qasm/main.qasm"
    )


def test_qrun_plan_json_is_dry_run_and_returns_machine_plan(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    result = RUNNER.invoke(
        app,
        [
            "plan",
            "--workspace",
            str(workspace),
            "--intent-file",
            str(PROJECT_ROOT / "examples" / "intent-ghz.md"),
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "0.3.0"
    assert payload["status"] == "ok"
    assert payload["input"]["mode"] == "intent"
    assert payload["qspec"]["pattern"] == "ghz"
    assert payload["execution"]["selected_backends"] == ["qiskit-local"]
    assert "qspec" in payload["artifacts_expected"]
    assert "report" in payload["artifacts_expected"]
    assert "manifest" in payload["artifacts_expected"]
    assert payload["policy"]["baseline_configured"] is False
    assert payload["blockers"] == []
    assert not workspace.exists()


def test_qrun_plan_json_flags_unknown_backend_as_blocker(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"
    qspec_path = tmp_path / "unknown-backend.json"
    qspec_path.write_text(
        json.dumps(
            {
                "schema_version": "0.3.0",
                "version": "0.1",
                "program_id": "prog_ghz_4",
                "goal": "Generate a 4-qubit GHZ circuit and measure all qubits.",
                "entrypoint": "main",
                "registers": [
                    {"kind": "qubit", "name": "q", "size": 4},
                    {"kind": "cbit", "name": "c", "size": 4},
                ],
                "parameters": [],
                "body": [
                    {"kind": "pattern", "pattern": "ghz", "args": {"register": "q", "size": 4}},
                    {
                        "kind": "measure",
                        "qubits": ["q[0]", "q[1]", "q[2]", "q[3]"],
                        "cbits": ["c[0]", "c[1]", "c[2]", "c[3]"],
                    },
                ],
                "observables": [],
                "constraints": {"shots": 1024, "optimization_level": 2},
                "backend_preferences": ["mystery-backend"],
                "metadata": {"source": "intent"},
            },
            indent=2,
        )
    )

    result = RUNNER.invoke(
        app,
        [
            "plan",
            "--workspace",
            str(workspace),
            "--qspec-file",
            str(qspec_path),
            "--json",
        ],
    )

    assert result.exit_code == 2, result.stdout
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "0.3.0"
    assert payload["status"] == "degraded"
    assert payload["execution"]["selected_backends"] == ["qiskit-local", "mystery-backend"]
    assert payload["blockers"] == ["unknown backend requested: mystery-backend"]


def test_qrun_plan_json_returns_machine_error_for_invalid_qspec_file(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"
    qspec_path = tmp_path / "invalid-qspec.json"
    qspec_path.write_text(json.dumps({"schema_version": "0.3.0"}))

    result = RUNNER.invoke(
        app,
        [
            "plan",
            "--workspace",
            str(workspace),
            "--qspec-file",
            str(qspec_path),
            "--json",
        ],
    )

    assert result.exit_code == 3, result.stdout
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "0.3.0"
    assert payload["status"] == "error"
    assert payload["reason"] == "invalid_qspec"
    assert payload["error_code"] == "invalid_qspec"


def test_qrun_plan_json_returns_machine_error_for_semantically_invalid_qspec(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"
    qspec_path = tmp_path / "semantic-invalid-qspec.json"
    qspec_path.write_text(
        json.dumps(
            {
                "schema_version": "0.3.0",
                "version": "0.1",
                "program_id": "prog_bad_2",
                "goal": "Bad QSpec",
                "entrypoint": "main",
                "registers": [
                    {"kind": "qubit", "name": "q", "size": 2},
                    {"kind": "cbit", "name": "c", "size": 2},
                ],
                "parameters": [],
                "observables": [],
                "body": [
                    {"kind": "pattern", "pattern": "ghz", "args": {"register": "q", "size": 2}},
                ],
                "constraints": {"shots": 1024, "optimization_level": 2},
                "backend_preferences": ["qiskit-local"],
                "metadata": {"source": "intent"},
            }
        )
    )

    result = RUNNER.invoke(
        app,
        [
            "plan",
            "--workspace",
            str(workspace),
            "--qspec-file",
            str(qspec_path),
            "--json",
        ],
    )

    assert result.exit_code == 3, result.stdout
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "0.3.0"
    assert payload["status"] == "error"
    assert payload["reason"] == "invalid_qspec"
    assert payload["error_code"] == "invalid_qspec"


def test_qrun_plan_json_returns_machine_error_for_invalid_revision_qspec(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    exec_result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(workspace),
            "--intent-file",
            str(PROJECT_ROOT / "examples" / "intent-ghz.md"),
            "--json",
        ],
    )
    assert exec_result.exit_code == 0, exec_result.stdout

    history_qspec = workspace / "specs" / "history" / "rev_000001.json"
    qspec_payload = json.loads(history_qspec.read_text())
    qspec_payload["body"] = [qspec_payload["body"][0]]
    history_qspec.write_text(json.dumps(qspec_payload, indent=2))

    result = RUNNER.invoke(
        app,
        [
            "plan",
            "--workspace",
            str(workspace),
            "--revision",
            "rev_000001",
            "--json",
        ],
    )

    assert result.exit_code == 3, result.stdout
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "0.3.0"
    assert payload["status"] == "error"
    assert payload["reason"] == "report_qspec_hash_mismatch"
    assert payload["error_code"] == "report_qspec_hash_mismatch"


def test_qrun_plan_json_returns_machine_error_for_manual_qspec_requirement(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"
    intent_path = tmp_path / "unsupported-intent.md"
    intent_path.write_text(
        """---
title: Unsupported intent
---

Design a novel quantum walk experiment.
"""
    )

    result = RUNNER.invoke(
        app,
        [
            "plan",
            "--workspace",
            str(workspace),
            "--intent-file",
            str(intent_path),
            "--json",
        ],
    )

    assert result.exit_code == 3, result.stdout
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "0.3.0"
    assert payload["status"] == "error"
    assert payload["reason"] == "manual_qspec_required"
    assert payload["error_code"] == "manual_qspec_required"


def test_qrun_status_json_reports_workspace_health_and_baseline(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    exec_result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(workspace),
            "--intent-file",
            str(PROJECT_ROOT / "examples" / "intent-ghz.md"),
            "--json",
        ],
    )
    assert exec_result.exit_code == 0, exec_result.stdout

    baseline_result = RUNNER.invoke(
        app,
        [
            "baseline",
            "set",
            "--workspace",
            str(workspace),
            "--revision",
            "rev_000001",
            "--json",
        ],
    )
    assert baseline_result.exit_code == 0, baseline_result.stdout

    result = RUNNER.invoke(
        app,
        ["status", "--workspace", str(workspace), "--json"],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "0.3.0"
    assert payload["status"] == "ok"
    assert payload["workspace"]["exists"] is True
    assert payload["workspace"]["initialized"] is True
    assert payload["current_revision"] == "rev_000001"
    assert payload["active"]["qspec"]["exists"] is True
    assert payload["active"]["report"]["exists"] is True
    assert payload["active"]["manifest"]["exists"] is True
    assert payload["latest_run_status"] == "ok"
    assert payload["baseline"]["configured"] is True
    assert payload["baseline"]["revision"] == "rev_000001"
    assert payload["degraded"] is False


def test_qrun_status_json_reports_invalid_baseline_as_degraded(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    exec_result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(workspace),
            "--intent-file",
            str(PROJECT_ROOT / "examples" / "intent-ghz.md"),
            "--json",
        ],
    )
    assert exec_result.exit_code == 0, exec_result.stdout

    baseline_result = RUNNER.invoke(
        app,
        [
            "baseline",
            "set",
            "--workspace",
            str(workspace),
            "--revision",
            "rev_000001",
            "--json",
        ],
    )
    assert baseline_result.exit_code == 0, baseline_result.stdout

    (workspace / "baselines" / "current.json").write_text('{"broken":')

    result = RUNNER.invoke(
        app,
        ["status", "--workspace", str(workspace), "--json"],
    )

    assert result.exit_code == 2, result.stdout
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "0.3.0"
    assert payload["status"] == "degraded"
    assert payload["baseline"]["status"] == "degraded"
    assert payload["baseline"]["reason"] == "baseline_invalid"
    assert payload["degraded"] is True


def test_qrun_plan_json_reports_invalid_baseline_as_not_compare_ready(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    exec_result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(workspace),
            "--intent-file",
            str(PROJECT_ROOT / "examples" / "intent-ghz.md"),
            "--json",
        ],
    )
    assert exec_result.exit_code == 0, exec_result.stdout

    baseline_result = RUNNER.invoke(
        app,
        [
            "baseline",
            "set",
            "--workspace",
            str(workspace),
            "--revision",
            "rev_000001",
            "--json",
        ],
    )
    assert baseline_result.exit_code == 0, baseline_result.stdout

    (workspace / "baselines" / "current.json").write_text('{"broken":')

    result = RUNNER.invoke(
        app,
        [
            "plan",
            "--workspace",
            str(workspace),
            "--intent-file",
            str(PROJECT_ROOT / "examples" / "intent-ghz.md"),
            "--json",
        ],
    )

    assert result.exit_code == 2, result.stdout
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "0.3.0"
    assert payload["status"] == "degraded"
    assert payload["policy"]["baseline_configured"] is True
    assert payload["policy"]["compare_ready"] is False
    assert "baseline_invalid:baseline_invalid" in payload["advisories"]


def test_qrun_show_json_supports_revision_lookup_and_baseline_relation(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    first = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(workspace),
            "--intent-file",
            str(PROJECT_ROOT / "examples" / "intent-ghz.md"),
            "--json",
        ],
    )
    assert first.exit_code == 0, first.stdout

    set_baseline = RUNNER.invoke(
        app,
        [
            "baseline",
            "set",
            "--workspace",
            str(workspace),
            "--revision",
            "rev_000001",
            "--json",
        ],
    )
    assert set_baseline.exit_code == 0, set_baseline.stdout

    second = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(workspace),
            "--intent-file",
            str(PROJECT_ROOT / "examples" / "intent-qaoa-maxcut.md"),
            "--json",
        ],
    )
    assert second.exit_code == 0, second.stdout

    latest_result = RUNNER.invoke(
        app,
        ["show", "--workspace", str(workspace), "--json"],
    )
    assert latest_result.exit_code == 0, latest_result.stdout
    latest_payload = json.loads(latest_result.stdout)
    assert latest_payload["revision"] == "rev_000002"
    assert latest_payload["baseline_relation"]["configured"] is True
    assert latest_payload["baseline_relation"]["matches_baseline"] is False

    revision_result = RUNNER.invoke(
        app,
        ["show", "--workspace", str(workspace), "--revision", "rev_000001", "--json"],
    )

    assert revision_result.exit_code == 0, revision_result.stdout
    payload = json.loads(revision_result.stdout)
    assert payload["schema_version"] == "0.3.0"
    assert payload["status"] == "ok"
    assert payload["revision"] == "rev_000001"
    assert payload["manifest"]["revision"] == "rev_000001"
    assert payload["qspec_summary"]["pattern"] == "ghz"
    assert payload["baseline_relation"]["configured"] is True
    assert payload["baseline_relation"]["baseline_revision"] == "rev_000001"
    assert payload["baseline_relation"]["matches_baseline"] is True


def test_qrun_status_json_reports_invalid_latest_manifest(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    exec_result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(workspace),
            "--intent-file",
            str(PROJECT_ROOT / "examples" / "intent-ghz.md"),
            "--json",
        ],
    )
    assert exec_result.exit_code == 0, exec_result.stdout

    latest_manifest = workspace / "manifests" / "latest.json"
    history_manifest = workspace / "manifests" / "history" / "rev_000001.json"
    latest_manifest.write_text('{"broken":')
    history_manifest.write_text('{"broken":')

    result = RUNNER.invoke(
        app,
        ["status", "--workspace", str(workspace), "--json"],
    )

    assert result.exit_code == 3, result.stdout
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "0.3.0"
    assert payload["status"] == "error"
    assert "active_manifest_invalid" in payload["errors"]
    assert payload["degraded"] is True


def test_qrun_status_json_reports_invalid_active_qspec(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    exec_result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(workspace),
            "--intent-file",
            str(PROJECT_ROOT / "examples" / "intent-ghz.md"),
            "--json",
        ],
    )
    assert exec_result.exit_code == 0, exec_result.stdout

    (workspace / "specs" / "current.json").write_text('{"broken":')

    result = RUNNER.invoke(
        app,
        ["status", "--workspace", str(workspace), "--json"],
    )

    assert result.exit_code == 3, result.stdout
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "0.3.0"
    assert payload["status"] == "error"
    assert "active_qspec_invalid" in payload["errors"]
    assert payload["active"]["qspec"]["status"] == "invalid"


def test_qrun_status_json_reports_invalid_active_report(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    exec_result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(workspace),
            "--intent-file",
            str(PROJECT_ROOT / "examples" / "intent-ghz.md"),
            "--json",
        ],
    )
    assert exec_result.exit_code == 0, exec_result.stdout

    (workspace / "reports" / "latest.json").write_text('{"broken":')

    result = RUNNER.invoke(
        app,
        ["status", "--workspace", str(workspace), "--json"],
    )

    assert result.exit_code == 3, result.stdout
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "0.3.0"
    assert payload["status"] == "error"
    assert "active_report_invalid" in payload["errors"]
    assert payload["active"]["report"]["status"] == "invalid"


def test_qrun_show_json_fails_closed_for_invalid_run_manifest(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    exec_result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(workspace),
            "--intent-file",
            str(PROJECT_ROOT / "examples" / "intent-ghz.md"),
            "--json",
        ],
    )
    assert exec_result.exit_code == 0, exec_result.stdout

    latest_manifest = workspace / "manifests" / "latest.json"
    history_manifest = workspace / "manifests" / "history" / "rev_000001.json"
    latest_manifest.write_text('{"broken":')
    history_manifest.write_text('{"broken":')

    result = RUNNER.invoke(
        app,
        ["show", "--workspace", str(workspace), "--json"],
    )

    assert result.exit_code == 3, result.stdout
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "0.3.0"
    assert payload["status"] == "error"
    assert payload["reason"] == "run_manifest_invalid"
    assert payload["error_code"] == "run_manifest_invalid"


def test_qrun_show_json_synthesizes_legacy_manifest_when_manifest_files_are_absent(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    exec_result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(workspace),
            "--intent-file",
            str(PROJECT_ROOT / "examples" / "intent-ghz.md"),
            "--json",
        ],
    )
    assert exec_result.exit_code == 0, exec_result.stdout

    (workspace / "manifests" / "latest.json").unlink()
    (workspace / "manifests" / "history" / "rev_000001.json").unlink()

    latest_report_path = workspace / "reports" / "latest.json"
    history_report_path = workspace / "reports" / "history" / "rev_000001.json"
    latest_report = json.loads(latest_report_path.read_text())
    history_report = json.loads(history_report_path.read_text())
    latest_report.pop("schema_version", None)
    history_report.pop("schema_version", None)
    latest_report_path.write_text(json.dumps(latest_report, indent=2))
    history_report_path.write_text(json.dumps(history_report, indent=2))

    result = RUNNER.invoke(
        app,
        ["show", "--workspace", str(workspace), "--json"],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "0.3.0"
    assert payload["status"] == "ok"
    assert payload["manifest"]["revision"] == "rev_000001"
    assert payload["manifest"]["report"]["path"] == str(history_report_path)


def test_qrun_status_json_reports_stale_or_tampered_manifest_integrity(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    first = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(workspace),
            "--intent-file",
            str(PROJECT_ROOT / "examples" / "intent-ghz.md"),
            "--json",
        ],
    )
    assert first.exit_code == 0, first.stdout

    second = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(workspace),
            "--intent-file",
            str(PROJECT_ROOT / "examples" / "intent-qaoa-maxcut.md"),
            "--json",
        ],
    )
    assert second.exit_code == 0, second.stdout

    stale_manifest = json.loads((workspace / "manifests" / "history" / "rev_000001.json").read_text())
    (workspace / "manifests" / "latest.json").write_text(json.dumps(stale_manifest, indent=2))

    result = RUNNER.invoke(
        app,
        ["status", "--workspace", str(workspace), "--json"],
    )

    assert result.exit_code == 3, result.stdout
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "0.3.0"
    assert payload["status"] == "error"
    assert "active_manifest_integrity_invalid" in payload["errors"]
    assert payload["degraded"] is True


def test_qrun_show_json_fails_closed_for_manifest_hash_mismatch(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    exec_result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(workspace),
            "--intent-file",
            str(PROJECT_ROOT / "examples" / "intent-ghz.md"),
            "--json",
        ],
    )
    assert exec_result.exit_code == 0, exec_result.stdout

    manifest_path = workspace / "manifests" / "history" / "rev_000001.json"
    latest_manifest_path = workspace / "manifests" / "latest.json"
    manifest_payload = json.loads(manifest_path.read_text())
    manifest_payload["qspec"]["hash"] = "sha256:deadbeef"
    serialized = json.dumps(manifest_payload, indent=2)
    manifest_path.write_text(serialized)
    latest_manifest_path.write_text(serialized)

    result = RUNNER.invoke(
        app,
        ["show", "--workspace", str(workspace), "--json"],
    )

    assert result.exit_code == 3, result.stdout
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "0.3.0"
    assert payload["status"] == "error"
    assert payload["reason"] == "run_manifest_integrity_invalid"
    assert payload["error_code"] == "run_manifest_integrity_invalid"


def test_qrun_schema_json_returns_named_schema_with_schema_version_field() -> None:
    result = RUNNER.invoke(
        app,
        ["schema", "manifest"],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "0.3.0"
    assert payload["status"] == "ok"
    assert payload["name"] == "manifest"
    assert payload["schema"]["type"] == "object"
    assert "schema_version" in payload["schema"]["properties"]


def test_existing_machine_outputs_include_schema_version(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    exec_result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(workspace),
            "--intent-file",
            str(PROJECT_ROOT / "examples" / "intent-ghz.md"),
            "--json",
        ],
    )
    assert exec_result.exit_code == 0, exec_result.stdout
    exec_payload = json.loads(exec_result.stdout)
    assert exec_payload["schema_version"] == "0.3.0"

    baseline_result = RUNNER.invoke(
        app,
        [
            "baseline",
            "set",
            "--workspace",
            str(workspace),
            "--revision",
            "rev_000001",
            "--json",
        ],
    )
    assert baseline_result.exit_code == 0, baseline_result.stdout
    assert json.loads(baseline_result.stdout)["schema_version"] == "0.3.0"

    compare_result = RUNNER.invoke(
        app,
        ["compare", "--workspace", str(workspace), "--baseline", "--json"],
    )
    assert compare_result.exit_code == 0, compare_result.stdout
    assert json.loads(compare_result.stdout)["schema_version"] == "0.3.0"

    export_result = RUNNER.invoke(
        app,
        ["export", "--workspace", str(workspace), "--format", "qasm3", "--json"],
    )
    assert export_result.exit_code == 0, export_result.stdout
    assert json.loads(export_result.stdout)["schema_version"] == "0.3.0"

    inspect_result = RUNNER.invoke(
        app,
        ["inspect", "--workspace", str(workspace), "--json"],
    )
    assert inspect_result.exit_code == 0, inspect_result.stdout
    assert json.loads(inspect_result.stdout)["schema_version"] == "0.3.0"

    doctor_result = RUNNER.invoke(
        app,
        ["doctor", "--workspace", str(workspace), "--json"],
    )
    assert doctor_result.exit_code == 0, doctor_result.stdout
    assert json.loads(doctor_result.stdout)["schema_version"] == "0.3.0"

    backend_list_result = RUNNER.invoke(
        app,
        ["backend", "list", "--json"],
    )
    assert backend_list_result.exit_code == 0, backend_list_result.stdout
    assert json.loads(backend_list_result.stdout)["schema_version"] == "0.3.0"
