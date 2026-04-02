"""Domain errors for Quantum Runtime."""


class QuantumRuntimeError(Exception):
    """Base exception for Quantum Runtime failures."""


class StructuredQuantumRuntimeError(QuantumRuntimeError):
    """Base error carrying a stable machine-readable code."""

    code: str = "runtime_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ManualQspecRequiredError(StructuredQuantumRuntimeError):
    """Raised when rule-based planning cannot infer a safe QSpec."""

    code = "manual_qspec_required"
