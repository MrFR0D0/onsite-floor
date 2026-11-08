"""Domain exceptions.

They carry a human-readable message and a stable machine-readable code. The HTTP layer
(see `http_errors.py`) maps them to status codes; the domain never knows about HTTP.

Every category has a default message and code, so it can be raised without arguments.
A feature-specific subclass overrides whichever defaults it needs, and the raiser may
always pass an explicit message and code instead.
"""

from typing import ClassVar


class DomainException(Exception):  # noqa: N818 - this is the public base of the whole hierarchy
    """Base class for every error raised by business logic.

    Do not raise it directly: it has no HTTP status. Raise one of its categories or a subclass of them.
    """

    default_message: ClassVar[str] = "Unexpected domain error"
    default_code: ClassVar[str] = "DOMAIN_ERROR"

    def __init__(self, message: str | None = None, code: str | None = None) -> None:
        self.message = message if message is not None else self.default_message
        self.code = code if code is not None else self.default_code
        super().__init__(self.message)

    def __str__(self) -> str:
        return self.message


class ObjectNotFoundException(DomainException):
    """The requested object does not exist."""

    default_message = "Requested object was not found"
    default_code = "OBJECT_NOT_FOUND"


class ConflictException(DomainException):
    """The request conflicts with the current state, for example a duplicate name."""

    default_message = "Request conflicts with the current state"
    default_code = "CONFLICT"


class ValidationException(DomainException):
    """The data is well-formed but violates a business rule."""

    default_message = "Data violates a business rule"
    default_code = "VALIDATION_FAILED"


class AuthenticationException(DomainException):
    """The caller could not be identified."""

    default_message = "Authentication is required"
    default_code = "AUTHENTICATION_REQUIRED"


class AuthorizationException(DomainException):
    """The caller is identified but is not allowed to do this."""

    default_message = "Permission denied"
    default_code = "PERMISSION_DENIED"


class GatewayUnavailableException(DomainException):
    """An external system the operation depends on is unavailable."""

    default_message = "External system is unavailable"
    default_code = "GATEWAY_UNAVAILABLE"
