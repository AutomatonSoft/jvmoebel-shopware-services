import zipfile

import pytest

from core.config import settings
from domains.ar.exceptions import (
    ARModelFileTooLargeException,
    UnsupportedARModelFormatException,
)
from domains.ar.validators.factory import ValidatorFactory
from domains.ar.validators.usdz_validator import USDZValidator
from scripts.validators.build_dice_usdz import build_dice_usdz
from scripts.validators.pack_glb import pack_glb
from scripts.validators.pack_usdz import USDC_MAGIC, pack_usdz
from tests.validators.ar_files import dice_glb_bytes, dice_glb_bytes_mutated, dice_usdz_bytes


def _validate(generated_ar, name: str, data: bytes) -> bool:
    path = generated_ar(name, data)
    return ValidatorFactory.validate(path)


class TestARValidator:
    def test_valid_glb_accepted(self, generated_ar):
        # ТЗ тесты-1: valid GLB → accepted
        result = _validate(
            generated_ar,
            "valid.glb",
            dice_glb_bytes(),
        )
        assert result is True

    def test_valid_usdz_accepted(self, generated_ar):
        # ТЗ тесты-2: valid USDZ → accepted
        result = _validate(
            generated_ar,
            "valid.usdz",
            dice_usdz_bytes(align=True),
        )
        assert result is True

    def test_corrupted_glb_rejected(self, generated_ar):
        # ТЗ тесты-3: corrupted GLB → rejected
        # ТЗ GLB-9: Нет повреждённых chunks
        valid = dice_glb_bytes()
        result = _validate(
            generated_ar,
            "corrupted.glb",
            valid[: len(valid) // 2],
        )
        assert result is False

    def test_fake_text_file_glb_rejected(self, generated_ar):
        # ТЗ тесты-4: fake text file .glb → rejected
        # ТЗ GLB-2: Magic/header = glTF
        path = generated_ar("fake.glb", b"This is not a real GLB file")
        assert ValidatorFactory.validate(path) is False

    def test_malformed_glb_length_rejected(self, generated_ar):
        # ТЗ тесты-5: malformed GLB length/chunk → rejected
        # ТЗ GLB-4: Declared length = actual length
        result = _validate(
            generated_ar,
            "malformed_length.glb",
            dice_glb_bytes(declared_length=100),
        )
        assert result is False

    def test_glb_version_not_2_rejected(self, generated_ar):
        # ТЗ GLB-3: glTF version = 2
        result = _validate(
            generated_ar,
            "version1.glb",
            dice_glb_bytes(version=1),
        )
        assert result is False

    def test_glb_first_chunk_not_json_rejected(self, generated_ar):
        # ТЗ GLB-6: Первый chunk = JSON
        result = _validate(
            generated_ar,
            "bin_first.glb",
            dice_glb_bytes(first_chunk_type=b"BIN\x00"),
        )
        assert result is False

    def test_glb_invalid_json_rejected(self, generated_ar):
        # ТЗ GLB-7: JSON валиден
        result = _validate(
            generated_ar,
            "bad_json.glb",
            pack_glb(json_bytes=b"{not json"),
        )
        assert result is False

    def test_glb_asset_version_rejected(self, generated_ar):
        # ТЗ GLB-8: asset.version = "2.0"
        def mutate(gltf):
            gltf["asset"]["version"] = "1.0"

        result = _validate(
            generated_ar,
            "asset_1.glb",
            dice_glb_bytes_mutated(mutate),
        )
        assert result is False

    def test_corrupted_usdz_rejected(self, generated_ar):
        # ТЗ тесты-6: corrupted USDZ → rejected
        valid = dice_usdz_bytes(align=True)
        result = _validate(generated_ar, "corrupted.usdz", valid[:20])
        assert result is False

    def test_fake_zip_usdz_rejected(self, generated_ar):
        # ТЗ тесты-7: fake ZIP .usdz → rejected
        result = _validate(
            generated_ar,
            "fake.usdz",
            pack_usdz([("test.txt", "This is a fake USDZ file")], align=True),
        )
        assert result is False

    def test_unsafe_archive_path_rejected(self, generated_ar):
        # ТЗ тесты-8: unsafe archive path ../ → rejected
        # ТЗ USDZ-7: Защита от ../ и absolute paths
        path = generated_ar("unsafe.usdz", b"")
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as zf:
            zf.writestr("../../../etc/passwd", "fake content")
            zf.writestr("dice.usda", build_dice_usdz())
        assert ValidatorFactory.validate(path) is False

    def test_encrypted_usdz_rejected(self, generated_ar):
        # ТЗ тесты-9: encrypted USDZ → rejected
        # ТЗ USDZ-3: Не encrypted
        try:
            import pyzipper
        except ImportError:
            pytest.skip("pyzipper not installed")

        path = generated_ar("encrypted.usdz", b"")
        with pyzipper.AESZipFile(
            path,
            "w",
            compression=pyzipper.ZIP_STORED,
            encryption=pyzipper.WZ_AES,
        ) as zf:
            zf.setpassword(b"test123")
            zf.writestr("dice.usda", build_dice_usdz())

        assert ValidatorFactory.validate(path) is False

    def test_compressed_usdz_rejected(self, generated_ar):
        # ТЗ тесты-10: compressed USDZ → rejected
        # ТЗ USDZ-4: Не compressed (ZIP_STORED)
        result = _validate(
            generated_ar,
            "compressed.usdz",
            dice_usdz_bytes(compress_type=zipfile.ZIP_DEFLATED),
        )
        assert result is False

    def test_invalid_usdz_alignment_rejected(self, generated_ar):
        # ТЗ тесты-11: invalid USDZ alignment → rejected
        # ТЗ USDZ-5: 64-byte alignment
        result = _validate(
            generated_ar,
            "unaligned.usdz",
            dice_usdz_bytes(align=False),
        )
        assert result is False

    def test_usda_without_definition_rejected(self, generated_ar):
        # ТЗ тесты-12: USDA без def/over/class → rejected
        # ТЗ USDZ-6.1: .usda: есть def/over/class или #usda + {}
        invalid_content = """#usda 1.0
( doc = "Test" )
# Just comments and metadata but no actual definition"""
        result = _validate(
            generated_ar,
            "no_definition.usdz",
            pack_usdz([("model.usda", invalid_content)], align=True),
        )
        assert result is False

    def test_glb_blob_uri_rejected(self, generated_ar):
        # ТЗ тесты-13: GLB с blob: URI → rejected
        # ТЗ GLB-11: Self-contained: запрет blob:/external URI
        def mutate(gltf):
            gltf["buffers"][0]["uri"] = "blob:http://example/abc"

        result = _validate(
            generated_ar,
            "blob.glb",
            dice_glb_bytes_mutated(mutate),
        )
        assert result is False

    def test_glb_external_uri_rejected(self, generated_ar):
        # ТЗ GLB-11: Self-contained: запрет blob:/external URI
        def mutate(gltf):
            gltf["images"] = [{"uri": "https://example.com/tex.png"}]

        result = _validate(
            generated_ar,
            "http.glb",
            dice_glb_bytes_mutated(mutate),
        )
        assert result is False

    def test_unsupported_obj_rejected(self, generated_ar):
        # ТЗ тесты-14: unsupported .obj → Exception
        path = generated_ar("model.obj", b"v 0.0 0.0 0.0")
        with pytest.raises(UnsupportedARModelFormatException):
            ValidatorFactory.validate(path)

    def test_unsupported_fbx_rejected(self, generated_ar):
        # ТЗ тесты-15: unsupported .fbx → Exception
        path = generated_ar("model.fbx", b"Fake FBX content")
        with pytest.raises(UnsupportedARModelFormatException):
            ValidatorFactory.validate(path)

    def test_oversized_file_rejected(self, generated_ar):
        # ТЗ тесты-16: oversized file → Exception
        # ТЗ GLB-10: Файл <= AR_MAX_FILE_SIZE
        path = generated_ar(
            "oversized.glb",
            b"\x00" * (settings.ar_max_file_size + 1),
        )
        with pytest.raises(ARModelFileTooLargeException):
            ValidatorFactory.validate(path)

    def test_zip_bomb_entries_rejected(self, generated_ar):
        # ТЗ тесты-17: ZIP bomb (entries > 10000) → rejected
        # ТЗ USDZ-8: ZIP bomb: entries <= 10000
        extra_entries = [(f"e{i}.bin", b"x") for i in range(10001)]
        result = _validate(
            generated_ar,
            "bomb_entries.usdz",
            pack_usdz(
                [("dice.usda", build_dice_usdz()), *extra_entries],
                align=False,
            ),
        )
        assert result is False

    def test_zip_bomb_uncompressed_size_rejected(self, generated_ar, monkeypatch):
        # ТЗ тесты-18: ZIP bomb (uncompressed size > 100 MB) → rejected
        # ТЗ USDZ-9: ZIP bomb: uncompressed size <= 100 MB
        monkeypatch.setattr(USDZValidator, "MAX_UNCOMPRESSED_SIZE", 10)
        result = _validate(
            generated_ar,
            "bomb_size.usdz",
            dice_usdz_bytes(align=True),
        )
        assert result is False

    def test_corrupted_zip_record_rejected(self, generated_ar):
        # ТЗ тесты-19: повреждённый ZIP record → rejected
        # ТЗ USDZ-10: Нет повреждённых archive records (testzip)
        result = _validate(
            generated_ar,
            "bad_crc.usdz",
            dice_usdz_bytes(align=True, corrupt_crc=True),
        )
        assert result is False

    def test_usdc_magic_accepted(self, generated_ar):
        # ТЗ USDZ-6.2: .usdc: сигнатура PXR-USDC
        result = _validate(
            generated_ar,
            "usdc.usdz",
            pack_usdz([("model.usdc", USDC_MAGIC + b"\x00" * 8)], align=True),
        )
        assert result is True

    def test_usdc_bad_magic_rejected(self, generated_ar):
        # ТЗ USDZ-6.2: .usdc: сигнатура PXR-USDC
        result = _validate(
            generated_ar,
            "bad_usdc.usdz",
            pack_usdz([("model.usdc", b"NOT-USDC" + b"\x00" * 8)], align=True),
        )
        assert result is False

    def test_usd_binary_accepted(self, generated_ar):
        # ТЗ USDZ-6.3: .usd: сигнатура PXR-USDC или как .usda
        result = _validate(
            generated_ar,
            "usd_bin.usdz",
            pack_usdz([("model.usd", USDC_MAGIC + b"\x00" * 8)], align=True),
        )
        assert result is True

    def test_usd_text_accepted(self, generated_ar):
        # ТЗ USDZ-6.3: .usd: сигнатура PXR-USDC или как .usda
        result = _validate(
            generated_ar,
            "usd_text.usdz",
            pack_usdz([("model.usd", build_dice_usdz())], align=True),
        )
        assert result is True

    def test_usda_with_def_without_marker_accepted(self, generated_ar):
        # ТЗ USDZ-6.1: .usda: есть def/over/class или #usda + {}
        content = """def Xform "Model"
{
    def Mesh "Cube"
    {
    }
}"""
        result = _validate(
            generated_ar,
            "def_only.usdz",
            pack_usdz([("model.usda", content)], align=True),
        )
        assert result is True

    def test_usdz_without_root_usd_rejected(self, generated_ar):
        # ТЗ USDZ-6: Root USD модель в корне
        result = _validate(
            generated_ar,
            "no_root.usdz",
            pack_usdz(
                [("subfolder/dice.usda", build_dice_usdz())],
                align=True,
            ),
        )
        assert result is False

    def test_windows_absolute_paths_rejected(self, generated_ar):
        # ТЗ USDZ-7: Защита от ../ и absolute paths
        path = generated_ar("win_abs.usdz", b"")
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as zf:
            zf.writestr("dice.usda", build_dice_usdz())
            zf.writestr("C:\\outside\\file.txt", "Should not be allowed")
        assert ValidatorFactory.validate(path) is False

    def test_unix_absolute_paths_rejected(self, generated_ar):
        # ТЗ USDZ-7: Защита от ../ и absolute paths
        path = generated_ar("unix_abs.usdz", b"")
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as zf:
            zf.writestr("dice.usda", build_dice_usdz())
            zf.writestr("/etc/passwd", "Should not be allowed")
        assert ValidatorFactory.validate(path) is False
