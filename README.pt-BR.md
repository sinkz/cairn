<div align="center">
  <h1>Cairn</h1>
  <p><strong>Conhecimento em Markdown para fluxos de busca, recuperação e escrita.</strong></p>
  <p>
    <a href="https://sinkz.github.io/cairn/">Site</a> ·
    <a href="docs/guides/quick-install.pt-BR.md">Instalação rápida</a> ·
    <a href="https://sinkz.github.io/cairn/learn.html">Como funciona</a> ·
    <a href="docs/guides/usage.pt-BR.md">Guia de uso</a> ·
    <a href="examples/README.md">Exemplos</a> ·
    <a href="README.md">English</a>
  </p>
  <p>
    <img alt="Python 3.11+" src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white">
    <img alt="Dependências de runtime: zero" src="https://img.shields.io/badge/dependencias_runtime-0-2f6f4e">
    <img alt="Testes de regressão: 164" src="https://img.shields.io/badge/testes-164-3b6ea8">
    <img alt="Recall at 3: 1.00" src="https://img.shields.io/badge/Recall%403-1.00-2f6f4e">
    <img alt="Redução de contexto: 92.15%" src="https://img.shields.io/badge/reducao_contexto-92.15%25-8a5a44">
    <img alt="Acurácia de decisão de escrita: 100%" src="https://img.shields.io/badge/escrita_decisoes-100%25-285da8">
    <img alt="Licença: MIT" src="https://img.shields.io/badge/licenca-MIT-15130f">
  </p>
</div>

## O Que É O Cairn

Cairn é uma CLI local para um vault de conhecimento em Markdown. Ele ajuda
pessoas e agentes a guardar notas reutilizáveis, buscá-las depois, recuperar só
o contexto necessário para uma tarefa e registrar novos aprendizados no vault.

A fonte da verdade é Markdown puro com frontmatter. A busca usa um índice SQLite
local e reconstruível. Cairn entrega mais valor dentro de fluxos com agentes,
mas não depende de um produto específico.

| Área | O que você ganha |
| --- | --- |
| Notas pessoais | Bugs, decisões, referências, aprendizados e processos recorrentes |
| Times de engenharia | Runbooks, incidentes, detalhes de bibliotecas e decisões de arquitetura |
| Suporte e produto | Acessos, escalonamentos, regras de produto e procedimentos de atendimento |
| Fluxos com agentes | Buscar primeiro, recuperar contexto compacto, resolver e atualizar ou criar notas |

## Snapshot Atual Do Benchmark

Os benchmarks determinísticos rodam localmente sem chamadas a modelos. Eles
medem qualidade de recuperação, orçamento de tokens, redução de contexto em
passagens contra documentos completos e decisões de escrita em fluxos de
atualizar vs criar.

| Métrica | Atual | Significado |
| --- | ---: | --- |
| Recall@3 | `1.00` | Notas esperadas aparecem nos três primeiros resultados. |
| MRR@3 | `1.00` | Resultados relevantes aparecem primeiro no conjunto atual. |
| nDCG@3 | `0.9934` | Qualidade de ranking contra rótulos determinísticos de relevância. |
| Redução de contexto | `92.15%` | Recuperação por passagens retorna muito menos texto que abrir documentos completos. |
| Redução em comparativos | `53.73%` | Redução medida nas rodadas comparativas configuradas. |
| Acurácia de decisão de escrita | `100%` | Decisões corretas de criar, atualizar, no-op e conflito no conjunto de fixtures. |
| Prevenção de duplicatas | `100%` | Notas reutilizáveis existentes são atualizadas ou preservadas em vez de duplicadas. |
| Testes de regressão | `164` | Testes unitários e de workflow rodados antes da publicação atual. |

Os dados do benchmark também são publicados no site por
[`docs/data/benchmarks.json`](docs/data/benchmarks.json).

```bash
python bench/run_eval.py --quiet --compare-golden bench/golden.json
python bench/run_writeback_eval.py --quiet --compare-golden bench/writeback/golden.json
```

## Instalação Rápida

Binários prontos do GitHub Releases não exigem Python instalado.

Linux e macOS:

```bash
curl -fsSL https://sinkz.github.io/cairn/install.sh | sh
```

Windows PowerShell:

```powershell
irm https://sinkz.github.io/cairn/install.ps1 | iex
```

Depois valide:

