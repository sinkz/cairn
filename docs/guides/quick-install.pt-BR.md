# Instalação Rápida

Este guia instala a CLI do ApolloKairn usando binários standalone publicados no
GitHub Releases. Este caminho não exige Python instalado na máquina do usuário.

O instalador instala o comando `apollokairn` e os aliases de compatibilidade
`ak` e `cairn`. O vault em Markdown é criado depois, no diretório que você
escolher.

## Instalar

Linux e macOS:

```bash
curl -fsSL https://sinkz.github.io/apollokairn/install.sh | sh
```

Windows PowerShell:

```powershell
irm https://sinkz.github.io/apollokairn/install.ps1 | iex
```

Verifique a instalação:

```bash
apollokairn --version
apollokairn --help
```

## Criar Um Vault Depois De Instalar

Escolha o caminho do vault. O instalador não cria nem move notas.

Linux e macOS:

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

## O Que Os Instaladores Fazem

Os scripts:

- detectam sistema operacional e arquitetura;
- baixam o binário correto do GitHub Releases;
- baixam `checksums.txt`;
- validam o checksum SHA-256;
- instalam o binário em um diretório do usuário;
- executam `apollokairn --version` no final.

As variáveis atuais são `APOLLOKAIRN_VERSION`, `APOLLOKAIRN_INSTALL_DIR` e
`APOLLOKAIRN_REPO`. Os instaladores ainda aceitam os fallbacks legados
`CAIRN_VERSION`, `CAIRN_INSTALL_DIR` e `CAIRN_REPO` durante a janela de rename.

Caminhos padrão:

| Plataforma | Caminho padrão |
| --- | --- |
| Linux | `~/.local/bin/apollokairn` |
| macOS | `~/.local/bin/apollokairn` |
| Windows | `%LOCALAPPDATA%\Programs\ApolloKairn\bin\apollokairn.exe` |

Artefatos publicados em release:

| Plataforma | Artefato |
| --- | --- |
| Linux x64 | `apollokairn-linux-x64.tar.gz` |
| Linux arm64 | `apollokairn-linux-arm64.tar.gz` |
| macOS x64 | `apollokairn-macos-x64.tar.gz` |
| macOS arm64 | `apollokairn-macos-arm64.tar.gz` |
| Windows x64 | `apollokairn-windows-x64.zip` |

O release Linux x64 é gerado em um container Debian 11 com glibc 2.31 para
manter o binário compatível com distribuições mais antigas. Se o seu sistema
for mais antigo que isso ou usar uma libc diferente de glibc, instale pelo
código fonte.

## Instalar Uma Versão Específica

Linux e macOS:

```bash
curl -fsSL https://sinkz.github.io/apollokairn/install.sh | APOLLOKAIRN_VERSION=v0.1.3 sh
```

Windows PowerShell:

```powershell
$env:APOLLOKAIRN_VERSION = "v0.1.3"
irm https://sinkz.github.io/apollokairn/install.ps1 | iex
```

## Instalar Em Outro Diretório

Linux e macOS:

```bash
curl -fsSL https://sinkz.github.io/apollokairn/install.sh | APOLLOKAIRN_INSTALL_DIR="$HOME/bin" sh
```

Windows PowerShell:

```powershell
$env:APOLLOKAIRN_INSTALL_DIR = "$env:USERPROFILE\bin"
irm https://sinkz.github.io/apollokairn/install.ps1 | iex
```

## Solução De Problemas

### `apollokairn: command not found`

O binário foi instalado, mas o shell não encontrou o diretório de instalação.

Linux e macOS, para o shell atual:

```bash
export PATH="$HOME/.local/bin:$PATH"
apollokairn --version
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
$env:Path = "$env:LOCALAPPDATA\Programs\ApolloKairn\bin;$env:Path"
apollokairn --version
```

Se o instalador já adicionou o PATH do usuário, reinicie o terminal. Se não
adicionou, faça manualmente:

```powershell
$dir = "$env:LOCALAPPDATA\Programs\ApolloKairn\bin"
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
[Environment]::SetEnvironmentVariable("Path", "$userPath;$dir", "User")
```

### Download retorna 404

A release ou o artefato solicitado não existe. Confira a release mais recente:

```text
https://github.com/sinkz/apollokairn/releases
```

Se ainda não houver release com binários, instale pelo código fonte para
desenvolvimento:

```bash
git clone https://github.com/sinkz/apollokairn.git
cd apollokairn
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
curl -fsSL https://sinkz.github.io/apollokairn/install.sh | APOLLOKAIRN_INSTALL_DIR="$HOME/.local/bin" sh
```

Se o arquivo existe, mas não está executável:

```bash
chmod +x "$HOME/.local/bin/apollokairn"
```

### macOS diz que o binário não pode ser aberto

Enquanto as releases não forem assinadas e notarizadas, o macOS pode bloquear o
binário depois de um download pelo navegador. Se você confia na release do
GitHub e no checksum, remova o atributo de quarentena:

```bash
xattr -dr com.apple.quarantine "$HOME/.local/bin/apollokairn"
apollokairn --version
```

### Proxy corporativo ou inspeção TLS bloqueia o script

Baixe manualmente o artefato da sua plataforma e `checksums.txt` pelo GitHub
Releases, valide o hash SHA-256 e coloque `apollokairn` em um diretório no `PATH`.

Exemplo manual para Linux x64:

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

No macOS, troque `sha256sum -c -` por:

```bash
grep '  apollokairn-macos-arm64.tar.gz$' checksums.txt | shasum -a 256 -c -
```

## Desinstalar

Linux e macOS:

```bash
rm -f "$HOME/.local/bin/apollokairn" "$HOME/.local/bin/ak" "$HOME/.local/bin/cairn"
```

Windows PowerShell:

```powershell
Remove-Item "$env:LOCALAPPDATA\Programs\ApolloKairn\bin\apollokairn.exe"
Remove-Item "$env:LOCALAPPDATA\Programs\ApolloKairn\bin\ak.exe" -ErrorAction SilentlyContinue
Remove-Item "$env:LOCALAPPDATA\Programs\ApolloKairn\bin\cairn.exe" -ErrorAction SilentlyContinue
```

Isso não apaga o vault. Remova o diretório do vault apenas se você não quiser
mais manter as notas Markdown.
