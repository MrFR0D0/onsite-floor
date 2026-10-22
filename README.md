# onsite-floor

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

## Running the tests

```bash
cd backend
uv run pytest            # run all tests
uv run pytest --cov      # with a coverage report
```

## License

Source-available under the [PolyForm Shield License 1.0.0](LICENSE). The source code is public and free to use, but the license does not allow using it to build a competing product. This is not an OSI-approved open-source license.
