"""Markdown parsing helpers for intent files."""

from __future__ import annotations

from collections import OrderedDict

import yaml


def split_front_matter(text: str) -> tuple[dict[str, object], str]:
    """Split markdown text into YAML front matter and markdown body."""
    if not text.startswith("---\n"):
        return {}, text.strip()

    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        return {}, text.strip()

    _, remainder = parts
    header = parts[0][4:]
    data = yaml.safe_load(header) or {}
    if not isinstance(data, dict):
        raise ValueError("Intent front matter must decode to a mapping.")

    return data, remainder.strip()


def parse_section_blocks(body: str) -> OrderedDict[str, str]:
    """Parse top-level markdown headings into named text blocks."""
    sections: OrderedDict[str, str] = OrderedDict()
    current_name: str | None = None
    current_lines: list[str] = []

    for line in body.splitlines():
        if line.startswith("# "):
            if current_name is not None:
                sections[current_name] = "\n".join(current_lines).strip()
            current_name = line[2:].strip().lower()
            current_lines = []
            continue

        current_lines.append(line)

    if current_name is not None:
        sections[current_name] = "\n".join(current_lines).strip()

    return sections
