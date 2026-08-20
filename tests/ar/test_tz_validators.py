# tests/ar/test_tz_validators.py

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

        # ИСПРАВЛЕНО: теперь это ВАЛИДНЫЙ USDA с структурой
        usda_content = """#usda 1.0
def Xform "Model"
{
    def Mesh "Cube"
    {
        float3[] extent = [(-0.5, -0.5, -0.5), (0.5, 0.5, 0.5)]
    }
}"""

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

        with zipfile.ZipFile(fake_usdz, 'w') as zf:
            zf.writestr('test.txt', 'This is a fake USDZ file')

        result = ValidatorFactory.validate(fake_usdz)
        assert result is False

    # ============ ТЗ: unsafe archive path ../ → rejected ============

    def test_unsafe_archive_path_rejected(self, tmp_path):
        """ТЗ: unsafe archive path ../ → rejected"""
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
        """ТЗ: encrypted USDZ → rejected"""
        try:
            import pyzipper
        except ImportError:
            pytest.skip("pyzipper not installed, run: pip install pyzipper")

        encrypted_path = tmp_path / "encrypted.usdz"

        # Создаем зашифрованный USDZ с AES-256
        with pyzipper.AESZipFile(
                encrypted_path,
                'w',
                compression=pyzipper.ZIP_STORED,
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
        """ТЗ: compressed USDZ → rejected"""
        compressed_path = tmp_path / "compressed.usdz"

        # Создаем USDZ со сжатием (нарушает спецификацию)
        with zipfile.ZipFile(compressed_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('model.usda', '#usda 1.0\n')

        result = ValidatorFactory.validate(compressed_path)
        assert result is False, "Compressed USDZ should be rejected"

    # ============ КРИТИЧЕСКИЕ ТЕСТЫ ДЛЯ USDZ ВАЛИДАТОРА ============

    def test_fake_usda_content_rejected(self, tmp_path):
        """Фальшивый USDA с произвольным текстом → rejected"""
        usdz_path = tmp_path / "fake_usda.usdz"

        with zipfile.ZipFile(usdz_path, 'w', compression=zipfile.ZIP_STORED) as zf:
            zf.writestr('model.usda', 'This is not a valid USD file' * 100)

        result = ValidatorFactory.validate(usdz_path)
        assert result is False, "Fake USDA with random text should be rejected"

    def test_usda_without_usd_marker_but_with_def_accepted(self, tmp_path):
        """
        ИСПРАВЛЕНО: USDA без #usda НО с def - должен быть ПРИНЯТ
        """
        usdz_path = tmp_path / "no_marker.usdz"

        content = """def Xform "Model"
{
    def Mesh "Cube"
    {
        # Some mesh data
    }
}"""

        with zipfile.ZipFile(usdz_path, 'w', compression=zipfile.ZIP_STORED) as zf:
            zf.writestr('model.usda', content)

        result = ValidatorFactory.validate(usdz_path)
        assert result is True, "USDA with def should be accepted even without #usda marker"

    def test_usda_without_definition_rejected(self, tmp_path):
        """USDA без def → rejected"""
        usdz_path = tmp_path / "no_definition.usdz"

        invalid_content = """#usda 1.0
( doc = "Test" )
# Just comments and metadata but no actual definition"""

        with zipfile.ZipFile(usdz_path, 'w', compression=zipfile.ZIP_STORED) as zf:
            zf.writestr('model.usda', invalid_content)

        result = ValidatorFactory.validate(usdz_path)
        assert result is False, "USDA without definition should be rejected"

    def test_windows_absolute_paths_rejected(self, tmp_path):
        """Windows absolute paths → rejected"""
        usdz_path = tmp_path / "win_abs.usdz"

        valid_usda = '#usda 1.0\ndef Xform "Model" { }'

        with zipfile.ZipFile(usdz_path, 'w', compression=zipfile.ZIP_STORED) as zf:
            zf.writestr('model.usda', valid_usda)
            zf.writestr('C:\\outside\\file.txt', 'Should not be allowed')

        result = ValidatorFactory.validate(usdz_path)
        assert result is False, "Windows absolute paths should be rejected"

    def test_windows_traversal_rejected(self, tmp_path):
        """Windows traversal → rejected"""
        usdz_path = tmp_path / "win_traversal.usdz"

        valid_usda = '#usda 1.0\ndef Xform "Model" { }'

        with zipfile.ZipFile(usdz_path, 'w', compression=zipfile.ZIP_STORED) as zf:
            zf.writestr('model.usda', valid_usda)
            zf.writestr('..\\outside\\file.txt', 'Should not be allowed')

        result = ValidatorFactory.validate(usdz_path)
        assert result is False, "Windows traversal paths should be rejected"

    def test_unix_absolute_paths_rejected(self, tmp_path):
        """Unix absolute paths → rejected"""
        usdz_path = tmp_path / "unix_abs.usdz"

        valid_usda = '#usda 1.0\ndef Xform "Model" { }'

        with zipfile.ZipFile(usdz_path, 'w', compression=zipfile.ZIP_STORED) as zf:
            zf.writestr('model.usda', valid_usda)
            zf.writestr('/etc/passwd', 'Should not be allowed')

        result = ValidatorFactory.validate(usdz_path)
        assert result is False, "Unix absolute paths should be rejected"

    def test_unix_traversal_rejected(self, tmp_path):
        """Unix traversal → rejected"""
        usdz_path = tmp_path / "unix_traversal.usdz"

        valid_usda = '#usda 1.0\ndef Xform "Model" { }'

        with zipfile.ZipFile(usdz_path, 'w', compression=zipfile.ZIP_STORED) as zf:
            zf.writestr('model.usda', valid_usda)
            zf.writestr('../../etc/passwd', 'Should not be allowed')

        result = ValidatorFactory.validate(usdz_path)
        assert result is False, "Unix traversal paths should be rejected"

    def test_null_byte_in_filename_handled(self, tmp_path):
        """
        ИСПРАВЛЕНО: Проверяем, что валидатор корректно обрабатывает null bytes
        zipfile сам не позволяет создать файл с null byte, поэтому тест проверяет
        что валидатор не падает и правильно обрабатывает ситуацию
        """
        usdz_path = tmp_path / "null_byte.usdz"

        valid_usda = '#usda 1.0\ndef Xform "Model" { }'

        with zipfile.ZipFile(usdz_path, 'w', compression=zipfile.ZIP_STORED) as zf:
            zf.writestr('model.usda', valid_usda)
            # Пытаемся добавить файл с null byte
            try:
                zf.writestr('malicious\x00file.txt', 'Should not be allowed')
                # Если файл создался - валидатор должен отклонить
                result = ValidatorFactory.validate(usdz_path)
                assert result is False, "Null byte in filename should be rejected"
            except ValueError:
                # zipfile отклонил null byte - это тоже защита, тест пройден
                pass

    def test_combined_attacks_rejected(self, tmp_path):
        """Комбинация атак → rejected"""
        usdz_path = tmp_path / "combined.usdz"

        valid_usda = '#usda 1.0\ndef Xform "Model" { }'

        with zipfile.ZipFile(usdz_path, 'w', compression=zipfile.ZIP_STORED) as zf:
            zf.writestr('model.usda', valid_usda)
            zf.writestr('..\\windows\\outside.txt', 'Should not be allowed')
            zf.writestr('/etc/passwd', 'Should not be allowed')
            zf.writestr('C:\\Windows\\System32\\config', 'Should not be allowed')

        result = ValidatorFactory.validate(usdz_path)
        assert result is False, "Combined attack vectors should be rejected"

    def test_usdz_without_root_usd_rejected(self, tmp_path):
        """USDZ без root USD → rejected"""
        usdz_path = tmp_path / "no_root.usdz"

        with zipfile.ZipFile(usdz_path, 'w', compression=zipfile.ZIP_STORED) as zf:
            zf.writestr('subfolder/model.usda', '#usda 1.0\n')
            zf.writestr('image.png', b'fake image')

        result = ValidatorFactory.validate(usdz_path)
        assert result is False, "USDZ without root USD file should be rejected"

    def test_usdz_with_mixed_separators_and_traversal_rejected(self, tmp_path):
        """Смешанные разделители с traversal → rejected"""
        usdz_path = tmp_path / "mixed_separators.usdz"

        valid_usda = '#usda 1.0\ndef Xform "Model" { }'

        with zipfile.ZipFile(usdz_path, 'w', compression=zipfile.ZIP_STORED) as zf:
            zf.writestr('model.usda', valid_usda)
            zf.writestr('../outside\\file.txt', 'Should not be allowed')

        result = ValidatorFactory.validate(usdz_path)
        assert result is False, "Mixed separators with traversal should be rejected"

    def test_usdz_with_valid_minimal_structure_accepted(self, tmp_path):
        """Минимальный валидный USDA → accepted"""
        usdz_path = tmp_path / "valid_minimal.usdz"

        valid_usda = """#usda 1.0
(
    doc = "Test model"
)

def Xform "Model"
{
    def Mesh "Cube"
    {
        float3[] extent = [(-0.5, -0.5, -0.5), (0.5, 0.5, 0.5)]
        int[] faceVertexCounts = [4, 4, 4, 4, 4, 4]
        int[] faceVertexIndices = [0, 1, 3, 2, 2, 3, 7, 6, 6, 7, 5, 4, 4, 5, 1, 0, 0, 2, 6, 4, 1, 5, 7, 3]
        point3f[] points = [(-0.5, -0.5, 0.5), (0.5, -0.5, 0.5), (-0.5, 0.5, 0.5), (0.5, 0.5, 0.5), (-0.5, -0.5, -0.5), (0.5, -0.5, -0.5), (-0.5, 0.5, -0.5), (0.5, 0.5, -0.5)]
    }
}"""

        with zipfile.ZipFile(usdz_path, 'w', compression=zipfile.ZIP_STORED) as zf:
            zf.writestr('model.usda', valid_usda)

        result = ValidatorFactory.validate(usdz_path)
        assert result is True, "Valid minimal USDA should be accepted"