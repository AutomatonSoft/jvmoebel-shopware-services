import struct
import json
from pathlib import Path
from typing import Dict, Any, List

from app.domains.ar.validators.base import BaseValidator


class GLBValidator(BaseValidator):
    GLB_MAGIC = b'glTF'
    GLB_VERSION = 2
    CHUNK_TYPE_JSON = b'JSON'

    def validate(self, file_path: Path) -> bool:
        # 1. Проверка размера
        self._check_size(file_path)

        try:
            with open(file_path, 'rb') as f:
                # 2. Проверка заголовка
                header = f.read(12)
                if len(header) != 12:
                    return False

                magic, version, length = struct.unpack('<4sII', header)

                # 3. Проверка magic
                if magic != self.GLB_MAGIC:
                    return False

                # 4. Проверка версии
                if version != self.GLB_VERSION:
                    return False

                # 5. Проверка длины файла
                f.seek(0, 2)
                actual_length = f.tell()
                if length != actual_length:
                    return False

                # 6. Проверка chunk boundaries
                f.seek(12)
                chunks = self._parse_chunks(f, length)
                if chunks is None or not chunks:
                    return False

                # 7. Проверка первого JSON chunk
                if chunks[0]['type'] != self.CHUNK_TYPE_JSON:
                    return False

                # 8. Проверка JSON валидности
                if not self._validate_json_chunk(f, chunks[0]):
                    return False

                # 9. Проверка самодостаточности
                f.seek(chunks[0]['offset'])
                json_data = f.read(chunks[0]['length'])
                gltf_data = json.loads(json_data.decode('utf-8'))

                if not self._is_self_contained(gltf_data):
                    return False

                return True

        except Exception:
            return False

    def _parse_chunks(self, f, total_length: int) -> List[Dict[str, Any]]:
        chunks = []
        offset = 12

        while offset < total_length:
            chunk_header = f.read(8)
            if len(chunk_header) != 8:
                return None

            chunk_length, chunk_type = struct.unpack('<I4s', chunk_header)

            if offset + 8 + chunk_length > total_length:
                return None

            chunks.append({
                'type': chunk_type,
                'length': chunk_length,
                'offset': offset + 8
            })

            f.seek(chunk_length, 1)
            offset += 8 + chunk_length

        return chunks

    def _validate_json_chunk(self, f, chunk: Dict[str, Any]) -> bool:
        try:
            f.seek(chunk['offset'])
            json_data = f.read(chunk['length'])
            gltf_data = json.loads(json_data.decode('utf-8'))

            if 'asset' not in gltf_data:
                return False

            asset = gltf_data['asset']
            if asset.get('version') != '2.0':
                return False

            return True

        except (json.JSONDecodeError, UnicodeDecodeError, KeyError):
            return False

    def _is_self_contained(self, gltf_data: Dict[str, Any]) -> bool:
        # Проверка буферов
        if 'buffers' in gltf_data:
            for buffer in gltf_data['buffers']:
                if 'uri' in buffer:
                    uri = buffer['uri']
                    if not uri.startswith('data:') and not uri.startswith('blob:'):
                        return False

        # Проверка изображений
        if 'images' in gltf_data:
            for image in gltf_data['images']:
                if 'uri' in image:
                    uri = image['uri']
                    if not uri.startswith('data:') and not uri.startswith('blob:'):
                        return False

        return True