# Instalação Rápida

Este guia instala a CLI do Cairn usando binários standalone publicados no
GitHub Releases. Este caminho não exige Python instalado na máquina do usuário.

O instalador só instala o comando `cairn`. O vault em Markdown é criado depois,
no diretório que você escolher.

## Instalar

Linux e macOS:

```bash
curl -fsSL https://sinkz.github.io/cairn/install.sh | sh
```

Windows PowerShell:

```powershell
irm https://sinkz.github.io/cairn/install.ps1 | iex
```

Verifique a instalação:

```bash
cairn --version
cairn --help
```

## Criar Um Vault Depois De Instalar

Escolha o caminho do vault. O instalador não cria nem move notas.

Linux e macOS:

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

## O Que Os Instaladores Fazem

Os scripts:

- detectam sistema operacional e arquitetura;
- baixam o binário correto do GitHub Releases;
- baixam `checksums.txt`;
- validam o checksum SHA-256;
- instalam o binário em um diretório do usuário;
- executam `cairn --version` no final.

Caminhos padrão:

| Plataforma | Caminho padrão |
| --- | --- |
| Linux | `~/.local/bin/cairn` |
| macOS | `~/.local/bin/cairn` |
| Windows | `%LOCALAPPDATA%\Programs\Cairn\bin\cairn.exe` |

Artefatos publicados em release:

| Plataforma | Artefato |
| --- | --- |
| Linux x64 | `cairn-linux-x64.tar.gz` |
| Linux arm64 | `cairn-linux-arm64.tar.gz` |
| macOS x64 | `cairn-macos-x64.tar.gz` |
| macOS arm64 | `cairn-macos-arm64.tar.gz` |
| Windows x64 | `cairn-windows-x64.zip` |

## Instalar Uma Versão Específica

Linux e macOS:

```bash
curl -fsSL https://sinkz.github.io/cairn/install.sh | CAIRN_VERSION=v0.1.0 sh
```

Windows PowerShell:

```powershell
$env:CAIRN_VERSION = "v0.1.0"
irm https://sinkz.github.io/cairn/install.ps1 | iex
```

## Instalar Em Outro Diretório

Linux e macOS:

```bash
curl -fsSL https://sinkz.github.io/cairn/install.sh | CAIRN_INSTALL_DIR="$HOME/bin" sh
```

Windows PowerShell:

```powershell
$env:CAIRN_INSTALL_DIR = "$env:USERPROFILE\bin"
irm https://sinkz.github.io/cairn/install.ps1 | iex
```

## Solução De Problemas

### `cairn: command not found`

O binário foi instalado, mas o shell não encontrou o diretório de instalação.

Linux e macOS, para o shell atual:

```bash
export PATH="$HOME/.local/bin:$PATH"
cairn --version
```

Para manter em novos terminais:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
```

Se você usa Bash em vez de Zsh:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
```

Windows PowerShell, para a sessão atual:

```powershell
$env:Path = "$env:LOCALAPPDATA\Programs\Cairn\bin;$env:Path"
cairn --version
```

Se o instalador já adicionou o PATH do usuário, reinicie o terminal. Se não
adicionou, faça manualmente:

```powershell
$dir = "$env:LOCALAPPDATA\Programs\Cairn\bin"
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
[Environment]::SetEnvironmentVariable("Path", "$userPath;$dir", "User")
```

### Download retorna 404

A release ou o artefato solicitado não existe. Confira a release mais recente:

```text
https://github.com/sinkz/cairn/releases
```

Se ainda não houver release com binários, instale pelo código fonte para
desenvolvimento:

```bash
git clone https://github.com/sinkz/cairn.git
cd cairn
python -m pip install -e .
```

### Checksum não confere

Não ignore o checksum. Apague o download temporário e tente de novo. Se o
problema continuar, confira a página da release no GitHub e abra uma issue com
nome do artefato, sistema operacional, arquitetura e entrada de `checksums.txt`.

### Permissão negada no Linux ou macOS

Use um diretório que pertence ao usuário:

```bash
mkdir -p "$HOME/.local/bin"
curl -fsSL https://sinkz.github.io/cairn/install.sh | CAIRN_INSTALL_DIR="$HOME/.local/bin" sh
```

Se o arquivo existe, mas não está executável:

```bash
chmod +x "$HOME/.local/bin/cairn"
```

### macOS diz que o binário não pode ser aberto

Enquanto as releases não forem assinadas e notarizadas, o macOS pode bloquear o
binário depois de um download pelo navegador. Se você confia na release do
GitHub e no checksum, remova o atributo de quarentena:

```bash
xattr -dr com.apple.quarantine "$HOME/.local/bin/cairn"
cairn --version
```

### Proxy corporativo ou inspeção TLS bloqueia o script

Baixe manualmente o artefato da sua plataforma e `checksums.txt` pelo GitHub
Releases, valide o hash SHA-256 e coloque `cairn` em um diretório no `PATH`.

Exemplo manual para Linux x64:

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

No macOS, troque `sha256sum -c -` por:

```bash
grep '  cairn-macos-arm64.tar.gz$' checksums.txt | shasum -a 256 -c -
```

## Desinstalar

Linux e macOS:

```bash
rm -f "$HOME/.local/bin/cairn"
```

Windows PowerShell:

```powershell
Remove-Item "$env:LOCALAPPDATA\Programs\Cairn\bin\cairn.exe"
```

Isso não apaga o vault. Remova o diretório do vault apenas se você não quiser
mais manter as notas Markdown.
