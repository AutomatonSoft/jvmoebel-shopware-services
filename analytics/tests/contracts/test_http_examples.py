from pathlib import Path

import pytest

from tests.contracts.loader import load_validator

http = load_validator("http")
VALID = sorted((http.ROOT / "examples" / "valid").glob("*.json"))
INVALID = sorted((http.ROOT / "examples" / "invalid").glob("*.json"))


def test_http_example_fixtures_exist() -> None:
    assert VALID
    assert INVALID


@pytest.mark.parametrize("path", VALID, ids=lambda path: path.name)
def test_valid_http_example(path: Path) -> None:
    assert http.validate(path, True)


@pytest.mark.parametrize("path", INVALID, ids=lambda path: path.name)
def test_invalid_http_example(path: Path) -> None:
    assert http.validate(path, False)


def test_http_extra_invariants() -> None:
    assert http.extra_invariants()
