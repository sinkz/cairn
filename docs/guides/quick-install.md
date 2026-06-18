# Quick Install

This guide installs the Cairn CLI from standalone binaries published on GitHub
Releases. This path does not require Python on the user's machine.

The installer only installs the `cairn` command. Your Markdown vault is created
afterwards, wherever you choose.

## Install

Linux and macOS:

```bash
curl -fsSL https://sinkz.github.io/cairn/install.sh | sh
```

Windows PowerShell:

```powershell
irm https://sinkz.github.io/cairn/install.ps1 | iex
```

Verify the install:

```bash
cairn --version
cairn --help
```

## Create A Vault After Installing

Choose the vault path yourself. The installer does not create or move notes.

Linux and macOS:

```bash
cairn init --path ~/CairnVault --profile personal
cairn validate --path ~/CairnVault
cairn index --path ~/CairnVault --rebuild
cairn doctor --path ~/CairnVault
```

Windows PowerShell:

```powershell
cairn init --path "$env:USERPROFILE\CairnVault" --profile personal
cairn validate --path "$env:USERPROFILE\CairnVault"
cairn index --path "$env:USERPROFILE\CairnVault" --rebuild
cairn doctor --path "$env:USERPROFILE\CairnVault"
```

## What The Installers Do

The scripts:

- detect your OS and CPU architecture;
- download the matching binary from GitHub Releases;
- download `checksums.txt`;
- verify the SHA-256 checksum;
- install the binary in a user-level directory;
- run `cairn --version` at the end.

Default install paths:

| Platform | Default path |
| --- | --- |
| Linux | `~/.local/bin/cairn` |
| macOS | `~/.local/bin/cairn` |
| Windows | `%LOCALAPPDATA%\Programs\Cairn\bin\cairn.exe` |

Published release assets:

| Platform | Asset |
| --- | --- |
| Linux x64 | `cairn-linux-x64.tar.gz` |
| Linux arm64 | `cairn-linux-arm64.tar.gz` |
| macOS x64 | `cairn-macos-x64.tar.gz` |
| macOS arm64 | `cairn-macos-arm64.tar.gz` |
| Windows x64 | `cairn-windows-x64.zip` |

## Install A Specific Version

Linux and macOS:

```bash
curl -fsSL https://sinkz.github.io/cairn/install.sh | CAIRN_VERSION=v0.1.0 sh
```

Windows PowerShell:

```powershell
$env:CAIRN_VERSION = "v0.1.0"
irm https://sinkz.github.io/cairn/install.ps1 | iex
```

## Install Somewhere Else

Linux and macOS:

```bash
curl -fsSL https://sinkz.github.io/cairn/install.sh | CAIRN_INSTALL_DIR="$HOME/bin" sh
```

Windows PowerShell:

```powershell
$env:CAIRN_INSTALL_DIR = "$env:USERPROFILE\bin"
irm https://sinkz.github.io/cairn/install.ps1 | iex
```

## Troubleshooting

### `cairn: command not found`

The binary installed, but your shell cannot find the install directory.

Linux and macOS, for the current shell:

```bash
export PATH="$HOME/.local/bin:$PATH"
cairn --version
```

Persist it for future shells:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
```

If you use Bash instead of Zsh:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
```

Windows PowerShell, for the current session:

```powershell
$env:Path = "$env:LOCALAPPDATA\Programs\Cairn\bin;$env:Path"
cairn --version
```

If the installer already added the user PATH, restart the terminal. If it did
not, add it manually:

```powershell
$dir = "$env:LOCALAPPDATA\Programs\Cairn\bin"
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
[Environment]::SetEnvironmentVariable("Path", "$userPath;$dir", "User")
```

### Download returns 404

The requested release or asset does not exist. Check the latest release:

```text
https://github.com/sinkz/cairn/releases
```

If no binary release has been published yet, install from source for development:

```bash
git clone https://github.com/sinkz/cairn.git
cd cairn
python -m pip install -e .
```

### Checksum mismatch

Do not bypass the checksum. Delete the temporary download and retry. If the
problem persists, check the GitHub Release page and open an issue with the
asset name, OS, architecture, and `checksums.txt` entry.

### Permission denied on Linux or macOS

Use a user-owned install directory:

```bash
mkdir -p "$HOME/.local/bin"
curl -fsSL https://sinkz.github.io/cairn/install.sh | CAIRN_INSTALL_DIR="$HOME/.local/bin" sh
```

If the file exists but is not executable:

```bash
chmod +x "$HOME/.local/bin/cairn"
```

### macOS says the binary cannot be opened

Until releases are signed and notarized, macOS may block the binary after a
browser download. If you trust the GitHub Release and checksum, remove the
quarantine attribute:

```bash
xattr -dr com.apple.quarantine "$HOME/.local/bin/cairn"
cairn --version
```

### Corporate proxy or TLS inspection blocks the script

Download the matching release asset and `checksums.txt` manually from GitHub
Releases, verify the SHA-256 hash, then place `cairn` in a directory on `PATH`.

Manual Linux x64 example:

```bash
mkdir -p "$HOME/.local/bin"
curl -fL -o /tmp/cairn-linux-x64.tar.gz https://github.com/sinkz/cairn/releases/latest/download/cairn-linux-x64.tar.gz
curl -fL -o /tmp/checksums.txt https://github.com/sinkz/cairn/releases/latest/download/checksums.txt
cd /tmp
grep '  cairn-linux-x64.tar.gz$' checksums.txt | sha256sum -c -
tar -xzf cairn-linux-x64.tar.gz -C "$HOME/.local/bin"
chmod +x "$HOME/.local/bin/cairn"
cairn --version
```

On macOS, replace `sha256sum -c -` with:

```bash
grep '  cairn-macos-arm64.tar.gz$' checksums.txt | shasum -a 256 -c -
```

## Uninstall

Linux and macOS:

```bash
rm -f "$HOME/.local/bin/cairn"
```

Windows PowerShell:

```powershell
Remove-Item "$env:LOCALAPPDATA\Programs\Cairn\bin\cairn.exe"
```

This does not delete your vault. Remove the vault directory only if you no
longer want the Markdown notes.
