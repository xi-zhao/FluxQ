from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path
from typing import Any

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ROUTER_PATH = PROJECT_ROOT / "integrations" / "cc-connect" / "bin" / "fluxq-qrun"
PROMPT_PATH = PROJECT_ROOT / "integrations" / "cc-connect" / "prompts" / "claw-system-prompt.md"


def _load_script_module(name: str, path: Path) -> Any:
    assert path.exists(), f"Missing script: {path}"
    loader = SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _tool_request(
    *,
    command: str,
    workspace_root: Path,
    args: list[str] | None = None,
    options: dict[str, Any] | None = None,
    output_mode: str | None = "json",
) -> dict[str, Any]:
    return {
        "command": command,
        "workspace_root": str(workspace_root),
        "args": args or [],
        "options": options or {},
        "output_mode": output_mode,
    }


def test_tool_router_approved_commands_cover_shipped_surface() -> None:
    module = _load_script_module("fluxq_qrun_test_router_commands", ROUTER_PATH)

    expected_commands = {
        "init",
        "prompt",
        "resolve",
        "plan",
        "status",
        "show",
        "schema",
        "baseline set",
        "baseline show",
        "baseline clear",
        "exec",
        "inspect",
        "compare",
        "doctor",
        "backend list",
        "ibm configure",
        "bench",
        "export",
        "pack",
        "pack-inspect",
        "pack-import",
        "remote submit",
    }

    assert set(module.APPROVED_COMMANDS) == expected_commands


# blocked payload contract for unshipped remote lifecycle verbs
def test_tool_router_rejects_unshipped_remote_lifecycle_verbs_with_blocked_payload(
    tmp_path: Path,
) -> None:
    module = _load_script_module("fluxq_qrun_test_router_blocked", ROUTER_PATH)

    payload = module.handle_request(
        _tool_request(
            command="remote cancel",
            workspace_root=tmp_path / ".quantum",
        )
    )

    assert payload["status"] == "blocked"
    assert payload["reason_codes"] == ["unshipped_remote_lifecycle_verb"]
    assert payload["gate"]["ready"] is False


@pytest.mark.parametrize(
    ("tool_request_payload", "expected_argv"),
    [
        (
            {
                "command": "prompt",
                "args": ["Build a 4-qubit GHZ circuit and explain it."],
                "options": {},
                "output_mode": "json",
            },
            [
                "qrun",
                "prompt",
                "Build a 4-qubit GHZ circuit and explain it.",
                "--json",
            ],
        ),
        (
            {
                "command": "plan",
                "args": [],
                "options": {
                    "intent_file": "intent.md",
                },
                "output_mode": "json",
            },
            [
                "qrun",
                "plan",
                "--intent-file",
                "intent.md",
                "--workspace",
                "__WORKSPACE__",
                "--json",
            ],
        ),
        (
            {
                "command": "exec",
                "args": [],
                "options": {
                    "intent_file": "intent.md",
                },
                "output_mode": "jsonl",
            },
            [
                "qrun",
                "exec",
                "--intent-file",
                "intent.md",
                "--workspace",
                "__WORKSPACE__",
                "--jsonl",
            ],
        ),
        (
            {
                "command": "backend list",
                "args": [],
                "options": {},
                "output_mode": "json",
            },
            [
                "qrun",
                "backend",
                "list",
                "--workspace",
                "__WORKSPACE__",
                "--json",
            ],
        ),
        (
            {
                "command": "schema",
                "args": ["report"],
                "options": {},
                "output_mode": None,
            },
            [
                "qrun",
                "schema",
                "report",
            ],
        ),
    ],
)
def test_tool_router_injects_workspace_and_machine_output_without_shelling(
    tmp_path: Path,
    tool_request_payload: dict[str, Any],
    expected_argv: list[str],
) -> None:
    module = _load_script_module("fluxq_qrun_test_router_exec", ROUTER_PATH)
    calls: list[dict[str, Any]] = []

    def _runner(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append({"argv": argv, "kwargs": kwargs})
        stdout = json.dumps({"status": "ok", "argv": argv[1:]})
        if "--jsonl" in argv:
            stdout = '{"event":"started"}\n{"event":"completed","status":"ok"}\n'
        return subprocess.CompletedProcess(argv, 0, stdout=stdout, stderr="")

    payload = module.handle_request(
        {
            **tool_request_payload,
            "workspace_root": str(tmp_path / ".quantum"),
        },
        runner=_runner,
    )

    assert payload["status"] == "ok"
    assert len(calls) == 1
    assert calls[0]["kwargs"].get("shell", False) is False
    assert calls[0]["kwargs"]["capture_output"] is True
    assert calls[0]["kwargs"]["text"] is True
    assert calls[0]["kwargs"]["check"] is False

    actual_argv = calls[0]["argv"]
    expected = [
        str(tmp_path / ".quantum") if item == "__WORKSPACE__" else item
        for item in expected_argv
    ]
    assert actual_argv == expected


def test_tool_router_requires_confirmation_for_remote_submit_without_confirmation_id(
    tmp_path: Path,
) -> None:
    module = _load_script_module("fluxq_qrun_test_router_confirmation", ROUTER_PATH)

    payload = module.handle_request(
        _tool_request(
            command="remote submit",
            workspace_root=tmp_path / ".quantum",
            options={
                "backend": "ibm_brisbane",
                "intent_file": "intent.md",
            },
        )
    )

    assert payload["status"] == "confirmation_required"
    assert payload["action"] == "remote submit"
    assert payload["input_source"] == {
        "kind": "intent_file",
        "value": "intent.md",
    }
    assert payload["workspace"] == str(tmp_path / ".quantum")
    assert payload["backend"] == "ibm_brisbane"
    assert payload["instance"] is None
    assert payload["may_create_remote_job"] is True
    assert payload["may_spend"] is True
    assert "consequence" in payload
    assert payload["approved_request"]["confirmation_id"] == payload["confirmation_id"]


@pytest.mark.parametrize("request_file", [False, True], ids=["stdin", "request_file"])
def test_tool_router_main_accepts_structured_request_from_stdin_or_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    request_file: bool,
) -> None:
    module = _load_script_module("fluxq_qrun_test_router_main", ROUTER_PATH)
    workspace_root = tmp_path / ".quantum"
    payload = _tool_request(
        command="status",
        workspace_root=workspace_root,
    )
    calls: list[list[str]] = []

    def _runner(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        return subprocess.CompletedProcess(
            argv,
            0,
            stdout=json.dumps({"status": "ok", "argv": argv[1:]}),
            stderr="",
        )

    stdin_text = json.dumps(payload)
    argv: list[str] = []
    if request_file:
        request_path = tmp_path / "request.json"
        request_path.write_text(stdin_text)
        argv = ["--request-file", str(request_path)]
        stdin_text = ""

    exit_code = module.main(argv, stdin_text=stdin_text, runner=_runner)
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["status"] == "ok"
    assert calls[0][:3] == ["qrun", "status", "--workspace"]


def test_prompt_policy_keeps_claw_conversational_and_on_fluxq_tools() -> None:
    prompt_text = PROMPT_PATH.read_text()

    assert "explanatory" in prompt_text
    assert "FluxQ" in prompt_text
    assert "qrun" in prompt_text
    assert "do not bypass" in prompt_text
    assert "remote lifecycle" in prompt_text
