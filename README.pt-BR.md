<div align="center">
  <h1>ApolloKairn</h1>
  <p><strong>Conhecimento em Markdown para fluxos de busca, recuperação e escrita.</strong></p>
  <p>
    <a href="https://sinkz.github.io/apollokairn/">Site</a> ·
    <a href="docs/guides/quick-install.pt-BR.md">Instalação rápida</a> ·
    <a href="https://sinkz.github.io/apollokairn/learn.html">Como funciona</a> ·
    <a href="docs/guides/usage.pt-BR.md">Guia de uso</a> ·
    <a href="examples/README.md">Exemplos</a> ·
    <a href="README.md">English</a>
  </p>
  <p>
    <img alt="Python 3.11+" src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white">
    <img alt="Dependências de runtime: zero" src="https://img.shields.io/badge/dependencias_runtime-0-2f6f4e">
    <img alt="Testes de regressão: 215" src="https://img.shields.io/badge/testes-215-3b6ea8">
    <img alt="Recall at 3: 1.00" src="https://img.shields.io/badge/Recall%403-1.00-2f6f4e">
    <img alt="Redução de contexto: 91.83%" src="https://img.shields.io/badge/reducao_contexto-91.83%25-8a5a44">
    <img alt="Acurácia de decisão de escrita: 100%" src="https://img.shields.io/badge/escrita_decisoes-100%25-285da8">
    <img alt="Licença: MIT" src="https://img.shields.io/badge/licenca-MIT-15130f">
  </p>
</div>

## O Que É O ApolloKairn

ApolloKairn é uma CLI local para um vault de conhecimento em Markdown. Ele ajuda
pessoas e agentes a guardar notas reutilizáveis, buscá-las depois, recuperar só
o contexto necessário para uma tarefa e registrar novos aprendizados no vault.

A fonte da verdade é Markdown puro com frontmatter. A busca usa um índice SQLite
local e reconstruível. ApolloKairn entrega mais valor dentro de fluxos com agentes,
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
| nDCG@3 | `0.9941` | Qualidade de ranking contra rótulos determinísticos de relevância. |
| Redução de contexto | `91.83%` | Recuperação por passagens retorna muito menos texto que abrir documentos completos. |
| Redução em comparativos | `53.73%` | Redução medida nas rodadas comparativas configuradas. |
| Acurácia de decisão de escrita | `100%` | Decisões corretas de criar, atualizar, no-op e conflito no conjunto de fixtures. |
| Prevenção de duplicatas | `100%` | Notas reutilizáveis existentes são atualizadas ou preservadas em vez de duplicadas. |
| Testes de regressão | `215` | Testes unitários e de workflow rodados antes da publicação atual. |

Os dados do benchmark também são publicados no site por
[`docs/data/benchmarks.json`](docs/data/benchmarks.json).

```bash
python bench/run_eval.py --quiet --compare-golden bench/golden.json
python bench/run_writeback_eval.py --quiet --compare-golden bench/writeback/golden.json
python bench/publish_metrics.py --output docs/data/benchmarks.json --tests 215
```

## Instalação Rápida

Binários prontos do GitHub Releases não exigem Python instalado.

> ApolloKairn se chamava Cairn. O comando `cairn` continua disponível como alias
> de compatibilidade por uma versão, mas a documentação nova usa `apollokairn`.

Linux e macOS:

```bash
curl -fsSL https://sinkz.github.io/apollokairn/install.sh | sh
```

Windows PowerShell:

```powershell
irm https://sinkz.github.io/apollokairn/install.ps1 | iex
```

Depois valide:

```powershell
apollokairn --version
apollokairn --help
```

Veja [Instalação rápida](docs/guides/quick-install.pt-BR.md) para caminhos
customizados, versão fixa, configuração de PATH, problemas de checksum e
fallback manual.

## Criar Um Vault

