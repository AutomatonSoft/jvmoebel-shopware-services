import struct
import zipfile
import zlib
from io import BytesIO
from pathlib import Path
from typing import Any


USDC_MAGIC = b"PXR-USDC"

MIN_USDA = """#usda 1.0
def Xform "Model"
{
}
"""

UsdEntry = tuple[str, str | bytes]


def _as_bytes(content: str | bytes) -> bytes:
    if isinstance(content, str):
        return content.encode("utf-8")
    return content


def _alignment_extra(header_start: int, filename: bytes) -> bytes:
    base = header_start + 30 + len(filename)
    extra_size = (64 - (base % 64)) % 64
    if extra_size == 0:
        return b""
    if extra_size < 4:
        extra_size += 64
    payload_size = extra_size - 4
    return struct.pack("<HH", 0xFFFF, payload_size) + b"\x00" * payload_size


def _pack_usdz_stored(
    entries: list[UsdEntry],
    align: bool,
    corrupt_crc: bool,
) -> bytes:
    local_parts: list[bytes] = []
    cd_parts: list[bytes] = []
    offset = 0
    first_data_end: int | None = None

    for name, content in entries:
        data = _as_bytes(content)
        name_bytes = name.encode("utf-8")
        crc = zlib.crc32(data) & 0xFFFFFFFF
        extra = _alignment_extra(offset, name_bytes) if align else b""

        local_header = struct.pack(
            "<IHHHHHIIIHH",
            0x04034B50,
            20,
            0,
            0,
            0,
            0,
            crc,
            len(data),
            len(data),
            len(name_bytes),
            len(extra),
        )
        data_start = offset + len(local_header) + len(name_bytes) + len(extra)
        if first_data_end is None and data:
            first_data_end = data_start + len(data)

        local_blob = local_header + name_bytes + extra + data
        cd_header = struct.pack(
            "<IHHHHHHIIIHHHHHII",
            0x02014B50,
            20,
            20,
            0,
            0,
            0,
            0,
            crc,
            len(data),
            len(data),
            len(name_bytes),
            len(extra),
            0,
            0,
            0,
            0,
            offset,
        )
        local_parts.append(local_blob)
        cd_parts.append(cd_header + name_bytes + extra)
        offset += len(local_blob)

    central_directory = b"".join(cd_parts)
    locals_blob = b"".join(local_parts)
    end_record = struct.pack(
        "<IHHHHIIH",
        0x06054B50,
        0,
        0,
        len(entries),
        len(entries),
        len(central_directory),
        len(locals_blob),
        0,
    )
    result = bytearray(locals_blob + central_directory + end_record)
    if corrupt_crc and first_data_end is not None:
        result[first_data_end - 1] ^= 0xFF
    return bytes(result)


def _pack_usdz_zipfile(
    entries: list[UsdEntry],
    compress_type: int,
) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=compress_type) as archive:
        for name, content in entries:
            archive.writestr(name, _as_bytes(content))
    return buffer.getvalue()


def pack_usdz(
    entries: list[UsdEntry] | None = None,
    *,
    align: bool = True,
    compress_type: int = zipfile.ZIP_STORED,
    corrupt_crc: bool = False,
) -> bytes:
    if entries is None:
        entries = [("model.usda", MIN_USDA)]

    if compress_type != zipfile.ZIP_STORED:
        return _pack_usdz_zipfile(entries, compress_type)

    return _pack_usdz_stored(
        entries=entries,
        align=align,
        corrupt_crc=corrupt_crc,
    )


def write_usdz(path: Path, *args: Any, **kwargs: Any) -> Path:
    path = Path(path)
    path.write_bytes(pack_usdz(*args, **kwargs))
    return path
