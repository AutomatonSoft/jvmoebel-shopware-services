from pathlib import Path

import pytest

from domains.ar.storage import ARModelStorage


@pytest.fixture
def storage(tmp_path: Path) -> ARModelStorage:
    ar_storage = ARModelStorage()
    ar_storage.base_path = (tmp_path / "ar_models").resolve()
    ar_storage.base_path.mkdir(parents=True, exist_ok=True)
    return ar_storage


@pytest.mark.asyncio
async def test_exists_is_false_for_path_outside_base(
    storage: ARModelStorage,
    tmp_path: Path,
):
    outsider = tmp_path / "secret.txt"
    outsider.write_text("keep")

    assert outsider.is_file()
    assert await storage.exists(str(outsider)) is False


@pytest.mark.asyncio
async def test_delete_refuses_path_outside_base(
    storage: ARModelStorage,
    tmp_path: Path,
):
    outsider = tmp_path / "secret.txt"
    outsider.write_text("keep")

    with pytest.raises(ValueError, match="Invalid storage path"):
        await storage.delete(str(outsider))

    assert outsider.is_file()


@pytest.mark.asyncio
async def test_delete_removes_file_inside_base(storage: ARModelStorage):
    inside = storage.base_path / "model.glb"
    inside.write_bytes(b"glb")

    assert await storage.exists(str(inside)) is True

    await storage.delete(str(inside))

    assert inside.exists() is False
    assert await storage.exists(str(inside)) is False