```bash
apollokairn init --path CAMINHO_DO_VAULT --profile engineering
apollokairn validate --path CAMINHO_DO_VAULT
apollokairn index --path CAMINHO_DO_VAULT --rebuild
apollokairn doctor --path CAMINHO_DO_VAULT
```

Perfis criam a estrutura inicial de pastas e schema:

| Perfil | Use para |
| --- | --- |
| `personal` | Notas pessoais, aprendizado, workflows e referências |
| `engineering` | Bugs, runbooks, incidentes, bibliotecas e decisões |
| `support` | Triagem de suporte, procedimentos, FAQs e escalonamentos |
| `product` | Requisitos, discovery, métricas e decisões de release |
| `custom` | Um schema mínimo para adaptar |

## Registrar Vaults

Registrar vaults permite trabalhar de qualquer repositório sem lembrar caminhos
longos:

```bash
apollokairn vault add CAMINHO_DO_VAULT --name pessoal --set-active
apollokairn vault list
apollokairn vault current
apollokairn vault use pessoal
```

Depois os comandos podem usar o vault ativo:

```bash
apollokairn search "deploy 403"
apollokairn retrieve "pedido de acesso" --budget 500
```

Agentes e scripts devem preferir nomes explícitos depois da descoberta:

```bash
apollokairn vault list --json
apollokairn search "deploy 403" --vault pessoal --json
```

A ordem de resolução é `--path`, depois `--vault`, depois o vault ativo
registrado e, por fim, o diretório atual para manter compatibilidade.

## Skill Opcional Para Agentes

Instale a skill compartilhada quando quiser que Codex ou Hermes saibam usar o
fluxo da CLI a partir de qualquer repositório:

```bash
apollokairn agent install codex
apollokairn agent install hermes
apollokairn agent doctor --json
```

O instalador copia uma skill pequena chamada `apollokairn-vault` por padrão e
pode ser rodado novamente. Use `--mode symlink` apenas em desenvolvimento com o
checkout do código. Guias locais dentro do vault continuam disponíveis com
`apollokairn setup-agent`.

## Instalar Pelo Código Fonte

A instalação pelo código fonte é mais útil para desenvolvimento ou quando ainda
não houver binários publicados em release:

```bash
git clone https://github.com/sinkz/apollokairn.git
cd apollokairn
python -m pip install -e .
apollokairn --help
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
apollokairn capture --path CAMINHO_DO_VAULT \
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
apollokairn capture --path CAMINHO_DO_VAULT \
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
apollokairn index --path CAMINHO_DO_VAULT
apollokairn search "deploy 403 token" --path CAMINHO_DO_VAULT --limit 3
apollokairn search "deploy token rotation kubernetes secret" --path CAMINHO_DO_VAULT --ranker rrf
apollokairn search "deploy 403 token" --path CAMINHO_DO_VAULT --json --explain
```

Se seu time usa sinônimos estáveis como `k8s` e `kubernetes`, mantenha isso em
`glossary.md` para a busca expandir vocabulário aprovado de forma
determinística:

```bash
apollokairn vocab add-term Kubernetes --alias k8s --alias kube --path CAMINHO_DO_VAULT
apollokairn vocab validate --path CAMINHO_DO_VAULT
apollokairn vocab suggest "kubernetes rollback" --path CAMINHO_DO_VAULT --json
```

### 3. Recuperar contexto compacto

```bash
apollokairn retrieve "deploy 403 token" --path CAMINHO_DO_VAULT --budget 800
apollokairn retrieve "deploy 403 token" --path CAMINHO_DO_VAULT --mode passages --budget 400
apollokairn retrieve "deploy token rotation kubernetes secret" --path CAMINHO_DO_VAULT --ranker auto --budget 800
apollokairn retrieve "deploy 403 token" --path CAMINHO_DO_VAULT --mode passages --budget 400 --json
apollokairn retrieve "deploy 403 token" --path CAMINHO_DO_VAULT --mode passages --budget 400 --json --explain
```

### 4. Atualizar em vez de duplicar

