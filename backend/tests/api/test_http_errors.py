"""Tests for how every kind of error is turned into the uniform HTTP response."""

import logging

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from onsite_floor.app import create_app
from onsite_floor.core.exceptions import (
    AuthenticationException,
    AuthorizationException,
    ConflictException,
    DomainException,
    GatewayUnavailableException,
    ObjectNotFoundException,
    ValidationException,
)
from onsite_floor.core.settings import Settings

STATUS_BY_CATEGORY = [
    (ObjectNotFoundException, 404),
    (ConflictException, 409),
    (ValidationException, 422),
    (AuthenticationException, 401),
    (AuthorizationException, 403),
    (GatewayUnavailableException, 502),
]


class Item(BaseModel):
    """Request body used to provoke validation errors."""

    name: str


def make_client(error: Exception, *, debug: bool = False) -> TestClient:
    """Build a client for an application that has an extra route raising the given error."""
    app = create_app(Settings(fastapi_debug_mode=debug))

    @app.get("/boom")
    async def boom() -> None:
        raise error

    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def client() -> TestClient:
    """A client for an application with a route that validates its input."""
    app = create_app(Settings(fastapi_debug_mode=False))

    @app.post("/items")
    async def create_item(item: Item, limit: int = 10) -> dict[str, int]:
        return {"limit": limit, "length": len(item.name)}

    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize(("category", "status_code"), STATUS_BY_CATEGORY)
def test_domain_exception_becomes_http_response(category: type[DomainException], status_code: int) -> None:
    """Each category is answered with its own status and a `{message, code}` JSON body.

    Clients rely on the status for the kind of problem and on `code` for a stable identifier.
    """
    client = make_client(category("Nothing here", "SOME_CODE"))

    response = client.get("/boom")

    assert response.status_code == status_code, f"{category.__name__} must be answered with {status_code}"
    assert response.json() == {"message": "Nothing here", "code": "SOME_CODE"}, "Body must have message and code"


@pytest.mark.parametrize(("category", "status_code"), STATUS_BY_CATEGORY)
def test_category_without_arguments_answers_with_its_defaults(
    category: type[DomainException], status_code: int
) -> None:
    """Raised bare, a category still produces a complete answer with its fallback message and code."""
    client = make_client(category())

    response = client.get("/boom")

    assert response.status_code == status_code
    assert response.json() == {"message": category.default_message, "code": category.default_code}


def test_every_category_has_a_status_mapping() -> None:
    """A new top-level category must get an HTTP status, otherwise this test fails."""
    mapped = {category for category, _ in STATUS_BY_CATEGORY}
    # Classes declared inside other tests are also registered as subclasses until garbage collection; skip them.
    existing = {
        category for category in DomainException.__subclasses__() if category.__module__.startswith("onsite_floor.")
    }

    assert existing == mapped, "Each direct subclass of DomainException needs a status"


def test_subclass_of_a_category_uses_the_category_status() -> None:
    """A feature-specific error inherits the status of the category it derives from."""

    class ProcessNotFoundException(ObjectNotFoundException):
        """A feature-style error declared only for this test."""

        default_code = "PROCESS_NOT_FOUND"

    client = make_client(ProcessNotFoundException("Process is missing"))

    response = client.get("/boom")

    assert response.status_code == 404, "A subclass of ObjectNotFoundException must be answered with 404"
    assert response.json() == {"message": "Process is missing", "code": "PROCESS_NOT_FOUND"}


def test_invalid_request_lists_the_offending_fields(client: TestClient) -> None:
    """A request that does not match the endpoint is answered with 422 and one entry per problem."""
    response = client.post("/items", params={"limit": "many"}, json={})

    body = response.json()
    assert response.status_code == 422
    assert body["code"] == "REQUEST_INVALID"
    assert body["message"] == "Request validation failed"
    problems = {detail["field"]: detail["message"] for detail in body["details"]}
    assert set(problems) == {"limit", "name"}, f"unexpected fields: {problems}"
    assert problems["name"] == "Field required", "Pydantic's explanation must be passed on"


