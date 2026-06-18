# Cairn

Cairn é uma CLI local para um vault de conhecimento em Markdown. Ele ajuda
pessoas e agentes de IA a salvar notas reutilizáveis, buscá-las depois e
recuperar só o contexto necessário para a tarefa atual.

English version: [README.md](README.md)

## Para Que Serve

Cairn é útil para lembrar coisas como:

- como um bug recorrente foi diagnosticado e corrigido;
- como pedir acesso ou executar um processo de time;
- qual biblioteca, ferramenta ou decisão de arquitetura foi escolhida e por quê;
- procedimentos de suporte e workflows de produto;
- notas pessoais que um agente deve conseguir encontrar depois.

O vault é composto por arquivos Markdown com frontmatter. O índice SQLite é
local e pode ser reconstruído a qualquer momento.

## Requisitos

- Python 3.11 ou mais novo.
- Nenhuma dependência de runtime fora da biblioteca padrão do Python.
- Git é opcional, mas recomendado para versionar o vault.

## Instalar A Partir Do Código Fonte

Na raiz do repositório:

```bash
python -m pip install -e .
cairn --help
```

Se não quiser instalar o pacote, rode pelo checkout fonte:

```bash
export PYTHONPATH="$PWD/src"
python -m cairn --help
```

PowerShell:

```powershell
$env:PYTHONPATH = Join-Path (Resolve-Path .).Path "src"
python -m cairn --help
```

## Criar O Primeiro Vault

Escolha onde o vault vai ficar e inicialize:

```bash
cairn init --path CAMINHO_DO_VAULT --profile personal
cairn validate --path CAMINHO_DO_VAULT
cairn index --path CAMINHO_DO_VAULT --rebuild
cairn doctor --path CAMINHO_DO_VAULT
```

Perfis criam a estrutura inicial de pastas e schema:

| Perfil | Use para |
| --- | --- |
| `personal` | notas pessoais, aprendizado, workflows e referências |
| `engineering` | bugs, runbooks, incidentes, bibliotecas e decisões |
| `support` | triagem de suporte, procedimentos, FAQs e escalonamentos |
| `product` | requisitos, discovery, métricas e decisões de release |
| `custom` | um schema mínimo para adaptar |

## Adicionar E Buscar Notas

Crie uma nota:

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

`capture` cria um arquivo Markdown válido com uma seção `# Context`. Para notas
mais ricas, mantenha o corpo Markdown em um arquivo e passe direto para a CLI:

```bash
cairn capture --path CAMINHO_DO_VAULT \
  --title "Deploy 403 after token rotation" \
  --description "Corrige autorização antiga de CI após rotação de token." \
  --type Runbook \
  --tag bug \
  --tag deploy \
  --body-file CAMINHO_DO_CORPO_DA_NOTA.md
```

Atualize o índice:

```bash
cairn index --path CAMINHO_DO_VAULT
```

Busque antes de abrir arquivos completos:

```bash
cairn search "deploy 403 token" --path CAMINHO_DO_VAULT --limit 3
cairn search "deploy token rotation kubernetes secret" --path CAMINHO_DO_VAULT --ranker rrf
```

Recupere um pacote de contexto dentro de um orçamento para o agente:

```bash
cairn retrieve "deploy 403 token" --path CAMINHO_DO_VAULT --budget 800
cairn retrieve "deploy 403 token" --path CAMINHO_DO_VAULT --mode passages --budget 400
cairn retrieve "deploy token rotation kubernetes secret" --path CAMINHO_DO_VAULT --ranker auto --budget 800
```

Procure uma nota existente antes de criar outra:

```bash
cairn similar "deploy forbidden token" --path CAMINHO_DO_VAULT --limit 5
```

Se `similar` encontrar o mesmo assunto, atualize:

```bash
cairn update knowledge/deploy-403-after-token-rotation.md \
  --path CAMINHO_DO_VAULT \
  --append "Adicionar o passo de verificação usado no incidente mais recente."
```

Para atualizações maiores, use `--append-file CAMINHO_DO_TEXTO.md` ou envie o
conteúdo por pipe com `--append-stdin`.

## Resumo Dos Comandos

| Comando | Função |
| --- | --- |
| `cairn init` | cria um vault |
| `cairn validate` | verifica frontmatter, schema e valores comuns com aparência de segredo |
| `cairn index` | cria ou atualiza o índice local |
| `cairn doctor` | verifica saúde do vault e do índice |
| `cairn capture` / `cairn add` | cria uma nota |
| `cairn similar` | encontra notas existentes antes de criar duplicata |
| `cairn search` | retorna snippets e paths ranqueados |
| `cairn retrieve` | retorna contexto dentro de um orçamento de tokens |
| `cairn show` | abre um documento completo, seção, snippet ou intervalo de linhas |
| `cairn update` | adiciona informação reutilizável a uma nota existente |
| `cairn setup-agent` | cria instruções específicas como `CODEX.md` |
| `cairn refresh-guides` | atualiza guias de agente gerados |
| `cairn stats` | mostra contagens e tamanho aproximado em tokens |
| `cairn export` / `cairn import` | move um vault como arquivo zip |

## Testar O Vault De Exemplo

```bash
cairn validate --path examples/engineering-vault
cairn index --path examples/engineering-vault --rebuild
cairn search "deploy 403 token" --path examples/engineering-vault --limit 3
cairn retrieve "hotfix release rollback" --path examples/engineering-vault --mode passages --budget 400
```

Veja [examples/README.md](examples/README.md) para mais walkthroughs.

## Documentação

- [Guia de uso](docs/guides/usage.pt-BR.md)
- [Usage guide in English](docs/guides/usage.md)
- [Vaults de exemplo](examples/README.md)
- [Roadmap](ROADMAP.md)
- [Changelog](CHANGELOG.md)

## Desenvolvimento

Rode a suíte de testes:

```bash
python -m unittest discover -v
```

Rode o benchmark determinístico de busca:

```bash
python bench/run_eval.py --quiet --compare-golden bench/golden.json
```

O benchmark verifica qualidade de ranking, prefixos golden, orçamentos de tokens
e redução de contexto em passagens contra documentos completos.

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
