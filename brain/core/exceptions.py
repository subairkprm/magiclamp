"""
MagicLamp Custom Exception Hierarchy
Provides structured error handling with proper HTTP status codes and clean JSON responses.
"""

from typing import Optional, Dict, Any


class MagicLampException(Exception):
    """Base exception for all MagicLamp errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to JSON-serializable dictionary."""
        result = {
            "error": self.error_code,
            "message": self.message,
            "status_code": self.status_code,
        }
        if self.details:
            result["details"] = self.details
        return result


# ── Brain/AI Exceptions ───────────────────────────
class BrainReasoningError(MagicLampException):
    """Raised when AI reasoning operations fail."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, status_code=503, error_code="BRAIN_REASONING_ERROR", details=details)


class AIEngineUnavailableError(BrainReasoningError):
    """Raised when the AI engine (Ollama) is unavailable."""

    def __init__(self, message: str = "AI Engine is currently unavailable", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, details=details)
        self.error_code = "AI_ENGINE_UNAVAILABLE"


class AITimeoutError(BrainReasoningError):
    """Raised when AI operations timeout."""

    def __init__(self, message: str = "AI operation timed out", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, details=details)
        self.error_code = "AI_TIMEOUT"


# ── Database Exceptions ────────────────────────────
class DatabaseError(MagicLampException):
    """Raised when database operations fail."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, status_code=500, error_code="DATABASE_ERROR", details=details)


class RecordNotFoundError(DatabaseError):
    """Raised when a requested record is not found."""

    def __init__(self, resource: str, identifier: str):
        super().__init__(
            message=f"{resource} not found: {identifier}", details={"resource": resource, "identifier": identifier}
        )
        self.status_code = 404
        self.error_code = "RECORD_NOT_FOUND"


class DuplicateRecordError(DatabaseError):
    """Raised when attempting to create a duplicate record."""

    def __init__(self, resource: str, field: str, value: str):
        super().__init__(
            message=f"{resource} already exists with {field}={value}",
            details={"resource": resource, "field": field, "value": value},
        )
        self.status_code = 409
        self.error_code = "DUPLICATE_RECORD"


# ── Authentication/Authorization Exceptions ────────
class AuthenticationError(MagicLampException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message=message, status_code=401, error_code="AUTHENTICATION_FAILED")


class AuthorizationError(MagicLampException):
    """Raised when user lacks required permissions."""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message=message, status_code=403, error_code="AUTHORIZATION_FAILED")


# ── Validation Exceptions ──────────────────────────
class ValidationError(MagicLampException):
    """Raised when input validation fails."""

    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        if field and not details:
            details = {"field": field}
        super().__init__(message=message, status_code=400, error_code="VALIDATION_ERROR", details=details)


# ── Integration Exceptions ─────────────────────────
class IntegrationError(MagicLampException):
    """Raised when external integration fails."""

    def __init__(self, service: str, message: str, details: Optional[Dict[str, Any]] = None):
        if not details:
            details = {}
        details["service"] = service
        super().__init__(
            message=f"{service} integration error: {message}",
            status_code=502,
            error_code="INTEGRATION_ERROR",
            details=details,
        )


class WebhookError(IntegrationError):
    """Raised when webhook delivery fails."""

    def __init__(self, webhook_url: str, message: str):
        super().__init__(service="webhook", message=message, details={"webhook_url": webhook_url})
        self.error_code = "WEBHOOK_ERROR"


# ── Task/Background Job Exceptions ─────────────────
class TaskNotFoundError(MagicLampException):
    """Raised when a background task is not found."""

    def __init__(self, task_id: str):
        super().__init__(
            message=f"Task not found: {task_id}",
            status_code=404,
            error_code="TASK_NOT_FOUND",
            details={"task_id": task_id},
        )


class TaskExecutionError(MagicLampException):
    """Raised when a background task fails during execution."""

    def __init__(self, task_id: str, message: str, details: Optional[Dict[str, Any]] = None):
        if not details:
            details = {}
        details["task_id"] = task_id
        super().__init__(
            message=f"Task execution failed: {message}",
            status_code=500,
            error_code="TASK_EXECUTION_ERROR",
            details=details,
        )
