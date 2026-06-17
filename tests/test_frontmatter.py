from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cairn.frontmatter import FrontmatterError, parse_document


class FrontmatterTests(unittest.TestCase):
    def test_parse_simple_frontmatter(self) -> None:
        doc = parse_document(
            "---\n"
            "type: Note\n"
            "title: Demo\n"
            "tags: [personal, workflow]\n"
            "aliases:\n"
            "  - setup\n"
            "  - bootstrap\n"
            "---\n\n"
            "# Body\n"
        )

        self.assertEqual(doc.frontmatter["type"], "Note")
        self.assertEqual(doc.frontmatter["title"], "Demo")
        self.assertEqual(doc.frontmatter["tags"], ["personal", "workflow"])
        self.assertEqual(doc.frontmatter["aliases"], ["setup", "bootstrap"])
        self.assertEqual(doc.body, "# Body\n")

    def test_crlf_body_separator_is_trimmed(self) -> None:
        doc = parse_document("---\r\ntype: Note\r\n---\r\n\r\n# Body\r\n")

        self.assertEqual(doc.body, "# Body\r\n")

    def test_missing_frontmatter_raises(self) -> None:
        with self.assertRaises(FrontmatterError):
            parse_document("# Body only\n")

    def test_unclosed_frontmatter_raises(self) -> None:
        with self.assertRaises(FrontmatterError):
            parse_document("---\ntype: Note\n")

    def test_rejects_unsupported_indented_mapping(self) -> None:
        with self.assertRaises(FrontmatterError):
            parse_document("---\ntype: Note\nmetadata:\n  owner: Diego\n---\n")


if __name__ == "__main__":
    unittest.main()
