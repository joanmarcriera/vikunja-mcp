"""Typed exceptions for Vikunja API interactions."""


class VikunjaError(Exception):
    """Base class for Vikunja client errors."""


class VikunjaAuthError(VikunjaError):
    """Authentication or authorization failed."""


class VikunjaNotFoundError(VikunjaError):
    """Requested resource does not exist."""


class VikunjaValidationError(VikunjaError):
    """Validation failed for request payload."""


class VikunjaConflictError(VikunjaError):
    """Conflict while mutating a resource."""


class VikunjaUnexpectedError(VikunjaError):
    """Unexpected upstream error."""
