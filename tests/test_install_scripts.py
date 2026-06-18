from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class InstallScriptTests(unittest.TestCase):
    def test_unix_installer_downloads_release_binary_and_verifies_checksum(self) -> None:
        script = (ROOT / "docs" / "install.sh").read_text(encoding="utf-8")

        self.assertIn("https://github.com/${REPO}/releases", script)
        self.assertIn("/latest/download", script)
        self.assertIn("cairn-linux-x64.tar.gz", script)
        self.assertIn("cairn-linux-arm64.tar.gz", script)
        self.assertIn("cairn-macos-x64.tar.gz", script)
        self.assertIn("cairn-macos-arm64.tar.gz", script)
        self.assertIn("checksums.txt", script)
        self.assertIn("sha256sum", script)
        self.assertIn("shasum -a 256", script)
        self.assertIn("CAIRN_INSTALL_DIR", script)
        self.assertIn("$HOME/.local/bin", script)
        self.assertNotIn("python -m pip", script)
        self.assertNotIn("pip install", script)

    def test_readmes_link_to_quick_install_guides(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        readme_pt = (ROOT / "README.pt-BR.md").read_text(encoding="utf-8")

        self.assertIn("docs/guides/quick-install.md", readme)
        self.assertIn("docs/guides/quick-install.pt-BR.md", readme_pt)
        self.assertIn("curl -fsSL https://sinkz.github.io/cairn/install.sh | sh", readme)
        self.assertIn("irm https://sinkz.github.io/cairn/install.ps1 | iex", readme)
        self.assertIn("curl -fsSL https://sinkz.github.io/cairn/install.sh | sh", readme_pt)
        self.assertIn("irm https://sinkz.github.io/cairn/install.ps1 | iex", readme_pt)

    def test_quick_install_guides_cover_path_troubleshooting_and_vault_creation(self) -> None:
        guide = (ROOT / "docs" / "guides" / "quick-install.md").read_text(encoding="utf-8")
        guide_pt = (ROOT / "docs" / "guides" / "quick-install.pt-BR.md").read_text(encoding="utf-8")

        for text in (guide, guide_pt):
            self.assertIn("install.sh", text)
            self.assertIn("install.ps1", text)
            self.assertIn("cairn --version", text)
            self.assertIn("cairn init", text)
            self.assertIn("CAIRN_INSTALL_DIR", text)
            self.assertIn("PATH", text)
            self.assertIn("checksums.txt", text)
            self.assertIn("GitHub Releases", text)

    def test_landing_links_to_installers_and_guides(self) -> None:
        page = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")

        self.assertIn("id=\"install\"", page)
        self.assertIn("curl -fsSL https://sinkz.github.io/cairn/install.sh | sh", page)
        self.assertIn("irm https://sinkz.github.io/cairn/install.ps1 | iex", page)
        self.assertIn("guides/quick-install.md", page)
        self.assertIn("guides/quick-install.pt-BR.md", page)

    def test_release_workflow_builds_standalone_assets(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

        self.assertIn("tags:", workflow)
        self.assertIn("'v*'", workflow)
        self.assertIn("pyinstaller", workflow)
        self.assertIn("ubuntu-24.04", workflow)
        self.assertIn("ubuntu-24.04-arm", workflow)
        self.assertIn("windows-latest", workflow)
        self.assertIn("macos-15-intel", workflow)
        self.assertIn("macos-15", workflow)
        self.assertIn("cairn-linux-x64.tar.gz", workflow)
        self.assertIn("cairn-linux-arm64.tar.gz", workflow)
        self.assertIn("cairn-windows-x64.zip", workflow)
        self.assertIn("cairn-macos-x64.tar.gz", workflow)
        self.assertIn("cairn-macos-arm64.tar.gz", workflow)
        self.assertIn("checksums.txt", workflow)
        self.assertIn("softprops/action-gh-release", workflow)

    def test_windows_installer_downloads_release_binary_and_verifies_checksum(self) -> None:
        script = (ROOT / "docs" / "install.ps1").read_text(encoding="utf-8")

        self.assertIn("https://github.com/$Repo/releases", script)
        self.assertIn("releases/latest/download", script)
        self.assertIn("cairn-windows-x64.zip", script)
        self.assertIn("checksums.txt", script)
        self.assertIn("Get-FileHash", script)
        self.assertIn("Expand-Archive", script)
        self.assertIn("CAIRN_INSTALL_DIR", script)
        self.assertIn("LOCALAPPDATA", script)
        self.assertNotIn("python -m pip", script)
        self.assertNotIn("pip install", script)


if __name__ == "__main__":
    unittest.main()
