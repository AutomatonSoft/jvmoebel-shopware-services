import pytest
import json
import struct
import zipfile
import os
from pathlib import Path
from app.domains.ar.validators.factory import ValidatorFactory
from app.domains.ar.exceptions import (
    UnsupportedARModelFormatException,
    ARModelFileTooLargeException,
)


class TestARValidatorsWithRealFiles:
    """Тесты с реальными файлами из папки fixtures"""

    @pytest.fixture
    def fixtures_dir(self) -> Path:
        """Путь к директории с фикстурами"""
        return Path(__file__).parent.parent / "fixtures" / "ar"

    # ============ ТЗ: valid GLB → accepted ============

    def test_valid_glb_accepted(self, fixtures_dir):
        """
        ТЗ: valid GLB → accepted

        Берем все GLB файлы из папки fixtures/ar/valid/glb/
        и проверяем, что валидатор пропускает их как корректные.
        Если хоть один файл не пройдет валидацию - тест упадет.
        """

        glb_files = list((fixtures_dir / "valid" / "glb").glob("*.glb"))

        # Проверяем, что есть хотя бы один файл
        assert len(glb_files) > 0, "No GLB files found in fixtures"

        for glb_file in glb_files:
            result = ValidatorFactory.validate(glb_file)
            assert result is True, f"Valid GLB should pass: {glb_file.name}"

    # ============ ТЗ: valid USDZ → accepted ============

    def test_valid_usdz_accepted(self, fixtures_dir):
        """
        ТЗ: valid USDZ → accepted

        Берем все USDZ файлы из папки fixtures/ar/valid/usdz/
        и проверяем, что валидатор пропускает их как корректные.
        Если хоть один файл не пройдет валидацию - тест упадет.
        """
        usdz_files = list((fixtures_dir / "valid" / "usdz").glob("*.usdz"))

        assert len(usdz_files) > 0, "No USDZ files found in fixtures"

        for usdz_file in usdz_files:
            result = ValidatorFactory.validate(usdz_file)
            assert result is True, f"Valid USDZ should pass: {usdz_file.name}"

    # ============ ТЗ: corrupted GLB → rejected ============

    def test_corrupted_glb_rejected(self, fixtures_dir):
        """ТЗ: corrupted GLB → rejected"""

        glb_files = list((fixtures_dir / "invalid" / "glb").glob("*.glb"))

        # Если нет файлов, пропускаем тест
        if not glb_files:
            pytest.skip("No corrupted GLB files found in fixtures")

        for glb_file in glb_files:
            result = ValidatorFactory.validate(glb_file)
            assert result is False, f"Corrupted GLB should fail: {glb_file.name}"

    # ============ ТЗ: corrupted USDZ → rejected ============

    def test_corrupted_usdz_rejected(self, fixtures_dir):
        """ТЗ: corrupted USDZ → rejected"""
        usdz_files = list((fixtures_dir / "invalid" / "usdz").glob("*.usdz"))

        if not usdz_files:
            pytest.skip("No corrupted USDZ files found in fixtures")

        for usdz_file in usdz_files:
            result = ValidatorFactory.validate(usdz_file)
            assert result is False, f"Corrupted USDZ should fail: {usdz_file.name}"