```bash
apollokairn similar "deploy forbidden token" --path CAMINHO_DO_VAULT --limit 5

apollokairn update knowledge/deploy-403-after-token-rotation.md \
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
| `apollokairn init` | Cria um vault |
| `apollokairn vault` | Registra, lista, inspeciona e troca vaults nomeados |
| `apollokairn validate` | Verifica frontmatter, schema e valores comuns com aparência de segredo |
| `apollokairn index` | Cria ou atualiza o índice local |
| `apollokairn doctor` | Verifica saúde do vault e do índice |
| `apollokairn capture` / `apollokairn add` | Cria uma nota |
| `apollokairn similar` | Encontra notas existentes antes de criar duplicata |
| `apollokairn search` | Retorna snippets e paths ranqueados |
| `apollokairn retrieve` | Retorna contexto dentro de um orçamento de tokens |
| `apollokairn show` | Abre documento completo, seção, snippet ou intervalo de linhas |
| `apollokairn update` | Adiciona informação reutilizável a uma nota existente |
| `apollokairn vocab` | Gerencia termos e aliases determinísticos do glossário |
| `apollokairn agent` | Instala ou verifica skills opcionais para Codex/Hermes |
| `apollokairn setup-agent` | Cria instruções específicas como `CODEX.md`, `HERMES.md` ou instruções do Copilot |
| `apollokairn refresh-guides` | Atualiza guias de agente gerados |
| `apollokairn stats` | Mostra contagens e tamanho aproximado em tokens |
| `apollokairn usage` | Ativa métricas locais de uso e gera relatório do vault |
| `apollokairn export` / `apollokairn import` | Move um vault como arquivo zip |

Todos os comandos operacionais suportam `--json` para fluxos com agentes; veja
o [guia de uso](docs/guides/usage.pt-BR.md) para o contrato completo.

## Vault De Exemplo

```bash
apollokairn validate --path examples/engineering-vault
apollokairn index --path examples/engineering-vault --rebuild
apollokairn search "deploy 403 token" --path examples/engineering-vault --limit 3
apollokairn retrieve "hotfix release rollback" --path examples/engineering-vault --mode passages --budget 400
```

Veja [examples/README.md](examples/README.md) para mais walkthroughs.

## Documentação

| Página | Descrição |
| --- | --- |
| [Site](https://sinkz.github.io/apollokairn/) | Overview público e cards de benchmark |
| [Como funciona](https://sinkz.github.io/apollokairn/learn.html) | Explicação conceitual e técnica |
| [Instalação rápida](docs/guides/quick-install.pt-BR.md) | Binários, PATH e solução de problemas |
| [Guia de uso](docs/guides/usage.pt-BR.md) | Guia completo dos comandos |
| [Assets agentic](agentic/README.md) | Fonte da skill compartilhada para Codex/Hermes |
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
python bench/publish_metrics.py --output docs/data/benchmarks.json --tests 215
```

Os benchmarks verificam qualidade de ranking, prefixos golden, orçamentos de
tokens, redução de contexto em passagens contra documentos completos, decisões
de atualizar vs criar, idempotência de no-op, prevenção de duplicatas e detecção
de conflito por escrita obsoleta.
`bench/publish_metrics.py` atualiza o JSON público do GitHub Pages, deduplica a
linha mais recente do histórico por data e rótulo e adiciona deltas das métricas
contra a rodada anterior.

## Referência OKF

ApolloKairn segue o formato útil do Open Knowledge Format: um conceito por arquivo
Markdown, metadados em frontmatter, `index.md` e `log.md`. ApolloKairn não exige
Google Cloud, Gemini, BigQuery ou a implementação de referência do OKF.

- [Anúncio do Google Cloud sobre OKF](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing)
- [GoogleCloudPlatform/knowledge-catalog](https://github.com/GoogleCloudPlatform/knowledge-catalog)
- [Diretório OKF](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf)
- [Especificação OKF v0.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)

## Licença

MIT. Veja [LICENSE](LICENSE).
