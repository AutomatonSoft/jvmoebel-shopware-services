import json
import struct
from pathlib import Path
from typing import Any

from app.domains.ar.validators.base import BaseValidator


class GLBValidator(BaseValidator):
    GLB_MAGIC = b"glTF"
    GLB_VERSION = 2
    CHUNK_TYPE_JSON = b"JSON"

    def validate(self, file_path: Path) -> bool:
        # ТЗ GLB-10: Файл <= AR_MAX_FILE_SIZE
        self._check_size(file_path)

        try:
            with open(file_path, "rb") as f:
                header = f.read(12)
                if len(header) != 12:
                    return False

                magic, version, length = struct.unpack("<4sII", header)

                # ТЗ GLB-2: Magic/header = glTF
                if magic != self.GLB_MAGIC:
                    return False

                # ТЗ GLB-3: glTF version = 2
                if version != self.GLB_VERSION:
                    return False

                # ТЗ GLB-4: Declared length = actual length
                f.seek(0, 2)
                actual_length = f.tell()
                if length != actual_length:
                    return False

                # ТЗ GLB-5: Корректные chunk boundaries
                # ТЗ GLB-9: Нет повреждённых chunks
                f.seek(12)
                chunks = self._parse_chunks(f, length)
                if chunks is None or not chunks:
                    return False

                # ТЗ GLB-6: Первый chunk = JSON
                if chunks[0]["type"] != self.CHUNK_TYPE_JSON:
                    return False

                # ТЗ GLB-7: JSON валиден
                # ТЗ GLB-8: asset.version = "2.0"
                if not self._validate_json_chunk(f, chunks[0]):
                    return False

                f.seek(chunks[0]["offset"])
                json_data = f.read(chunks[0]["length"])
                gltf_data = json.loads(json_data.decode("utf-8"))

                # ТЗ GLB-11: Self-contained: запрет blob:/external URI
                if not self._is_self_contained(gltf_data):
                    return False

                return True

        except Exception:
            return False

    def _parse_chunks(
        self,
        f,
        total_length: int,
    ) -> list[dict[str, Any]] | None:
        chunks: list[dict[str, Any]] = []
        offset = 12

        while offset < total_length:
            chunk_header = f.read(8)
            if len(chunk_header) != 8:
                return None

            chunk_length, chunk_type = struct.unpack("<I4s", chunk_header)

            if offset + 8 + chunk_length > total_length:
                return None

            chunks.append(
                {
                    "type": chunk_type,
                    "length": chunk_length,
                    "offset": offset + 8,
                }
            )

            f.seek(chunk_length, 1)
            offset += 8 + chunk_length

        return chunks

    def _validate_json_chunk(self, f, chunk: dict[str, Any]) -> bool:
        try:
            f.seek(chunk["offset"])
            json_data = f.read(chunk["length"])
            gltf_data = json.loads(json_data.decode("utf-8"))

            if "asset" not in gltf_data:
                return False

            asset = gltf_data["asset"]
            if asset.get("version") != "2.0":
                return False

            return True

        except (json.JSONDecodeError, UnicodeDecodeError, KeyError):
            return False

    def _is_self_contained(self, gltf_data: dict[str, Any]) -> bool:
        if "buffers" in gltf_data:
            for buffer in gltf_data["buffers"]:
                if "uri" in buffer and not buffer["uri"].startswith("data:"):
                    return False

        if "images" in gltf_data:
            for image in gltf_data["images"]:
                if "uri" in image and not image["uri"].startswith("data:"):
                    return False

        return True
