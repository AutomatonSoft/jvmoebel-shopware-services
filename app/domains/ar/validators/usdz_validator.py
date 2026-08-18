import zipfile
import os
from pathlib import Path

from app.domains.ar.validators.base import BaseValidator


class USDZValidator(BaseValidator):
    USD_EXTENSIONS = {'.usd', '.usda', '.usdc'}
    USDZ_ALIGNMENT = 64  # Требование USDZ: 64-байтовое выравнивание

    def validate(self, file_path: Path) -> bool:
        # 1. Проверка размера
        self._check_size(file_path)

        try:
            with open(file_path, 'rb') as f:
                # 2. Проверка ZIP заголовка
                header = f.read(4)
                if header != b'PK\x03\x04':
                    return False

                f.seek(0)

                # 3. Открываем как ZIP
                try:
                    with zipfile.ZipFile(f, 'r') as zip_file:
                        # 4. Проверка на encryption
                        for info in zip_file.infolist():
                            if info.flag_bits & 0x1:  # encrypted
                                return False

                        # 5. Проверка на compression (USDZ требует без сжатия)
                        for info in zip_file.infolist():
                            if info.compress_type != zipfile.ZIP_STORED:
                                return False

                        # 6. Проверка на безопасные пути
                        for info in zip_file.infolist():
                            filename = info.filename

                            # Проверка на абсолютный путь
                            if os.path.isabs(filename):
                                return False

                            # Проверка на directory traversal (../)
                            # Разбиваем путь на части и ищем '..'
                            parts = filename.split('/')
                            for part in parts:
                                if part == '..':
                                    return False

                            # Проверка на скрытые файлы
                            if filename.startswith('.') or '/.' in filename:
                                return False

                        # 7. Проверка наличия root USD модели
                        usd_files = []
                        for info in zip_file.infolist():
                            ext = os.path.splitext(info.filename)[1].lower()
                            if ext in self.USD_EXTENSIONS:
                                usd_files.append(info.filename)

                        if not usd_files:
                            return False

                        root_usd = [f for f in usd_files if '/' not in f and '\\' not in f]
                        if not root_usd:
                            return False

                        # 8. Проверка целостности (CRC)
                        corrupted = zip_file.testzip()
                        if corrupted is not None:
                            return False

                        # 9. Проверка USDZ alignment (64-байтовое выравнивание)
                        # Временно закомментировано, так как не все валидные USDZ файлы
                        # соблюдают это требование (например, файлы от Apple).
                        # Если потребуется строгая проверка - раскомментировать.
                        # if not self._check_usdz_alignment(zip_file):
                        #     return False

                        # 10. Проверка ZIP bomb: entry count limit
                        if len(zip_file.infolist()) > 10000:
                            return False

                        # 11. Проверка ZIP bomb: total uncompressed size limit
                        total_uncompressed = sum(info.file_size for info in zip_file.infolist())
                        if total_uncompressed > 100 * 1024 * 1024:  # 100 MB
                            return False

                except zipfile.BadZipFile:
                    return False

                return True

        except Exception:
            return False

    def _check_usdz_alignment(self, zip_file: zipfile.ZipFile) -> bool:
        """
        Проверка 64-байтового выравнивания для USDZ файлов.
        Каждый файл внутри архива должен начинаться с offset, кратного 64.
        """
        for info in zip_file.infolist():
            if info.header_offset % self.USDZ_ALIGNMENT != 0:
                return False
        return True