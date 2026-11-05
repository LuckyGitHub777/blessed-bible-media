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



def jpeg_header_markers(content: bytes):
    """Yield pre-image JPEG markers; reject truncated or malformed headers."""
    if not content.startswith(b"\xff\xd8"):
        raise ValueError("Missing JPEG start marker")
    offset = 2
    while offset < len(content):
        if content[offset] != 0xFF:
            raise ValueError("Malformed JPEG marker sequence")
        while offset < len(content) and content[offset] == 0xFF:
            offset += 1
        if offset >= len(content):
            raise ValueError("Truncated JPEG marker")
        marker = content[offset]
        offset += 1
        if marker == 0xDA:  # Start of entropy-coded image data
            return
        if marker == 0xD9:
            raise ValueError("JPEG ended before image data")
        if marker == 0x01 or 0xD0 <= marker <= 0xD7:
            yield marker
            continue
        if offset + 2 > len(content):
            raise ValueError("Truncated JPEG segment length")
        size = (content[offset] << 8) | content[offset + 1]
        if size < 2 or offset + size > len(content):
            raise ValueError("Malformed JPEG segment length")
        yield marker
        offset += size
    raise ValueError("Missing JPEG image data marker")


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


    def test_no_app1_iptc_or_jpeg_comments_in_public_images(self):
        # APP1 commonly carries EXIF/XMP; APP13 carries IPTC/Photoshop
        # metadata, while COM can contain freeform creator or location text.
        forbidden = {0xE1, 0xED, 0xFE}
        for item in media_files():
            markers = set(jpeg_header_markers(item.read_bytes()))
            self.assertFalse(
                markers & forbidden,
                "Public JPEG contains a metadata-bearing segment: " + item.name,
            )

    def test_metadata_header_guard_rejects_synthetic_injection(self):
        for marker in (0xE1, 0xED, 0xFE):
            synthetic = (
                b"\xff\xd8" + bytes((0xFF, marker, 0, 4)) +
                b"AB" + b"\xff\xda\x00\x02" + b"\x00\xff\xd9"
            )
            with self.subTest(marker=marker):
                self.assertIn(marker, list(jpeg_header_markers(synthetic)))

    def test_truncated_jpeg_metadata_segment_is_rejected(self):
        with self.assertRaises(ValueError):
            list(jpeg_header_markers(b"\xff\xd8\xff\xe1\x00\x12AB\xff\xd9"))

    def test_source_boundary_has_explicit_support_documentation(self):
        self.assertTrue((ROOT / "README.md").is_file())
        self.assertTrue((ROOT / "SECURITY.md").is_file())


    def test_visual_gallery_references_only_existing_public_images(self):
        """Every displayed archive tile must point to the existing local image."""
        gallery_path = ROOT / "GALLERY.md"
        self.assertTrue(gallery_path.is_file())
        gallery = gallery_path.read_text(encoding="utf-8")
        tiles = re.findall(
            r"\[!\[[^\]]+\]\(([^)]+)\)\]\(([^)]+)\)",
            gallery,
        )
        self.assertGreaterEqual(len(tiles), 60)
        seen = set()
        for preview, original in tiles:
            self.assertEqual(preview, original)
            self.assertTrue(PATH_PATTERN.fullmatch(preview), preview)
            self.assertTrue((ROOT / preview).is_file(), preview)
            self.assertNotIn(preview, seen, "Duplicate gallery tile: " + preview)
            seen.add(preview)

    def test_collection_readme_opens_the_gallery(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("[Open the visual archive](GALLERY.md)", readme)


if __name__ == "__main__":
    unittest.main()
