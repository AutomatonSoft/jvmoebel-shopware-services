import os
import re
import struct
import zipfile
from pathlib import Path
from typing import Optional

from domains.ar.validators.base import BaseValidator


class USDZValidator(BaseValidator):
    USD_EXTENSIONS = {".usd", ".usda", ".usdc"}
    USDC_MAGIC = b"PXR-USDC"
    USDA_HEADER = re.compile(r"^#usda\s+\d+(?:\.\d+)?\b")
    PRIM_OPEN = re.compile(
        r"\b(?:def|over|class)\s+\S+(?:\s+\S+)*\s*\{",
        re.DOTALL,
    )
    MAX_ENTRIES = 10000
    MAX_UNCOMPRESSED_SIZE = 100 * 1024 * 1024  # 100 MB

    def validate(self, file_path: Path) -> bool:
        # ТЗ USDZ-11: Файл <= AR_MAX_FILE_SIZE
        self._check_size(file_path)

        try:
            with open(file_path, "rb") as f:
                header = f.read(4)
                # ТЗ USDZ-2: Валидный ZIP container (PK)
                if header != b"PK\x03\x04":
                    return False

                f.seek(0)

                try:
                    with zipfile.ZipFile(f, "r") as zip_file:
                        usd_files: list[str] = []

                        scanned_entries = 0
                        total_uncompressed = 0
                        for info in zip_file.infolist():
                            scanned_entries += 1
                            total_uncompressed += info.file_size
                            if (
                                scanned_entries > self.MAX_ENTRIES
                                or total_uncompressed > self.MAX_UNCOMPRESSED_SIZE
                            ):
                                return False
                            # ТЗ USDZ-3: Не encrypted
                            if info.flag_bits & 0x1:
                                return False

                            # ТЗ USDZ-4: Не compressed (ZIP_STORED)
                            if info.compress_type != zipfile.ZIP_STORED:
                                return False

                            # ТЗ USDZ-7: Защита от ../ и absolute paths
                            if not self._is_safe_path(info.filename):
                                return False

                            filename = info.filename.replace("\\", "/")
                            ext = os.path.splitext(filename)[1].lower()
                            if ext in self.USD_EXTENSIONS:
                                usd_files.append(filename)

                        # ТЗ USDZ-8: ZIP bomb: entries <= 10000
                        if len(zip_file.infolist()) > self.MAX_ENTRIES:
                            return False

                        # ТЗ USDZ-9: ZIP bomb: uncompressed size <= 100 MB
                        total_uncompressed = sum(
                            info.file_size for info in zip_file.infolist()
                        )
                        if total_uncompressed > self.MAX_UNCOMPRESSED_SIZE:
                            return False

                        # ТЗ USDZ-10: Нет повреждённых archive records (testzip)
                        if zip_file.testzip() is not None:
                            return False

                        # ТЗ USDZ-5: 64-byte alignment
                        if not self._has_64_byte_alignment(file_path, zip_file):
                            return False

                        # ТЗ USDZ-6: Root USD модель в корне
                        root_usd = self._find_root_usd(usd_files)
                        if not root_usd:
                            return False

                        if not self._validate_usd_files(zip_file, usd_files):
                            return False

                except zipfile.BadZipFile:
                    return False

                return True

        except Exception:
            return False

    def _has_64_byte_alignment(
        self,
        file_path: Path,
        zip_file: zipfile.ZipFile,
    ) -> bool:
        with open(file_path, "rb") as raw:
            for info in zip_file.infolist():
                if info.is_dir():
                    continue
                raw.seek(info.header_offset)
                local_header = raw.read(30)
                if len(local_header) != 30:
                    return False

                name_len, extra_len = struct.unpack_from("<HH", local_header, 26)
                data_offset = info.header_offset + 30 + name_len + extra_len
                if data_offset % 64 != 0:
                    return False

        return True

    def _is_safe_path(self, filename: str) -> bool:
        if "\0" in filename:
            return False

        if any(c in filename for c in '<>:"|?*'):
            return False

        normalized = filename.replace("\\", "/")

        if normalized.startswith("/") or normalized.startswith("//"):
            return False

        if re.match(r"^[A-Za-z]:", normalized):
            return False

        if normalized.endswith("/"):
            normalized = normalized.rstrip("/")
            if not normalized:
                return False

        parts = normalized.split("/")
        for part in parts:
            if part in ("..", ".", ""):
                return False

        if normalized.startswith(".") or "/." in normalized:
            return False

        return True

    def _find_root_usd(self, usd_files: list[str]) -> Optional[str]:
        root_files = []
        for filename in usd_files:
            normalized = filename.replace("\\", "/")
            if "/" not in normalized:
                root_files.append(normalized)
        return root_files[0] if root_files else None

    def _validate_usd_files(
        self,
        zip_file: zipfile.ZipFile,
        usd_files: list[str],
    ) -> bool:
        for filename in usd_files:
            ext = os.path.splitext(filename)[1].lower()

            try:
                content = zip_file.read(filename)
                if not content:
                    return False

                if ext == ".usda":
                    # USDA: #usda header + prim (def/over/class) with braces
                    if not self._validate_usda_content(content):
                        return False
                elif ext == ".usdc":
                    # ТЗ USDZ-6.2: .usdc: сигнатура PXR-USDC
                    if not content.startswith(self.USDC_MAGIC):
                        return False
                elif ext == ".usd":
                    # ТЗ USDZ-6.3: .usd: сигнатура PXR-USDC или как .usda
                    if content.startswith(self.USDC_MAGIC):
                        continue
                    if not self._validate_usda_content(content):
                        return False
            except Exception:
                return False

        return True

    def _validate_usda_content(self, content: bytes) -> bool:
        try:
            text = content.decode("utf-8").lstrip("\ufeff")
            lines = [line.strip() for line in text.splitlines() if line.strip()]

            if not lines:
                return False

            if not self.USDA_HEADER.match(lines[0]):
                return False

            full_text = "\n".join(lines)
            if not self.PRIM_OPEN.search(full_text):
                return False

            return "}" in full_text

        except Exception:
            return False
