from __future__ import annotations

import unittest
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cairn.profiles import get_profile, list_profiles
from cairn.templates import render_agents_md, render_schema_md


class ProfileTests(unittest.TestCase):
    def test_profiles_include_core_domains(self) -> None:
        self.assertEqual(
            list_profiles(),
            ["custom", "engineering", "personal", "product", "support"],
        )

    def test_engineering_profile_has_runbook_type(self) -> None:
        profile = get_profile("engineering")

        self.assertIn("Runbook", profile.types)
        self.assertIn("bug", profile.tags)
        self.assertIn("processes", profile.folders)

    def test_schema_template_lists_types_and_tags(self) -> None:
        profile = get_profile("support")
        text = render_schema_md(profile)

        self.assertIn("# ApolloKairn Schema", text)
        self.assertIn("## Types", text)
        self.assertIn("- Procedure", text)
        self.assertIn("## Tags", text)
        self.assertIn("- escalation", text)

    def test_agents_template_contains_top_three_rule(self) -> None:
        profile = get_profile("personal")
        text = render_agents_md(profile)

        self.assertIn("apollokairn search", text)
        self.assertIn("Open at most the top 3", text)
        self.assertIn("SCHEMA.md", text)
        self.assertIn("--body-file", text)
        self.assertIn("apollokairn index", text)
        self.assertIn("Never store secrets", text)


if __name__ == "__main__":
    unittest.main()
