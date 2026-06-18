# Quick Install

This guide installs the ApolloKairn CLI from standalone binaries published on GitHub
Releases. This path does not require Python on the user's machine.

The installer installs the `apollokairn` command plus the `ak` and `cairn`
compatibility aliases. Your Markdown vault is created afterwards, wherever you
choose.

## Install

Linux and macOS:

```bash
curl -fsSL https://sinkz.github.io/apollokairn/install.sh | sh
```

Windows PowerShell:

```powershell
irm https://sinkz.github.io/apollokairn/install.ps1 | iex
```

Verify the install:

```bash
apollokairn --version
apollokairn --help
```

## Create A Vault After Installing

Choose the vault path yourself. The installer does not create or move notes.

Linux and macOS:

```bash
apollokairn init --path ~/ApolloKairnVault --profile personal
apollokairn validate --path ~/ApolloKairnVault
apollokairn index --path ~/ApolloKairnVault --rebuild
apollokairn doctor --path ~/ApolloKairnVault
```

Windows PowerShell:

```powershell
apollokairn init --path "$env:USERPROFILE\ApolloKairnVault" --profile personal
apollokairn validate --path "$env:USERPROFILE\ApolloKairnVault"
apollokairn index --path "$env:USERPROFILE\ApolloKairnVault" --rebuild
apollokairn doctor --path "$env:USERPROFILE\ApolloKairnVault"
```

## What The Installers Do

The scripts:

- detect your OS and CPU architecture;
- download the matching binary from GitHub Releases;
- download `checksums.txt`;
- verify the SHA-256 checksum;
- install the binary in a user-level directory;
- run `apollokairn --version` at the end.

The current environment variables are `APOLLOKAIRN_VERSION`,
`APOLLOKAIRN_INSTALL_DIR`, and `APOLLOKAIRN_REPO`. The installers still honor
legacy `CAIRN_VERSION`, `CAIRN_INSTALL_DIR`, and `CAIRN_REPO` fallbacks during
the rename window.

Default install paths:

| Platform | Default path |
| --- | --- |
| Linux | `~/.local/bin/apollokairn` |
| macOS | `~/.local/bin/apollokairn` |
| Windows | `%LOCALAPPDATA%\Programs\ApolloKairn\bin\apollokairn.exe` |

Published release assets:

| Platform | Asset |
| --- | --- |
| Linux x64 | `apollokairn-linux-x64.tar.gz` |
| Linux arm64 | `apollokairn-linux-arm64.tar.gz` |
| macOS x64 | `apollokairn-macos-x64.tar.gz` |
| macOS arm64 | `apollokairn-macos-arm64.tar.gz` |
| Windows x64 | `apollokairn-windows-x64.zip` |

The Linux x64 release is built in a Debian 11 container with glibc 2.31 to keep
the binary usable on older distributions. If your system is older than that or
uses a non-glibc libc, install from source instead.

## Install A Specific Version

Linux and macOS:

```bash
curl -fsSL https://sinkz.github.io/apollokairn/install.sh | APOLLOKAIRN_VERSION=v0.1.2 sh
```

Windows PowerShell:

```powershell
$env:APOLLOKAIRN_VERSION = "v0.1.2"
irm https://sinkz.github.io/apollokairn/install.ps1 | iex
```

## Install Somewhere Else

Linux and macOS:

```bash
curl -fsSL https://sinkz.github.io/apollokairn/install.sh | APOLLOKAIRN_INSTALL_DIR="$HOME/bin" sh
```

Windows PowerShell:

```powershell
$env:APOLLOKAIRN_INSTALL_DIR = "$env:USERPROFILE\bin"
irm https://sinkz.github.io/apollokairn/install.ps1 | iex
```

## Troubleshooting

### `apollokairn: command not found`

The binary installed, but your shell cannot find the install directory.

Linux and macOS, for the current shell:

```bash
export PATH="$HOME/.local/bin:$PATH"
apollokairn --version
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
$env:Path = "$env:LOCALAPPDATA\Programs\ApolloKairn\bin;$env:Path"
apollokairn --version
```

If the installer already added the user PATH, restart the terminal. If it did
not, add it manually:

```powershell
$dir = "$env:LOCALAPPDATA\Programs\ApolloKairn\bin"
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
[Environment]::SetEnvironmentVariable("Path", "$userPath;$dir", "User")
```

### Download returns 404

The requested release or asset does not exist. Check the latest release:

```text
https://github.com/sinkz/apollokairn/releases
```

If no binary release has been published yet, install from source for development:

```bash
git clone https://github.com/sinkz/apollokairn.git
cd apollokairn
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
curl -fsSL https://sinkz.github.io/apollokairn/install.sh | APOLLOKAIRN_INSTALL_DIR="$HOME/.local/bin" sh
```

If the file exists but is not executable:

```bash
chmod +x "$HOME/.local/bin/apollokairn"
```

### macOS says the binary cannot be opened

Until releases are signed and notarized, macOS may block the binary after a
browser download. If you trust the GitHub Release and checksum, remove the
quarantine attribute:

```bash
xattr -dr com.apple.quarantine "$HOME/.local/bin/apollokairn"
apollokairn --version
```

### Corporate proxy or TLS inspection blocks the script

Download the matching release asset and `checksums.txt` manually from GitHub
Releases, verify the SHA-256 hash, then place `apollokairn` in a directory on `PATH`.

Manual Linux x64 example:

```bash
mkdir -p "$HOME/.local/bin"
curl -fL -o /tmp/apollokairn-linux-x64.tar.gz https://github.com/sinkz/apollokairn/releases/latest/download/apollokairn-linux-x64.tar.gz
curl -fL -o /tmp/checksums.txt https://github.com/sinkz/apollokairn/releases/latest/download/checksums.txt
cd /tmp
grep '  apollokairn-linux-x64.tar.gz$' checksums.txt | sha256sum -c -
tar -xzf apollokairn-linux-x64.tar.gz -C "$HOME/.local/bin"
chmod +x "$HOME/.local/bin/apollokairn"
apollokairn --version
```

On macOS, replace `sha256sum -c -` with:

```bash
grep '  apollokairn-macos-arm64.tar.gz$' checksums.txt | shasum -a 256 -c -
```

## Uninstall

Linux and macOS:

```bash
rm -f "$HOME/.local/bin/apollokairn" "$HOME/.local/bin/ak" "$HOME/.local/bin/cairn"
```

Windows PowerShell:

```powershell
Remove-Item "$env:LOCALAPPDATA\Programs\ApolloKairn\bin\apollokairn.exe"
Remove-Item "$env:LOCALAPPDATA\Programs\ApolloKairn\bin\ak.exe" -ErrorAction SilentlyContinue
Remove-Item "$env:LOCALAPPDATA\Programs\ApolloKairn\bin\cairn.exe" -ErrorAction SilentlyContinue
```

This does not delete your vault. Remove the vault directory only if you no
longer want the Markdown notes.
