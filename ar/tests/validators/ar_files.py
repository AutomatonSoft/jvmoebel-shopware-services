from pathlib import Path

from scripts.validators.build_dice_glb import build_dice_glb
from scripts.validators.build_dice_usdz import build_dice_usdz
from scripts.validators.pack_glb import pack_glb
from scripts.validators.pack_usdz import pack_usdz

# True: не удалять файлы из generated/ после теста
KEEP_GENERATED = False

GENERATED_DIR = Path(__file__).resolve().parent / "generated"


def dice_glb_bytes(**pack_kwargs) -> bytes:
    gltf, bin_data = build_dice_glb()
    return pack_glb(gltf, bin_data, **pack_kwargs)


def dice_glb_bytes_mutated(mutate_gltf, **pack_kwargs) -> bytes:
    gltf, bin_data = build_dice_glb()
    mutate_gltf(gltf)
    return pack_glb(gltf, bin_data, **pack_kwargs)


def dice_usdz_bytes(**pack_kwargs) -> bytes:
    return pack_usdz(
        [("dice.usda", build_dice_usdz())],
        **pack_kwargs,
    )


def write_generated(name: str, data: bytes) -> Path:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    path = GENERATED_DIR / name
    path.write_bytes(data)
    return path


def cleanup_generated(path: Path) -> None:
    if not KEEP_GENERATED and path.exists():
        path.unlink()