def test_invalid_request_logs_field_names_but_not_values(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    """The log names the offending fields so that frequent mistakes can be found, but never echoes the input."""
    caplog.set_level(logging.INFO, logger="onsite_floor.core.http_errors")

    client.post("/items", params={"limit": "secret-value"}, json={})

    messages = [record.getMessage() for record in caplog.records]
    assert len(messages) == 1, f"expected exactly one log line, got: {messages}"
    prefix, fields = messages[0].rsplit(": ", 1)
    assert prefix == "invalid request on POST /items: 2 problem(s)"
    assert set(fields.split(", ")) == {"limit", "name"}, "Both offending fields must be named in the log"
    assert "secret-value" not in caplog.text, "Values sent by the client must not reach the log"


def test_valid_request_is_not_touched(client: TestClient) -> None:
    """The handlers must not interfere with a request that is fine."""
    response = client.post("/items", params={"limit": 5}, json={"name": "abc"})

    assert response.status_code == 200
    assert response.json() == {"limit": 5, "length": 3}


def test_unknown_route_uses_the_uniform_format(client: TestClient) -> None:
    """A path nobody serves is answered in the same shape as every other error."""
    response = client.get("/no-such-route")

    assert response.status_code == 404
    assert response.json() == {"message": "Not Found", "code": "NOT_FOUND"}


def test_wrong_method_keeps_the_allow_header(client: TestClient) -> None:
    """405 keeps the `Allow` header that tells the client which methods work."""
    response = client.get("/items")

    assert response.status_code == 405
    assert response.json()["code"] == "METHOD_NOT_ALLOWED"
    assert response.headers["allow"] == "POST", "Headers of the original HTTPException must be preserved"


def test_http_exception_keeps_status_message_and_headers() -> None:
    """An `HTTPException` raised by our own code is passed through with its status, text and headers."""
    error = HTTPException(401, "Login required", headers={"WWW-Authenticate": "Bearer"})
    client = make_client(error)

    response = client.get("/boom")

    assert response.status_code == 401
    assert response.json() == {"message": "Login required", "code": "UNAUTHORIZED"}
    assert response.headers["www-authenticate"] == "Bearer"


def test_http_exception_with_a_non_standard_status() -> None:
    """A status Python does not know still gets a generic code instead of a crash."""
    client = make_client(HTTPException(299, "Odd"))

    response = client.get("/boom")

    assert response.status_code == 299
    assert response.json() == {"message": "Odd", "code": "HTTP_ERROR"}


def test_status_without_body_stays_empty() -> None:
    """204 must not carry a body, otherwise the server would break the connection."""
    client = make_client(HTTPException(204))

    response = client.get("/boom")

    assert response.status_code == 204
    assert response.content == b"", "A 204 response must have no body"


def test_unexpected_error_is_uniform_and_does_not_leak() -> None:
    """A non-domain exception becomes a plain 500 in the same shape, without its details."""
    client = make_client(RuntimeError("internal secret"))

    response = client.get("/boom")

    assert response.status_code == 500, "Unexpected errors must stay 500"
    assert response.json() == {"message": "Internal server error", "code": "INTERNAL_ERROR"}
    assert "internal secret" not in response.text, "Internal details must not reach the client"


def test_unexpected_error_is_still_raised_for_the_server_to_log() -> None:
    """After answering, Starlette raises the error again so the server logs it with its traceback."""
    app = create_app(Settings(fastapi_debug_mode=False))

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("internal secret")

    with pytest.raises(RuntimeError, match="internal secret"):
        TestClient(app).get("/boom")


def test_debug_mode_shows_the_traceback_instead() -> None:
    """With `fastapi_debug_mode` on, Starlette's debug page replaces our 500 answer, which helps in development."""
    client = make_client(RuntimeError("internal secret"), debug=True)

    response = client.get("/boom")

    assert response.status_code == 500
    assert "internal secret" in response.text, "Debug mode is expected to expose the error"
