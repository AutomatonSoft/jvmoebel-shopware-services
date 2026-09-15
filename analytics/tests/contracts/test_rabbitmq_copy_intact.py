from pathlib import Path

import pytest

from tests.contracts.loader import load_validator

rabbitmq = load_validator("rabbitmq")
VALID = sorted((rabbitmq.ROOT / "examples" / "valid").glob("*.json"))
INVALID = sorted((rabbitmq.ROOT / "examples" / "invalid").glob("*.json"))


def test_rabbitmq_example_fixtures_exist() -> None:
    assert VALID
    assert INVALID


@pytest.mark.parametrize("path", VALID, ids=lambda path: path.name)
def test_valid_rabbitmq_example(path: Path) -> None:
    assert rabbitmq.validate(path, True)


@pytest.mark.parametrize("path", INVALID, ids=lambda path: path.name)
def test_invalid_rabbitmq_example(path: Path) -> None:
    assert rabbitmq.validate(path, False)


def test_rabbitmq_extra_invariants() -> None:
    assert rabbitmq.extra_invariants()
