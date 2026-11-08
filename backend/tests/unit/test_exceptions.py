"""Tests for the domain exception hierarchy."""

import pytest

from onsite_floor.core.exceptions import DomainException, ObjectNotFoundException

# Every top-level category of the project, collected automatically so that a new one is checked from day one.
# The filter keeps out classes that tests declare locally: Python registers them as subclasses too
# and removes them only when the garbage collector runs.
CATEGORIES = [
    category for category in DomainException.__subclasses__() if category.__module__.startswith("onsite_floor.")
]


def test_categories_are_discovered() -> None:
    """The automatic list must not silently become empty: parametrized tests over it would then run zero cases."""
    assert ObjectNotFoundException in CATEGORIES, f"categories were not discovered: {CATEGORIES}"


def test_exception_carries_message_and_code() -> None:
    """A domain exception exposes a readable message and a stable machine-readable code."""
    error = DomainException("Something went wrong", "SOMETHING_WRONG")

    assert error.message == "Something went wrong", "The message must be kept as given"
    assert error.code == "SOMETHING_WRONG", "The code must be kept as given"


def test_str_is_the_message() -> None:
    """`str(error)` is the human-readable message, so logs and tracebacks stay clean."""
    error = DomainException("Something went wrong", "SOMETHING_WRONG")

    assert str(error) == "Something went wrong", "str() must return the message without the code"


@pytest.mark.parametrize("category", CATEGORIES)
def test_every_category_is_a_domain_exception(category: type[DomainException]) -> None:
    """Every category derives from `DomainException`, so one handler base covers them all."""
    assert issubclass(category, DomainException), f"{category.__name__} must derive from DomainException"


@pytest.mark.parametrize("category", CATEGORIES)
def test_category_can_be_raised_without_arguments(category: type[DomainException]) -> None:
    """A category falls back to its own default message and code when the raiser gives none."""
    error = category()

    assert error.message == category.default_message, "The default message must be used"
    assert error.code == category.default_code, "The default code must be used"
    assert str(error) == category.default_message, "str() must show the default message"


@pytest.mark.parametrize("category", CATEGORIES)
def test_explicit_arguments_override_the_defaults(category: type[DomainException]) -> None:
    """A message and a code given at the raise site win over the category defaults."""
    error = category("Route 'x' is missing", "ROUTE_NOT_FOUND")

    assert error.message == "Route 'x' is missing", "An explicit message must win"
    assert error.code == "ROUTE_NOT_FOUND", "An explicit code must win"


def test_subclass_overrides_only_what_it_declares() -> None:
    """A feature error that sets only its code keeps the message of its category."""

    class ProcessNotFoundException(ObjectNotFoundException):
        """A feature-style error declared only for this test."""

        default_code = "PROCESS_NOT_FOUND"

    error = ProcessNotFoundException()

    assert error.code == "PROCESS_NOT_FOUND", "The subclass code must override the category code"
    assert error.message == ObjectNotFoundException.default_message, "The category message must be inherited"


@pytest.mark.parametrize("category", CATEGORIES)
def test_every_category_defines_its_own_defaults(category: type[DomainException]) -> None:
    """A category must not silently inherit the generic defaults of the base class."""
    assert "default_message" in vars(category), f"{category.__name__} must declare default_message"
    assert "default_code" in vars(category), f"{category.__name__} must declare default_code"


def test_default_codes_are_unique() -> None:
    """Two categories sharing a code would make them indistinguishable for the frontend."""
    codes = [category.default_code for category in CATEGORIES]

    assert len(set(codes)) == len(codes), f"Duplicate default codes: {codes}"
