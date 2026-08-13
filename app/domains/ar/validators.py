# app/domains/ar/validators.py


#               !!!ВАЖНО!!!
# Этот валидатор написал гпт, я не работал с такими форматами ранее и не проверял
# Поэтому узнать, писали ли ранее такой валидатор в компании и проверить его работу на тестах


import json
import struct
import zipfile

from fastapi import UploadFile

from .exceptions import (
    InvalidARModelFileException,
    UnsupportedARModelFormatException,
)


GLB_HEADER_SIZE = 12
GLB_CHUNK_HEADER_SIZE = 8

GLB_MAGIC = 0x46546C67
GLB_VERSION = 2

GLB_JSON_CHUNK_TYPE = 0x4E4F534A
GLB_BIN_CHUNK_TYPE = 0x004E4942

ZIP_LOCAL_FILE_HEADER_SIZE = 30

USDZ_ALIGNMENT = 64

SUPPORTED_USD_EXTENSIONS = (
    ".usd",
    ".usda",
    ".usdc",
)

SUPPORTED_FORMATS = {
    "glb",
    "usdz",
}


async def validate_model_file(
    file: UploadFile,
    file_format: str,
) -> None:

    if file_format not in SUPPORTED_FORMATS:
        raise UnsupportedARModelFormatException()

    if file_format == "glb":
        await _validate_glb(file)
        return

    if file_format == "usdz":
        await _validate_usdz(file)


async def _validate_glb(
    file: UploadFile,
) -> None:

    await file.seek(0)

    actual_size = _get_file_size(file)

    if actual_size < GLB_HEADER_SIZE:
        raise InvalidARModelFileException()

    await file.seek(0)

    header = await file.read(
        GLB_HEADER_SIZE,
    )

    if len(header) != GLB_HEADER_SIZE:
        raise InvalidARModelFileException()

    magic, version, total_length = struct.unpack(
        "<III",
        header,
    )

    if magic != GLB_MAGIC:
        raise InvalidARModelFileException()

    if version != GLB_VERSION:
        raise InvalidARModelFileException()

    if total_length != actual_size:
        raise InvalidARModelFileException()

    if total_length < (
        GLB_HEADER_SIZE + GLB_CHUNK_HEADER_SIZE
    ):
        raise InvalidARModelFileException()

    bytes_read = GLB_HEADER_SIZE
    json_chunk_found = False

    while bytes_read < total_length:

        if (
            total_length - bytes_read
            < GLB_CHUNK_HEADER_SIZE
        ):
            raise InvalidARModelFileException()

        chunk_header = await file.read(
            GLB_CHUNK_HEADER_SIZE,
        )

        if len(chunk_header) != GLB_CHUNK_HEADER_SIZE:
            raise InvalidARModelFileException()

        chunk_length, chunk_type = struct.unpack(
            "<II",
            chunk_header,
        )

        bytes_read += GLB_CHUNK_HEADER_SIZE

        if chunk_length == 0:
            raise InvalidARModelFileException()

        if bytes_read + chunk_length > total_length:
            raise InvalidARModelFileException()

        if chunk_type == GLB_JSON_CHUNK_TYPE:

            if json_chunk_found:
                raise InvalidARModelFileException()

            if bytes_read != (
                GLB_HEADER_SIZE
                + GLB_CHUNK_HEADER_SIZE
            ):
                raise InvalidARModelFileException()

            json_data = await file.read(
                chunk_length,
            )

            if len(json_data) != chunk_length:
                raise InvalidARModelFileException()

            json_data = _strip_glb_json_padding(
                json_data,
            )

            try:
                json_text = json_data.decode("utf-8")
                gltf = json.loads(json_text)

            except (
                UnicodeDecodeError,
                json.JSONDecodeError,
            ):
                raise InvalidARModelFileException()

            if not isinstance(gltf, dict):
                raise InvalidARModelFileException()

            asset = gltf.get("asset")

            if not isinstance(asset, dict):
                raise InvalidARModelFileException()

            if asset.get("version") != "2.0":
                raise InvalidARModelFileException()

            json_chunk_found = True

        elif chunk_type == GLB_BIN_CHUNK_TYPE:

            if not json_chunk_found:
                raise InvalidARModelFileException()

            bin_data = await file.read(
                chunk_length,
            )

            if len(bin_data) != chunk_length:
                raise InvalidARModelFileException()

        else:
            raise InvalidARModelFileException()

        bytes_read += chunk_length

    if bytes_read != total_length:
        raise InvalidARModelFileException()

    if not json_chunk_found:
        raise InvalidARModelFileException()

    await file.seek(0)


def _strip_glb_json_padding(
    data: bytes,
) -> bytes:

    stripped_data = data.rstrip(b" ")

    if not stripped_data:
        raise InvalidARModelFileException()

    padding = data[len(stripped_data):]

    if padding and any(
        byte != 0x20
        for byte in padding
    ):
        raise InvalidARModelFileException()

    return stripped_data


async def _validate_usdz(
    file: UploadFile,
) -> None:

    await file.seek(0)

    try:
        with zipfile.ZipFile(file.file) as archive:

            members = archive.infolist()

            if not members:
                raise InvalidARModelFileException()

            first_member = members[0]

            if first_member.is_dir():
                raise InvalidARModelFileException()

            for member in members:

                if member.is_dir():
                    raise InvalidARModelFileException()

                if member.flag_bits & 0x1:
                    raise InvalidARModelFileException()

                if member.compress_type != zipfile.ZIP_STORED:
                    raise InvalidARModelFileException()

                data_offset = (
                    member.header_offset
                    + ZIP_LOCAL_FILE_HEADER_SIZE
                    + len(
                        member.filename.encode("utf-8"),
                    )
                    + len(member.extra)
                )

                if data_offset % USDZ_ALIGNMENT != 0:
                    raise InvalidARModelFileException()

            first_filename = first_member.filename.lower()

            if not first_filename.endswith(
                SUPPORTED_USD_EXTENSIONS,
            ):
                raise InvalidARModelFileException()

            first_file_data = archive.read(
                first_member,
            )

            if not _is_usd_file(first_file_data):
                raise InvalidARModelFileException()

    except (
        zipfile.BadZipFile,
        OSError,
        ValueError,
    ):
        raise InvalidARModelFileException()

    await file.seek(0)


def _is_usd_file(
    data: bytes,
) -> bool:

    if data.startswith(b"#usda"):
        return True

    if data.startswith(b"PXR-USDC"):
        return True

    return False


def _get_file_size(
    file: UploadFile,
) -> int:

    current_position = file.file.tell()

    file.file.seek(0, 2)
    size = file.file.tell()

    file.file.seek(current_position)

    return size