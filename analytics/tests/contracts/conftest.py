import pytest


@pytest.fixture(autouse=True)
def reset_db():
    yield
