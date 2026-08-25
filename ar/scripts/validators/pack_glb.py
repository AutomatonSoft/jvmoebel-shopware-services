import json
import struct
from pathlib import Path
from typing import Any


GLB_MAGIC = b"glTF"
GLB_VERSION = 2
JSON_CHUNK_TYPE = b"JSON"
BIN_CHUNK_TYPE = b"BIN\x00"

MIN_GLTF: dict[str, Any] = {
    "asset": {"version": "2.0"},
    "scene": 0,
    "scenes": [{"nodes": [0]}],
    "nodes": [{"name": "root"}],
}


def _pad4(data: bytes, pad_byte: bytes) -> bytes:
    padding = (4 - len(data) % 4) % 4
    return data + pad_byte * padding


def pack_glb(
    gltf: dict[str, Any] | None = None,
    bin_data: bytes = b"",
    *,
    magic: bytes = GLB_MAGIC,
    version: int = GLB_VERSION,
    declared_length: int | None = None,
    first_chunk_type: bytes = JSON_CHUNK_TYPE,
    json_bytes: bytes | None = None,
) -> bytes:
    if json_bytes is None:
        payload = gltf if gltf is not None else MIN_GLTF
        json_bytes = json.dumps(
            payload,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")

    json_bytes = _pad4(json_bytes, b" ")
    chunks = struct.pack("<I4s", len(json_bytes), first_chunk_type) + json_bytes

    if bin_data:
        bin_padded = _pad4(bin_data, b"\x00")
        chunks += struct.pack("<I4s", len(bin_padded), BIN_CHUNK_TYPE) + bin_padded

    actual_length = 12 + len(chunks)
    length = actual_length if declared_length is None else declared_length
    header = struct.pack("<4sII", magic, version, length)
    return header + chunks


def write_glb(path: Path, *args: Any, **kwargs: Any) -> Path:
    path = Path(path)
    path.write_bytes(pack_glb(*args, **kwargs))
    return path
