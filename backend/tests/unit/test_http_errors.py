"""Unit tests for the internals of the HTTP error handlers."""

import asyncio
from collections.abc import Sequence

import pytest
from fastapi import Request
from fastapi.responses import Response

from onsite_floor.core.http_errors import (
    ErrorHandler,
    _field_name,
    _handle_http_exception,
    _handle_validation_error,
    _make_handler,
)


@pytest.mark.parametrize(
    "handler",
    [_make_handler(404), _handle_validation_error, _handle_http_exception],
    ids=["domain", "validation", "http"],
)
def test_handler_reraises_errors_it_was_not_meant_for(handler: ErrorHandler) -> None:
    """A handler refuses to answer for an exception of a foreign type.

    Each handler is registered for one kind of error, so this is a safety net: if it ever happens,
    the original error must surface instead of being turned into a misleading response.
    """
    request = Request({"type": "http", "method": "GET", "path": "/"})

    async def call_handler() -> Response:
        return await handler(request, RuntimeError("unexpected"))

    with pytest.raises(RuntimeError, match="unexpected"):
        asyncio.run(call_handler())


@pytest.mark.parametrize(
    ("location", "expected"),
    [
        (("body", "name"), "name"),
        (("query", "limit"), "limit"),
        (("path", "process_id"), "process_id"),
        (("body", "items", 0, "quantity"), "items.0.quantity"),
        (("body",), "body"),
        (("name",), "name"),
    ],
)
def test_field_name_drops_the_request_part(location: Sequence[int | str], expected: str) -> None:
    """The field name is the dotted path inside the request, without the leading body/query/path marker."""
    assert _field_name(location) == expected, f"{location!r} must become {expected!r}"
