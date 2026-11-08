# onsite-floor

[![CI](https://github.com/MrFR0D0/onsite-floor/actions/workflows/ci.yml/badge.svg)](https://github.com/MrFR0D0/onsite-floor/actions/workflows/ci.yml)

Self-hosted OEE and shop-floor traceability for small manufacturers.

> **Status:** early development. The project is being built step by step.

## Running the backend locally

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
cd backend
uv sync
uv run uvicorn onsite_floor.app:app --reload
```

The API is then available at http://localhost:8000, with interactive documentation at http://localhost:8000/docs and a health check at http://localhost:8000/api/health.

## Configuration

Settings are read from environment variables prefixed with `ONSITE_FLOOR_`, or from a `.env` file in the directory the app is started from. To get started:

```bash
cd backend
cp .env.example .env
```

| Variable | Values | Default | Meaning |
|---|---|---|---|
| `ONSITE_FLOOR_FASTAPI_DEBUG_MODE` | `true` / `false` | `false` | FastAPI debug mode (detailed error pages) |
| `ONSITE_FLOOR_LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | `INFO` | Minimum severity that is logged |
| `ONSITE_FLOOR_LOG_FORMAT` | `text` / `json` | `text` | Human-readable lines or one JSON object per line |

## Error format

Every error the API returns has the same JSON shape, so a frontend can handle them in one place:

```json
{"message": "Process '42' was not found", "code": "PROCESS_NOT_FOUND"}
```

`message` is for developers and logs; the frontend chooses its own user-facing text by the stable `code`. An invalid request also carries `details` with one entry per offending field:

```json
{
  "message": "Request validation failed",
  "code": "REQUEST_INVALID",
  "details": [{"field": "name", "message": "Field required"}]
}
```

| Situation | Status | `code` |
|---|---|---|
| Object does not exist | 404 | `OBJECT_NOT_FOUND` or a feature-specific code |
| Conflict with the current state | 409 | `CONFLICT` or a feature-specific code |
| Data violates a business rule | 422 | `VALIDATION_FAILED` or a feature-specific code |
| Not authenticated / not allowed | 401 / 403 | `AUTHENTICATION_REQUIRED` / `PERMISSION_DENIED` |
| External system unavailable | 502 | `GATEWAY_UNAVAILABLE` |
| Malformed request | 422 | `REQUEST_INVALID` |
| Unknown path / wrong method | 404 / 405 | `NOT_FOUND` / `METHOD_NOT_ALLOWED` |
| Unexpected failure | 500 | `INTERNAL_ERROR` (no internal details are exposed) |

## Running the tests

```bash
cd backend
uv run pytest            # run all tests
uv run pytest --cov      # with a coverage report
```

## Code quality

[Ruff](https://docs.astral.sh/ruff/) is used for linting and formatting, [mypy](https://mypy.readthedocs.io/) in strict mode for type checking.

```bash
cd backend
uv run ruff check .            # find problems
uv run ruff check . --fix      # fix what can be fixed safely
uv run ruff format .           # format the code
uv run ruff format --check .   # only check formatting
uv run mypy                    # check types
```

## License

Source-available under the [PolyForm Shield License 1.0.0](LICENSE). The source code is public and free to use, but the license does not allow using it to build a competing product. This is not an OSI-approved open-source license.
