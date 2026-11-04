"""Read-only structural and privacy checks for already-public image assets.

These tests verify file format and metadata containment only; they DO NOT
certify artwork ownership, permission to publish, KJV textual accuracy,
delivery to a social account, or rights in any image.
"""
from __future__ import annotations

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
MEDIA_DIRS = ("posts", "stories")
PATH_PATTERN = re.compile(
    r"(?:posts|stories)/20[0-9]{2}/(?:0[1-9]|1[0-2])/"
    r"20[0-9]{2}-[0-9]{2}-[0-9]{2}-[a-f0-9]{12}\.jpg"
)


def media_files():
    return sorted(file for top in MEDIA_DIRS
                  for file in (ROOT / top).rglob("*") if file.is_file())


class PublicMediaStructure(unittest.TestCase):
    def test_assets_exist_in_both_public_delivery_lanes(self):
        for top in MEDIA_DIRS:
            self.assertTrue(any((ROOT / top).rglob("*.jpg")), top)

    def test_assets_use_bounded_relative_date_names(self):
        for item in media_files():
            self.assertTrue(PATH_PATTERN.fullmatch(item.relative_to(ROOT).as_posix()),
                            item.relative_to(ROOT))

    def test_all_media_files_are_regular_not_symlinks(self):
        for item in media_files():
            self.assertFalse(item.is_symlink(), item)
            self.assertTrue(item.stat().st_size > 4, item)

    def test_public_media_have_jpeg_markers(self):
        for item in media_files():
            content = item.read_bytes()
            self.assertTrue(content.startswith(b"\xff\xd8"), item)
            self.assertTrue(content.endswith(b"\xff\xd9"), item)

    def test_no_embedded_exif_metadata_in_public_images(self):
        for item in media_files():
            self.assertNotIn(b"Exif\x00\x00", item.read_bytes(),
                             "Public image contains EXIF; review before distribution: "+item.name)

    def test_source_boundary_has_explicit_support_documentation(self):
        self.assertTrue((ROOT / "README.md").is_file())
        self.assertTrue((ROOT / "SECURITY.md").is_file())


if __name__ == "__main__":
    unittest.main()
