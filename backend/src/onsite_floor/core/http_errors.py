"""Translation of every kind of error into one uniform HTTP response.

Whatever goes wrong, the client receives the same JSON shape::

    {"message": "Human-readable text", "code": "STABLE_MACHINE_CODE", "details": [...]}

`details` appears only when there is something to add; for an invalid request it lists the
offending fields as `{"field": ..., "message": ...}`. The frontend picks its own text by `code`.
"""

import logging
from collections.abc import Awaitable, Callable, Mapping, Sequence
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

from onsite_floor.core.exceptions import (
    AuthenticationException,
    AuthorizationException,
    ConflictException,
    DomainException,
    GatewayUnavailableException,
    ObjectNotFoundException,
    ValidationException,
)

logger = logging.getLogger(__name__)

type ErrorHandler = Callable[[Request, Exception], Awaitable[Response]]

# TODO: extend this table when the project gets external integrations and authentication.
# Today every category is logged at INFO in `_make_handler`. Store a log level next to each
# status instead, for example `category -> (status, level)`: 401/403 deserve WARNING (repeated
# refusals can mean an access-guessing attempt) and 502 deserves WARNING (an external system we
# depend on is failing, which is a signal for the operator), while 404/409/422 stay at INFO.
_STATUS_BY_EXCEPTION: dict[type[DomainException], int] = {
    ObjectNotFoundException: 404,
    ConflictException: 409,
    ValidationException: 422,
    AuthenticationException: 401,
    AuthorizationException: 403,
    GatewayUnavailableException: 502,
}

# Parts of a request that Pydantic puts first in an error location, for example ("query", "limit").
_REQUEST_PARTS = frozenset({"body", "query", "path", "header", "cookie"})

# HTTP statuses whose responses must not have a body.
_NO_BODY_STATUSES = frozenset({204, 304})


def add_exception_handlers(app: FastAPI) -> None:
    """Make every error the application can produce answer in the uniform format.

    Args:
        app: The FastAPI application to attach the handlers to.
    """
    for exception_type, status_code in _STATUS_BY_EXCEPTION.items():
        app.add_exception_handler(exception_type, _make_handler(status_code))
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
    app.add_exception_handler(Exception, _handle_unexpected_error)


def _error_response(
    status_code: int,
    message: str,
    code: str,
    details: list[dict[str, str]] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    """Build the uniform error body; `details` is included only when given."""
    content: dict[str, Any] = {"message": message, "code": code}
    if details is not None:
        content["details"] = details
    return JSONResponse(status_code=status_code, content=content, headers=headers)


def _make_handler(status_code: int) -> ErrorHandler:
    async def handler(request: Request, exc: Exception) -> Response:
        if not isinstance(exc, DomainException):
            # Unreachable: only DomainException subclasses are registered. Re-raise rather than guess.
            raise exc
        logger.info("domain error %s on %s %s", exc.code, request.method, request.url.path)
        return _error_response(status_code, exc.message, exc.code)

    return handler


async def _handle_validation_error(request: Request, exc: Exception) -> Response:
    """Answer a request that does not match the endpoint's parameters or body."""
    if not isinstance(exc, RequestValidationError):
        raise exc
    details = [{"field": _field_name(error["loc"]), "message": error["msg"]} for error in exc.errors()]
    # Field names are part of our API and safe to log; the values sent by the client are not logged.
    fields = ", ".join(detail["field"] for detail in details)
    logger.info("invalid request on %s %s: %d problem(s): %s", request.method, request.url.path, len(details), fields)
    return _error_response(422, "Request validation failed", "REQUEST_INVALID", details)


async def _handle_http_exception(request: Request, exc: Exception) -> Response:
    """Answer errors raised by the framework (unknown route, wrong method) or by `HTTPException`."""
    if not isinstance(exc, StarletteHTTPException):
        raise exc
    if exc.status_code in _NO_BODY_STATUSES:
        return Response(status_code=exc.status_code, headers=exc.headers)
    code, phrase = _describe_status(exc.status_code)
    message = exc.detail if isinstance(exc.detail, str) else phrase
    logger.info("http error %s on %s %s", code, request.method, request.url.path)
    return _error_response(exc.status_code, message, code, headers=exc.headers)


async def _handle_unexpected_error(_request: Request, _exc: Exception) -> Response:
    """Answer any error nobody expected, without revealing what it was.

    Nothing is logged here: after sending this response Starlette raises the error again,
    and the server logs it together with the traceback.
    """
    return _error_response(500, "Internal server error", "INTERNAL_ERROR")


def _field_name(location: Sequence[int | str]) -> str:
    """Turn a Pydantic error location into a field name: `("body", "items", 0, "qty")` -> `items.0.qty`."""
    parts = location[1:] if location and location[0] in _REQUEST_PARTS else location
    return ".".join(str(part) for part in parts) or ".".join(str(part) for part in location)


def _describe_status(status_code: int) -> tuple[str, str]:
    """Return the code and the standard phrase for a status: 404 -> `("NOT_FOUND", "Not Found")`."""
    try:
        status = HTTPStatus(status_code)
    except ValueError:
        return "HTTP_ERROR", "HTTP error"
    return status.name, status.phrase
