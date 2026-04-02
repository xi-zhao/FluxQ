"""Intent file parsing entrypoints."""

from __future__ import annotations

from pathlib import Path

from .markdown import parse_section_blocks, split_front_matter
from .structured import IntentModel


def parse_intent_file(path: Path) -> IntentModel:
    """Parse an intent markdown file from disk."""
    return parse_intent_text(path.read_text())


def parse_intent_text(text: str) -> IntentModel:
    """Parse markdown-plus-front-matter into a normalized intent model."""
    front_matter, body = split_front_matter(text)
    sections = parse_section_blocks(body)

    goal = sections.get("goal") or body.strip()
    if not goal:
        raise ValueError("Intent must define a goal.")

    return IntentModel(
        title=_as_optional_str(front_matter.get("title")),
        goal=goal,
        exports=_as_string_list(front_matter.get("exports"), default=["qiskit", "qasm3"]),
        backend_preferences=_as_string_list(
            front_matter.get("backend_preferences"),
            default=["qiskit-local"],
        ),
        constraints=_as_dict(front_matter.get("constraints")),
        shots=_as_int(front_matter.get("shots"), default=1024),
        notes=sections.get("notes"),
    )


def _as_optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _as_string_list(value: object, default: list[str]) -> list[str]:
    if value is None:
        return list(default)
    if not isinstance(value, list):
        raise ValueError("Expected a list value in intent front matter.")
    return [str(item) for item in value]


def _as_dict(value: object) -> dict[str, object]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("Expected a mapping for intent constraints.")
    return {str(key): item for key, item in value.items()}


def _as_int(value: object, default: int) -> int:
    if value is None:
        return default
    return int(value)
