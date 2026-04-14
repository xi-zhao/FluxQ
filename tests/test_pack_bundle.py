from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACK_MODULE_PATH = PROJECT_ROOT / "src" / "quantum_runtime" / "runtime" / "pack.py"


def _load_pack_module():
    spec = importlib.util.spec_from_file_location("pack_under_test", PACK_MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_current_pack_shape(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "intent.json").write_text(json.dumps({"schema_version": "0.3.0"}, indent=2))
    (root / "qspec.json").write_text(json.dumps({"schema_version": "0.3.0"}, indent=2))
    (root / "plan.json").write_text(json.dumps({"schema_version": "0.3.0"}, indent=2))
    (root / "report.json").write_text(json.dumps({"schema_version": "0.3.0"}, indent=2))
    (root / "manifest.json").write_text(json.dumps({"schema_version": "0.3.0"}, indent=2))
    (root / "events.jsonl").write_text('{"event_type":"exec_completed","revision":"rev_000001"}\n')
    (root / "trace.ndjson").write_text('{"event_type":"exec_completed","revision":"rev_000001"}\n')
    export_path = root / "exports" / "qasm"
    export_path.mkdir(parents=True, exist_ok=True)
    (export_path / "main.qasm").write_text("OPENQASM 3;")
    _write_bundle_manifest(root)
    return root


def _write_bundle_manifest(root: Path) -> None:
    required = {
        "intent.json",
        "qspec.json",
        "plan.json",
        "report.json",
        "manifest.json",
        "events.jsonl",
        "trace.ndjson",
    }
    entries: list[dict[str, object]] = []
    for candidate in sorted(root.rglob("*")):
        if not candidate.is_file():
            continue
        relative_path = candidate.relative_to(root).as_posix()
        if relative_path == "bundle_manifest.json":
            continue
        entries.append(
            {
                "path": relative_path,
                "required": relative_path in required or relative_path.startswith("exports/"),
                "digest": f"sha256:{_sha256_file(candidate)}",
            }
        )

    (root / "bundle_manifest.json").write_text(
        json.dumps(
            {
                "schema_version": "0.3.0",
                "revision": "rev_000001",
                "entries": entries,
            },
            indent=2,
        ),
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def test_inspect_pack_bundle_reports_ok_for_current_pack_shape(tmp_path: Path) -> None:
    pack_module = _load_pack_module()
    pack_root = _write_current_pack_shape(tmp_path / ".quantum" / "packs" / "rev_000001")

    inspection = pack_module.inspect_pack_bundle(pack_root)

    assert inspection.status == "ok"
    assert inspection.required == [
        "intent.json",
        "qspec.json",
        "plan.json",
        "report.json",
        "manifest.json",
        "bundle_manifest.json",
        "events.jsonl",
        "trace.ndjson",
        "exports/",
    ]
    assert inspection.present == inspection.required
    assert inspection.missing == []
    assert inspection.revision == "rev_000001"
    assert inspection.mismatched == []
    assert inspection.reason_codes == []
    assert inspection.gate["ready"] is True


def test_inspect_pack_bundle_reports_missing_required_objects(tmp_path: Path) -> None:
    pack_module = _load_pack_module()
    pack_root = _write_current_pack_shape(tmp_path / ".quantum" / "packs" / "rev_000001")
    (pack_root / "manifest.json").unlink()

    inspection = pack_module.inspect_pack_bundle(pack_root)

    assert inspection.status == "error"
    assert "manifest.json" in inspection.missing
    assert "exports/" not in inspection.missing


def test_inspect_pack_bundle_requires_bundle_manifest_and_trace_snapshot(tmp_path: Path) -> None:
    pack_module = _load_pack_module()
    pack_root = _write_current_pack_shape(tmp_path / ".quantum" / "packs" / "rev_000001")
    (pack_root / "bundle_manifest.json").unlink()
    (pack_root / "trace.ndjson").unlink()

    inspection = pack_module.inspect_pack_bundle(pack_root)

    assert inspection.status == "error"
    assert "bundle_manifest.json" in inspection.missing
    assert "trace.ndjson" in inspection.missing


def test_inspect_pack_bundle_reports_digest_mismatch(tmp_path: Path) -> None:
    pack_module = _load_pack_module()
    pack_root = _write_current_pack_shape(tmp_path / ".quantum" / "packs" / "rev_000001")
    (pack_root / "qspec.json").write_text(json.dumps({"schema_version": "0.3.0", "tampered": True}, indent=2))

    inspection = pack_module.inspect_pack_bundle(pack_root)

    assert inspection.status == "error"
    assert "qspec.json" in inspection.mismatched
    assert "bundle_digest_mismatch:qspec.json" in inspection.reason_codes
    assert inspection.gate["ready"] is False


def test_inspect_pack_bundle_reports_missing_bundle_manifest(tmp_path: Path) -> None:
    pack_module = _load_pack_module()
    pack_root = _write_current_pack_shape(tmp_path / ".quantum" / "packs" / "rev_000001")
    (pack_root / "bundle_manifest.json").unlink()

    inspection = pack_module.inspect_pack_bundle(pack_root)

    assert inspection.status == "error"
    assert "bundle_manifest.json" in inspection.missing
    assert "bundle_manifest_missing" in inspection.reason_codes
    assert inspection.gate["ready"] is False
