class Bug2EvalError(Exception):
    """Base exception for user-facing Bug2Eval failures."""

class CaseValidationError(Bug2EvalError):
    """Raised when an eval case is malformed or fails integrity checks."""

class CommandExecutionError(Bug2EvalError):
    """Raised when an external command cannot be executed."""
