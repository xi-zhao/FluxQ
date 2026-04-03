"""ASCII and PNG diagram generation."""

from __future__ import annotations

from pathlib import Path

from matplotlib import pyplot as plt
from pydantic import BaseModel

from quantum_runtime.lowering.qiskit_emitter import build_qiskit_circuit
from quantum_runtime.qspec import QSpec
from quantum_runtime.workspace.manager import WorkspaceHandle


class DiagramArtifacts(BaseModel):
    """Paths to generated diagram artifacts."""

    text_path: Path
    png_path: Path


def write_diagrams(
    qspec: QSpec,
    workspace: WorkspaceHandle,
    *,
    parameter_bindings: dict[str, float] | None = None,
) -> DiagramArtifacts:
    """Write `circuit.txt` and `circuit.png` into the workspace figures directory."""
    circuit = build_qiskit_circuit(qspec, parameter_bindings=parameter_bindings)
    text_path = workspace.root / "figures" / "circuit.txt"
    png_path = workspace.root / "figures" / "circuit.png"

    text_diagram = str(circuit.draw(output="text"))
    text_path.write_text(text_diagram)

    fig = plt.figure(figsize=(12, max(2, text_diagram.count("\n") * 0.35)))
    fig.text(
        0.01,
        0.99,
        text_diagram,
        ha="left",
        va="top",
        family="monospace",
        fontsize=10,
    )
    plt.axis("off")
    fig.savefig(png_path, dpi=200, bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)

    return DiagramArtifacts(text_path=text_path, png_path=png_path)
