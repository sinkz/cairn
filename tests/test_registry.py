from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


def make_vault(path: Path) -> None:
    (path / ".cairn").mkdir(parents=True)
    (path / ".cairn" / "config.json").write_text('{"profile": "personal"}\n', encoding="utf-8")


class RegistryTests(unittest.TestCase):
    def isolated_registry(self, temp: Path) -> dict[str, str]:
        return {"APOLLOKAIRN_REGISTRY_PATH": str(temp / "registry.json")}

    def test_add_vault_persists_named_record(self) -> None:
        from cairn.registry import add_vault, load_registry

        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, self.isolated_registry(Path(tmp))):
            vault = Path(tmp) / "personal"
            make_vault(vault)

            record = add_vault(vault, name="personal")
            registry = load_registry()

        self.assertEqual(record.name, "personal")
        self.assertEqual(record.path, vault.resolve())
        self.assertIn("personal", registry.vaults)
        self.assertIsNone(registry.active)

    def test_add_vault_can_mark_record_active(self) -> None:
        from cairn.registry import add_vault, current_vault

        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, self.isolated_registry(Path(tmp))):
            vault = Path(tmp) / "work"
            make_vault(vault)

            add_vault(vault, name="work", set_active=True)
            current = current_vault()

        self.assertIsNotNone(current)
        self.assertEqual(current.name, "work")
        self.assertEqual(current.path, vault.resolve())

    def test_duplicate_name_fails(self) -> None:
        from cairn.registry import RegistryError, add_vault

        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, self.isolated_registry(Path(tmp))):
            vault = Path(tmp) / "work"
            make_vault(vault)
            add_vault(vault, name="work")

            with self.assertRaisesRegex(RegistryError, "already registered"):
                add_vault(vault, name="work")

    def test_use_vault_switches_active_record(self) -> None:
        from cairn.registry import add_vault, current_vault, use_vault

        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, self.isolated_registry(Path(tmp))):
            personal = Path(tmp) / "personal"
            work = Path(tmp) / "work"
            make_vault(personal)
            make_vault(work)
            add_vault(personal, name="personal", set_active=True)
            add_vault(work, name="work")

            active = use_vault("work")
            current = current_vault()

        self.assertEqual(active.name, "work")
        self.assertEqual(current.name, "work")

    def test_use_vault_does_not_switch_to_stale_record(self) -> None:
        from cairn.registry import RegistryError, add_vault, current_vault, use_vault

        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, self.isolated_registry(Path(tmp))):
            valid = Path(tmp) / "valid"
            stale = Path(tmp) / "stale"
            make_vault(valid)
            make_vault(stale)
            add_vault(valid, name="valid", set_active=True)
            add_vault(stale, name="stale")
            shutil.rmtree(stale)

            with self.assertRaises(RegistryError):
                use_vault("stale")
            current = current_vault()

        self.assertEqual(current.name, "valid")

    def test_remove_active_vault_clears_current(self) -> None:
        from cairn.registry import add_vault, current_vault, remove_vault

        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, self.isolated_registry(Path(tmp))):
            vault = Path(tmp) / "personal"
            make_vault(vault)
            add_vault(vault, name="personal", set_active=True)

            removed = remove_vault("personal")
            current = current_vault()

        self.assertEqual(removed.name, "personal")
        self.assertIsNone(current)

    def test_doctor_reports_missing_and_invalid_vaults(self) -> None:
        from cairn.registry import add_vault, doctor_vaults

        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, self.isolated_registry(Path(tmp))):
            valid = Path(tmp) / "valid"
            invalid = Path(tmp) / "invalid"
            missing = Path(tmp) / "missing"
            make_vault(valid)
            make_vault(invalid)
            make_vault(missing)
            add_vault(valid, name="valid", set_active=True)
            add_vault(invalid, name="invalid")
            add_vault(missing, name="missing")
            (invalid / ".cairn" / "config.json").unlink()
            shutil.rmtree(missing)

            statuses = {item.name: item for item in doctor_vaults()}

        self.assertTrue(statuses["valid"].exists)
        self.assertTrue(statuses["valid"].is_vault)
        self.assertTrue(statuses["valid"].active)
        self.assertTrue(statuses["invalid"].exists)
        self.assertFalse(statuses["invalid"].is_vault)
        self.assertFalse(statuses["missing"].exists)
        self.assertFalse(statuses["missing"].is_vault)

    def test_resolve_prefers_path_then_named_vault_then_active_then_current_directory(self) -> None:
        from cairn.registry import add_vault, resolve_vault_path

        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, self.isolated_registry(Path(tmp))):
            explicit = Path(tmp) / "explicit"
            named = Path(tmp) / "named"
            active = Path(tmp) / "active"
            make_vault(explicit)
            make_vault(named)
            make_vault(active)
            add_vault(named, name="named")
            add_vault(active, name="active", set_active=True)

            self.assertEqual(resolve_vault_path(path=explicit, vault_name="named"), explicit.resolve())
            self.assertEqual(resolve_vault_path(path=None, vault_name="named"), named.resolve())
            self.assertEqual(resolve_vault_path(path=None, vault_name=None), active.resolve())

        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, self.isolated_registry(Path(tmp))):
            self.assertEqual(resolve_vault_path(path=None, vault_name=None), Path.cwd())


if __name__ == "__main__":
    unittest.main()