class TestARValidatorsWithGeneratedFiles:
    """
    Тесты с файлами, создаваемыми на лету
    Или с реальными файлами, которые были изменены
    """

    @pytest.fixture
    def fixtures_dir(self) -> Path:
        """Путь к директории с фикстурами"""
        return Path(__file__).parent.parent / "fixtures" / "ar"

    # ============ ЛИЧНОЕ: валидный GLB (создаем сами) ============

    def test_valid_glb_generated_accepted(self, tmp_path):
        """
        ЛИЧНОЕ: создаем валидный GLB и проверяем, что он проходит
        (не из ТЗ, добавлено для независимости от fixtures)
        """
        glb_path = tmp_path / "valid.glb"

        # Минимальный валидный GLB
        gltf = {
            "asset": {"version": "2.0"},
            "scene": 0,
            "scenes": [{"nodes": [0]}],
            "nodes": [{"name": "root"}]
        }

        json_data = json.dumps(gltf, separators=(',', ':')).encode('utf-8')
        json_len = len(json_data)

        # Padding до 4 байт
        padding = (4 - json_len % 4) % 4
        json_data += b'\x00' * padding

        # Заголовок GLB
        total_length = 12 + 8 + len(json_data)
        header = struct.pack('<4sII', b'glTF', 2, total_length)

        # JSON chunk
        chunk = struct.pack('<I4s', len(json_data), b'JSON') + json_data

        with open(glb_path, 'wb') as f:
            f.write(header + chunk)

        result = ValidatorFactory.validate(glb_path)
        assert result is True, "Generated valid GLB should pass"

    # ============ ЛИЧНОЕ: валидный USDZ (создаем сами) ============

    def test_valid_usdz_generated_accepted(self, tmp_path):
        """
        ЛИЧНОЕ: создаем валидный USDZ и проверяем, что он проходит
        (не из ТЗ, добавлено для независимости от fixtures)
        """
        usdz_path = tmp_path / "valid.usdz"

        # Минимальный валидный USDA контент
        usda_content = '#usda 1.0\n'

        # Создаем ZIP без сжатия (требование USDZ)
        with zipfile.ZipFile(usdz_path, 'w', compression=zipfile.ZIP_STORED) as zf:
            zf.writestr('model.usda', usda_content)

        result = ValidatorFactory.validate(usdz_path)
        assert result is True, "Generated valid USDZ should pass"

    # ============ ТЗ: fake text file named .glb → rejected ============

    def test_fake_text_file_glb_rejected(self, tmp_path):
        """ТЗ: fake text file named .glb → rejected"""
        fake_glb = tmp_path / "fake.glb"
        fake_glb.write_text("This is not a real GLB file")

        result = ValidatorFactory.validate(fake_glb)
        assert result is False

    # ============ ТЗ: malformed GLB length/chunk → rejected ============

    def test_malformed_glb_rejected(self, fixtures_dir, tmp_path):
        """ТЗ: malformed GLB length/chunk → rejected"""
        # Берем валидный GLB из fixtures
        glb_files = list((fixtures_dir / "valid" / "glb").glob("*.glb"))
        if not glb_files:
            pytest.skip("No valid GLB files found in fixtures")

        valid_glb = glb_files[0]
        malformed_path = tmp_path / "malformed.glb"

        with open(valid_glb, 'rb') as f:
            data = bytearray(f.read())

        # Меняем длину в заголовке (байты 8-11) на меньшую
        # <I — формат для упаковки 4-байтового целого числа (unsigned int) в little-endian
        # 8 — смещение в байтах от начала файла (именно там хранится length)
        # 100 — новое очень маленькое значение длины
        if len(data) > 12:
            struct.pack_into('<I', data, 8, 100)

        with open(malformed_path, 'wb') as f:
            f.write(data)

        result = ValidatorFactory.validate(malformed_path)
        assert result is False

    # ============ ТЗ: fake ZIP named .usdz → rejected ============

    def test_fake_zip_usdz_rejected(self, tmp_path):
        """ТЗ: fake ZIP named .usdz → rejected"""
        fake_usdz = tmp_path / "fake.usdz"

        # Создаем обычный ZIP без USD контента
        with zipfile.ZipFile(fake_usdz, 'w') as zf:
            zf.writestr('test.txt', 'This is a fake USDZ file')

        result = ValidatorFactory.validate(fake_usdz)
        assert result is False

    # ============ ТЗ: unsafe archive path ../ → rejected ============

    def test_unsafe_archive_path_rejected(self, tmp_path):
        """
        ТЗ: unsafe archive path ../ → rejected
        Проверяет, что USDZ файл не содержит пути с directory traversal (../)
        """
        unsafe_usdz = tmp_path / "unsafe.usdz"

        with zipfile.ZipFile(unsafe_usdz, 'w') as zf:
            # Опасный файл - пытается выйти из папки
            zf.writestr('../../../etc/passwd', 'fake content')
            # Безопасный файл - чтобы архив выглядел как USDZ
            zf.writestr('model.usda', '#usda 1.0\n')

        result = ValidatorFactory.validate(unsafe_usdz)
        assert result is False

    # ============ ТЗ: encrypted USDZ → rejected ============

    def test_encrypted_usdz_rejected(self, tmp_path):
        """
        ТЗ: encrypted USDZ → rejected

        Создаем зашифрованный USDZ с помощью pyzipper (AES-256)
        и проверяем, что валидатор отклоняет его.
        Для создания зашифрованного архива используем pyzipper,
        так как стандартный zipfile не поддерживает шифрование.
        """
        try:
            import pyzipper
        except ImportError:
            pytest.skip("pyzipper not installed, run: pip install pyzipper")

        encrypted_path = tmp_path / "encrypted.usdz"

        # Создаем зашифрованный USDZ с AES-256
        with pyzipper.AESZipFile(
                encrypted_path,
                'w',
                compression=pyzipper.ZIP_STORED,  # USDZ требует без сжатия
                encryption=pyzipper.WZ_AES
        ) as zf:
            zf.setpassword(b'test123')
            zf.writestr('model.usda', '#usda 1.0\n')

        # Проверяем, что валидатор отклоняет зашифрованный файл
        result = ValidatorFactory.validate(encrypted_path)
        assert result is False, "Encrypted USDZ should be rejected"

    # ============ ТЗ: unsupported .obj → rejected ============

    def test_unsupported_obj_rejected(self, tmp_path):
        """ТЗ: unsupported .obj → rejected"""
        obj_file = tmp_path / "model.obj"
        obj_file.write_text("v 0.0 0.0 0.0")

        with pytest.raises(UnsupportedARModelFormatException):
            ValidatorFactory.validate(obj_file)

    # ============ ТЗ: unsupported .fbx → rejected ============

    def test_unsupported_fbx_rejected(self, tmp_path):
        """ТЗ: unsupported .fbx → rejected"""
        fbx_file = tmp_path / "model.fbx"
        fbx_file.write_text("Fake FBX content")

        with pytest.raises(UnsupportedARModelFormatException):
            ValidatorFactory.validate(fbx_file)

    # ============ ТЗ: oversized file → rejected ============

    def test_oversized_file_rejected(self, tmp_path):
        """ТЗ: oversized file → rejected"""
        from app.core.config import settings

        oversized_file = tmp_path / "oversized.glb"
        # Создаем файл на 1 байт больше допустимого размера
        oversized_size = settings.ar_max_file_size + 1
        with open(oversized_file, 'wb') as f:
            f.write(b'\x00' * oversized_size)

        with pytest.raises(ARModelFileTooLargeException):
            ValidatorFactory.validate(oversized_file)

    # ============ ТЗ: compressed USDZ → rejected ============

    def test_compressed_usdz_rejected(self, tmp_path):
        """ТЗ: compressed USDZ → rejected (из пункта encrypted/compressed invalid USDZ)"""
        compressed_path = tmp_path / "compressed.usdz"

        # Создаем USDZ со сжатием (нарушает спецификацию)
        with zipfile.ZipFile(compressed_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('model.usda', '#usda 1.0\n')

        result = ValidatorFactory.validate(compressed_path)
        assert result is False, "Compressed USDZ should be rejected"
