from __future__ import annotations

import unittest
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cairn.schema import parse_schema


class SchemaTests(unittest.TestCase):
    def test_parse_types_and_tags(self) -> None:
        schema = parse_schema(
            "# Cairn Schema\n\n"
            "Profile: `engineering`\n\n"
            "## Types\n\n"
            "- Runbook\n"
            "- Decision\n\n"
            "## Tags\n\n"
            "- bug\n"
            "- deploy\n"
        )

        self.assertEqual(schema.profile, "engineering")
        self.assertEqual(schema.types, {"Runbook", "Decision"})
        self.assertEqual(schema.tags, {"bug", "deploy"})


if __name__ == "__main__":
    unittest.main()
