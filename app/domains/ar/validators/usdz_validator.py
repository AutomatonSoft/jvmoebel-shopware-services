# app/domains/ar/validators/usdz_validator.py

import zipfile
import os
import re
from pathlib import Path
from typing import Optional

from app.domains.ar.validators.base import BaseValidator


class USDZValidator(BaseValidator):
    USD_EXTENSIONS = {'.usd', '.usda', '.usdc'}
    MAX_ENTRIES = 10000
    MAX_UNCOMPRESSED_SIZE = 100 * 1024 * 1024  # 100 MB

    def validate(self, file_path: Path) -> bool:
        self._check_size(file_path)

        try:
            with open(file_path, 'rb') as f:
                header = f.read(4)
                if header != b'PK\x03\x04':
                    return False

                f.seek(0)

                try:
                    with zipfile.ZipFile(f, 'r') as zip_file:
                        has_usd_file = False
                        usd_files = []

                        for info in zip_file.infolist():
                            if info.flag_bits & 0x1:
                                return False

                            if info.compress_type != zipfile.ZIP_STORED:
                                return False

                            if not self._is_safe_path(info.filename):
                                return False

                            filename = info.filename.replace('\\', '/')
                            ext = os.path.splitext(filename)[1].lower()
                            if ext in self.USD_EXTENSIONS:
                                has_usd_file = True
                                usd_files.append(filename)

                        if not has_usd_file:
                            return False

                        root_usd = self._find_root_usd(usd_files)
                        if not root_usd:
                            return False

                        if not self._validate_usd_files(zip_file, usd_files):
                            return False

                        corrupted = zip_file.testzip()
                        if corrupted is not None:
                            return False

                        if len(zip_file.infolist()) > self.MAX_ENTRIES:
                            return False

                        total_uncompressed = sum(info.file_size for info in zip_file.infolist())
                        if total_uncompressed > self.MAX_UNCOMPRESSED_SIZE:
                            return False

                except zipfile.BadZipFile:
                    return False

                return True

        except Exception:
            return False

    def _is_safe_path(self, filename: str) -> bool:
        if '\0' in filename:
            return False

        if any(c in filename for c in '<>:"|?*'):
            return False

        normalized = filename.replace('\\', '/')

        if normalized.startswith('/') or normalized.startswith('//'):
            return False

        if re.match(r'^[A-Za-z]:', normalized):
            return False

        parts = normalized.split('/')
        for part in parts:
            if part in ('..', '.', ''):
                return False

        if normalized.startswith('.') or '/.' in normalized:
            return False

        return True

    def _find_root_usd(self, usd_files: list[str]) -> Optional[str]:
        root_files = []
        for filename in usd_files:
            normalized = filename.replace('\\', '/')
            if '/' not in normalized:
                root_files.append(normalized)
        return root_files[0] if root_files else None

    def _validate_usd_files(self, zip_file: zipfile.ZipFile, usd_files: list[str]) -> bool:
        for filename in usd_files:
            ext = os.path.splitext(filename)[1].lower()

            try:
                with zip_file.open(filename) as usd_file:
                    first_byte = usd_file.read(1)
                    if not first_byte:
                        return False

                    if ext == '.usda':
                        usd_file.seek(0)
                        content = usd_file.read(4096)
                        if not self._validate_usda_content(content):
                            return False
            except Exception:
                return False

        return True

    def _validate_usda_content(self, content: bytes) -> bool:
        try:
            text = content.decode('utf-8', errors='ignore')
            lines = [line.strip() for line in text.split('\n') if line.strip()]

            if not lines:
                return False

            full_text = ' '.join(lines)

            # Проверяем наличие маркера USD
            has_usd_marker = '#usda' in full_text or '#usd' in full_text

            # Проверяем наличие определений (def, over, class) - ОБЯЗАТЕЛЬНО!
            has_definition = bool(re.search(r'\b(def|over|class)\s+', full_text))

            # Проверяем наличие скобок
            has_braces = '{' in full_text and '}' in full_text

            # USD файл должен иметь ОБЯЗАТЕЛЬНО определение (def/over/class)
            # ИЛИ маркер + скобки
            if has_definition:
                return True

            # Если нет определения, но есть маркер и скобки - тоже пропускаем
            if has_usd_marker and has_braces:
                return True

            return False

        except Exception:
            return False