```powershell
cairn --version
cairn --help
```

Veja [Instalação rápida](docs/guides/quick-install.pt-BR.md) para caminhos
customizados, versão fixa, configuração de PATH, problemas de checksum e
fallback manual.

## Criar Um Vault

```bash
cairn init --path CAMINHO_DO_VAULT --profile engineering
cairn validate --path CAMINHO_DO_VAULT
cairn index --path CAMINHO_DO_VAULT --rebuild
cairn doctor --path CAMINHO_DO_VAULT
```

Perfis criam a estrutura inicial de pastas e schema:

| Perfil | Use para |
| --- | --- |
| `personal` | Notas pessoais, aprendizado, workflows e referências |
| `engineering` | Bugs, runbooks, incidentes, bibliotecas e decisões |
| `support` | Triagem de suporte, procedimentos, FAQs e escalonamentos |
| `product` | Requisitos, discovery, métricas e decisões de release |
| `custom` | Um schema mínimo para adaptar |

## Instalar Pelo Código Fonte

A instalação pelo código fonte é mais útil para desenvolvimento ou quando ainda
não houver binários publicados em release:

```bash
git clone https://github.com/sinkz/cairn.git
cd cairn
python -m pip install -e .
cairn --help
```

Rodar sem instalar:

```bash
export PYTHONPATH="$PWD/src"
python -m cairn --help
```

PowerShell:

```powershell
$env:PYTHONPATH = Join-Path (Resolve-Path .).Path "src"
python -m cairn --help
```

## Fluxo Diário

### 1. Capturar uma nota

```bash
cairn capture --path CAMINHO_DO_VAULT \
  --title "Deploy 403 after token rotation" \
  --description "Corrige autorização antiga de CI após rotação de token." \
  --type Runbook \
  --tag bug \
  --tag deploy \
  --system ci \
  --signal "HTTP 403" \
  --body "Deploy falhou depois de uma rotação de token. Atualize o segredo de CI e rode novamente o job que falhou."
```

Para notas maiores, mantenha o corpo em um arquivo Markdown:

```bash
cairn capture --path CAMINHO_DO_VAULT \
  --title "Deploy 403 after token rotation" \
  --description "Corrige autorização antiga de CI após rotação de token." \
  --type Runbook \
  --tag bug \
  --tag deploy \
  --body-file CAMINHO_DO_CORPO_DA_NOTA.md
```

`capture` e `add` validam o schema alvo e escaneiam o conteúdo novo por valores
com aparência de segredo antes de escrever o arquivo.

### 2. Buscar antes de abrir arquivos

```bash
cairn index --path CAMINHO_DO_VAULT
cairn search "deploy 403 token" --path CAMINHO_DO_VAULT --limit 3
cairn search "deploy token rotation kubernetes secret" --path CAMINHO_DO_VAULT --ranker rrf
cairn search "deploy 403 token" --path CAMINHO_DO_VAULT --json --explain
```

Se seu time usa sinônimos estáveis como `k8s` e `kubernetes`, mantenha isso em
`glossary.md` para a busca estrita expandir misses exatos de forma
determinística:

```bash
cairn vocab add-term Kubernetes --alias k8s --alias kube --path CAMINHO_DO_VAULT
cairn vocab validate --path CAMINHO_DO_VAULT
cairn vocab suggest "kubernetes rollback" --path CAMINHO_DO_VAULT --json
```

### 3. Recuperar contexto compacto

```bash
cairn retrieve "deploy 403 token" --path CAMINHO_DO_VAULT --budget 800
cairn retrieve "deploy 403 token" --path CAMINHO_DO_VAULT --mode passages --budget 400
cairn retrieve "deploy token rotation kubernetes secret" --path CAMINHO_DO_VAULT --ranker auto --budget 800
cairn retrieve "deploy 403 token" --path CAMINHO_DO_VAULT --mode passages --budget 400 --json
cairn retrieve "deploy 403 token" --path CAMINHO_DO_VAULT --mode passages --budget 400 --json --explain
```

### 4. Atualizar em vez de duplicar

```bash
cairn similar "deploy forbidden token" --path CAMINHO_DO_VAULT --limit 5

cairn update knowledge/deploy-403-after-token-rotation.md \
  --path CAMINHO_DO_VAULT \
  --append "Adicionar o passo de verificação usado no incidente mais recente."
```

