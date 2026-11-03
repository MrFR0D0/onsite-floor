"""Tests that every logger of the project and of its dependencies reaches our root handler.

The configuration promises a single place where all log records come out in one format. That promise
breaks silently when a library switches off its loggers, stops records from travelling upwards
(`propagate=False`) or attaches handlers of its own. These tests turn such a case into a failing test,
for example after a dependency upgrade.

Limit: only loggers that already exist are visible. Libraries that create a logger lazily, at first use,
cannot be seen here.
"""

import importlib
import importlib.metadata
import logging
import logging.config
import re
from collections.abc import Iterator

import pytest
import uvicorn.config

from onsite_floor.core.logging import configure_logging
from onsite_floor.core.settings import Settings

pytestmark = pytest.mark.usefixtures("restore_logging")

FAKE_PREFIX = "audit_fake"


def find_undelivered_loggers() -> list[str]:
    """Describe every known logger whose records would not end up in the root handler.

    Returns:
        One line per problem; an empty list means that every logger delivers to the root.
    """
    problems: list[str] = []
    manager = logging.root.manager
    if manager.disable != logging.NOTSET:
        problems.append(f"logging.disable({manager.disable}) is active: records up to that level are dropped")
    for name, item in sorted(manager.loggerDict.items()):
        if not isinstance(item, logging.Logger):
            continue  # a placeholder: an intermediate node nobody created explicitly
        if item.disabled:
            problems.append(f"{name}: logger is disabled, its records are dropped")
        node: logging.Logger | None = item
        while node is not None and node is not logging.root:
            # NullHandler is the library convention for "no output of my own", it is harmless
            foreign = [handler for handler in node.handlers if not isinstance(handler, logging.NullHandler)]
            if foreign:
                problems.append(f"{name}: records are also written by handlers of '{node.name}': {foreign}")
            if not node.propagate:
                problems.append(f"{name}: propagate=False on '{node.name}', records never reach the root")
                break
            node = node.parent
    return problems


def normalize(distribution_name: str) -> str:
    """Bring a distribution name to the canonical form (`Pydantic_Settings` -> `pydantic-settings`)."""
    return re.sub(r"[-_.]+", "-", distribution_name).lower()


def dependency_modules() -> list[str]:
    """Return the top-level import names of the runtime dependencies declared in `pyproject.toml`."""
    wanted: set[str] = set()
    for requirement in importlib.metadata.requires("onsite-floor") or []:
        if "extra ==" in requirement:
            continue
        wanted.add(normalize(re.split(r"[\s;<>=!~\[(]", requirement, maxsplit=1)[0]))
    return sorted(
        module
        for module, distributions in importlib.metadata.packages_distributions().items()
        if any(normalize(distribution) in wanted for distribution in distributions)
    )


@pytest.fixture
def fake_logger_names() -> Iterator[list[str]]:
    """Collect the names of loggers a test invents and remove them afterwards, so they do not leak."""
    names: list[str] = []
    yield names
    for name in names:
        logging.root.manager.loggerDict.pop(name, None)


def test_every_logger_reaches_the_root_handler() -> None:
    """After startup and our configuration, no known logger is cut off from the root handler.

    The dependencies are imported first so that they create their loggers. Then the test repeats what
    really happens at start: uvicorn applies its own logging configuration, after which we apply ours.
    New dependencies are picked up automatically from `pyproject.toml`.
    """
    for module in dependency_modules():
        importlib.import_module(module)
    logging.config.dictConfig(uvicorn.config.LOGGING_CONFIG)

    configure_logging(Settings(_env_file=None))

    problems = find_undelivered_loggers()
    assert not problems, "Some loggers do not reach the root handler:\n" + "\n".join(problems)


def test_audit_detects_a_logger_that_stops_propagation(fake_logger_names: list[str]) -> None:
    """Self-check: the audit reports `propagate=False`, otherwise the main test could never fail."""
    fake_logger_names.append(f"{FAKE_PREFIX}.stopper")
    logging.getLogger(fake_logger_names[-1]).propagate = False

    problems = find_undelivered_loggers()

    assert any("propagate=False" in problem and FAKE_PREFIX in problem for problem in problems), problems


def test_audit_detects_a_foreign_handler(fake_logger_names: list[str]) -> None:
    """Self-check: a handler attached by a library is reported, because it bypasses our formatter."""
    fake_logger_names.append(f"{FAKE_PREFIX}.writer")
    logging.getLogger(fake_logger_names[-1]).addHandler(logging.StreamHandler())

    problems = find_undelivered_loggers()

    assert any("handlers of" in problem and FAKE_PREFIX in problem for problem in problems), problems


def test_audit_detects_a_disabled_logger(fake_logger_names: list[str]) -> None:
    """Self-check: a disabled logger (what `dictConfig` does by default to old loggers) is reported."""
    fake_logger_names.append(f"{FAKE_PREFIX}.muted")
    logging.getLogger(fake_logger_names[-1]).disabled = True

    problems = find_undelivered_loggers()

    assert any("disabled" in problem and FAKE_PREFIX in problem for problem in problems), problems


def test_audit_ignores_null_handlers(fake_logger_names: list[str]) -> None:
    """Self-check: `NullHandler` is the standard library convention and must not raise an alarm."""
    fake_logger_names.append(f"{FAKE_PREFIX}.polite")
    logging.getLogger(fake_logger_names[-1]).addHandler(logging.NullHandler())

    problems = find_undelivered_loggers()

    assert not [problem for problem in problems if FAKE_PREFIX in problem], problems