Para atualizações maiores, use `--append-file CAMINHO_DO_TEXTO.md` ou envie o
conteúdo por pipe com `--append-stdin`.
Agentes podem adicionar `--json`, prever escritas com `--dry-run` e passar
`--expect-sha256 SHA256_ATUAL` para evitar atualizar um arquivo que mudou desde
a última inspeção. O conteúdo novo anexado é escaneado por valores com aparência
de segredo antes da escrita.

## Comandos

| Comando | Função |
| --- | --- |
| `cairn init` | Cria um vault |
| `cairn validate` | Verifica frontmatter, schema e valores comuns com aparência de segredo |
| `cairn index` | Cria ou atualiza o índice local |
| `cairn doctor` | Verifica saúde do vault e do índice |
| `cairn capture` / `cairn add` | Cria uma nota |
| `cairn similar` | Encontra notas existentes antes de criar duplicata |
| `cairn search` | Retorna snippets e paths ranqueados |
| `cairn retrieve` | Retorna contexto dentro de um orçamento de tokens |
| `cairn show` | Abre documento completo, seção, snippet ou intervalo de linhas |
| `cairn update` | Adiciona informação reutilizável a uma nota existente |
| `cairn vocab` | Gerencia termos e aliases determinísticos do glossário |
| `cairn setup-agent` | Cria instruções específicas como `CODEX.md`, `HERMES.md` ou instruções do Copilot |
| `cairn refresh-guides` | Atualiza guias de agente gerados |
| `cairn stats` | Mostra contagens e tamanho aproximado em tokens |
| `cairn export` / `cairn import` | Move um vault como arquivo zip |

Todos os comandos operacionais suportam `--json` para fluxos com agentes; veja
o [guia de uso](docs/guides/usage.pt-BR.md) para o contrato completo.

## Vault De Exemplo

```bash
cairn validate --path examples/engineering-vault
cairn index --path examples/engineering-vault --rebuild
cairn search "deploy 403 token" --path examples/engineering-vault --limit 3
cairn retrieve "hotfix release rollback" --path examples/engineering-vault --mode passages --budget 400
```

Veja [examples/README.md](examples/README.md) para mais walkthroughs.

## Documentação

| Página | Descrição |
| --- | --- |
| [Site](https://sinkz.github.io/cairn/) | Overview público e cards de benchmark |
| [Como funciona](https://sinkz.github.io/cairn/learn.html) | Explicação conceitual e técnica |
| [Instalação rápida](docs/guides/quick-install.pt-BR.md) | Binários, PATH e solução de problemas |
| [Guia de uso](docs/guides/usage.pt-BR.md) | Guia completo dos comandos |
| [Adapters para agentes](docs/guides/adapters.pt-BR.md) | Guias gerados para Codex, Claude, OpenCode, Hermes, Copilot e agentes genéricos |
| [Vaults de exemplo](examples/README.md) | Exemplos reproduzíveis |
| [Roadmap](ROADMAP.md) | Fases atuais de implementação |
| [Changelog](CHANGELOG.md) | Mudanças publicadas |
| [Instruções para agentes](AGENTS.md) | Regras do repositório para agentes de IA |
| [README em inglês](README.md) | Documentação em inglês |

## Desenvolvimento

Rode a suíte de testes:

```bash
python -m unittest discover -v
```

Rode os benchmarks determinísticos:

```bash
python bench/run_eval.py --quiet --compare-golden bench/golden.json
python bench/run_writeback_eval.py --quiet --compare-golden bench/writeback/golden.json
```

Os benchmarks verificam qualidade de ranking, prefixos golden, orçamentos de
tokens, redução de contexto em passagens contra documentos completos, decisões
de atualizar vs criar, idempotência de no-op, prevenção de duplicatas e detecção
de conflito por escrita obsoleta.

## Referência OKF

Cairn segue o formato útil do Open Knowledge Format: um conceito por arquivo
Markdown, metadados em frontmatter, `index.md` e `log.md`. Cairn não exige
Google Cloud, Gemini, BigQuery ou a implementação de referência do OKF.

- [Anúncio do Google Cloud sobre OKF](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing)
- [GoogleCloudPlatform/knowledge-catalog](https://github.com/GoogleCloudPlatform/knowledge-catalog)
- [Diretório OKF](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf)
- [Especificação OKF v0.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)

## Licença

MIT. Veja [LICENSE](LICENSE).
