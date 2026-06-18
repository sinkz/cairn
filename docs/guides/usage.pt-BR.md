# Guia de Uso do Cairn

Este guia explica para que o Cairn serve, como configurar um vault e quando usar
cada comando.

## Para Que Serve

Cairn é um vault local em Markdown otimizado para humanos e agentes de IA. Ele
ajuda a salvar conhecimento reutilizável depois de resolver problemas, tomar
decisões, documentar processos ou aprender padrões recorrentes.

Casos de uso comuns:

- notas de debug e correções de bugs recorrentes;
- runbooks operacionais;
- processos de escalonamento de suporte;
- decisões de produto ou arquitetura;
- referências de bibliotecas, acessos e processos;
- notas pessoais que um agente deve conseguir encontrar depois.

A ideia central é simples: agentes devem buscar primeiro, abrir só os documentos
mais relevantes e registrar conhecimento reutilizável depois que o trabalho foi
resolvido.

## Instalação

Para desenvolvimento local:

```bash
python -m pip install -e .
```

Em um checkout fonte sem instalar:

```bash
export PYTHONPATH="$PWD/src"
python -m cairn --help
```

PowerShell:

```powershell
$env:PYTHONPATH = Join-Path (Resolve-Path .).Path "src"
python -m cairn --help
```

## Criando Um Vault

```bash
cairn init --path ~/brain --profile personal
```

Perfis definem pastas, tipos e tags iniciais.

| Perfil | Uso |
| --- | --- |
| `personal` | Notas pessoais, aprendizado, workflows e referências |
| `engineering` | Bugs, runbooks, incidentes, bibliotecas e decisões |
| `product` | Requisitos, discovery, métricas e decisões de release |
| `support` | Triagem de suporte, procedimentos, FAQs e escalonamentos |
| `custom` | Ponto de partida mínimo para seu próprio schema |

O comando cria:

| Caminho | Função |
| --- | --- |
| `AGENTS.md` | Instruções para agentes que usam o vault |
| `SCHEMA.md` | Tipos e tags permitidos |
| `index.md` | Entrada humana do vault |
| `log.md` | Registro cronológico de atualizações |
| `.cairn/config.json` | Configurações do Cairn |
| `_templates/concept.md` | Template inicial para novas notas |
| pastas de domínio | `knowledge`, `processes`, `decisions`, `references`, `notes`, `inbox` |

## Configuração

Cairn guarda configurações locais em `.cairn/config.json`.

Exemplo:

```json
{
  "exclude": ["inbox"],
  "generated_guides": ["AGENTS.md"],
  "profile": "engineering",
  "search_limit": 3
}
```

Campos importantes:

| Campo | Função |
| --- | --- |
| `profile` | Perfil usado na inicialização do vault |
| `search_limit` | Limite padrão sugerido para agentes |
| `exclude` | Pastas ou padrões ignorados pela validação e indexação |
| `generated_guides` | Arquivos de guia de agente gerenciados pelo Cairn |

Use `exclude` para áreas de rascunho, inbox privada, arquivos gerados e qualquer
conteúdo que não deve ser indexado.

## Formato Dos Documentos

Cada conceito reutilizável deve ser um arquivo Markdown com frontmatter:

```markdown
---
type: Runbook
title: Deploy 403 after token rotation
description: Fixes deploy failures caused by stale workspace access tokens.
tags: [bug, deploy]
timestamp: 2026-06-17T12:00:00-03:00
aliases: [deploy forbidden, token 403]
systems: [ci, deployment]
signals: [http 403, forbidden, workspace access]
---

# Context

O que aconteceu e quando isso se aplica.

# Diagnosis

Como reconhecer o problema.

# Resolution

Como resolver.
```

Campos obrigatórios:

- `type`
- `title`
- `description`
- `tags`
- `timestamp`

Campos opcionais úteis:

- `aliases`: nomes alternativos que pessoas ou agentes podem buscar;
- `systems`: sistemas, produtos, repositórios, serviços ou domínios afetados;
- `signals`: sintomas, erros, logs, status codes ou frases de gatilho.

Nunca salve segredos, tokens, senhas, chaves privadas ou credenciais.

## Referência de Comandos

### `cairn init`

Cria um novo vault.

```bash
cairn init --path ~/brain --profile engineering
```

Use uma vez por vault. Rodar novamente é seguro; arquivos existentes são
preservados.

### `cairn validate`

Verifica se as notas Markdown seguem o `SCHEMA.md` e as regras de frontmatter.
Ele também bloqueia valores comuns com aparência de segredo, como access keys,
tokens de provedores e blocos de chave privada, sem imprimir o valor detectado.

```bash
cairn validate --path ~/brain
```

Use antes de indexar, antes de commitar um vault ou quando um agente criou ou
editou notas.

### `cairn add` e `cairn capture`

Cria uma nota reutilizável com frontmatter válido do Cairn.

```bash
cairn add --path ~/brain \
  --title "Deploy 403 after token rotation" \
  --description "Corrige autorização antiga de CI após rotação de token." \
  --type Runbook \
  --tag bug \
  --tag deploy \
  --system ci \
  --signal "HTTP 403" \
  --body "# Context\n\nDeploy falhou depois da rotação do token."
```

`capture` é um alias com o mesmo comportamento. Use depois que uma tarefa foi
resolvida e o conhecimento provavelmente será útil de novo.

### `cairn update`

Adiciona texto a uma nota existente se o mesmo texto ainda não estiver lá.

```bash
cairn update knowledge/deploy-403.md --path ~/brain --append "Adicionar o novo passo de verificação."
```

Use quando `cairn similar` encontrar uma nota existente que deve ser expandida
em vez de duplicada.

### `cairn index`

Cria ou atualiza o índice local SQLite FTS.

```bash
cairn index --path ~/brain --rebuild
cairn index --path ~/brain
```

Use `--rebuild` na primeira configuração ou se o índice estiver corrompido. Sem
`--rebuild`, a indexação é incremental: arquivos alterados são atualizados,
arquivos removidos saem do índice e arquivos iguais são ignorados.

### `cairn doctor`

Verifica a saúde do vault e se o índice está atualizado.

```bash
cairn doctor --path ~/brain
```

Use quando a busca parecer estranha, depois de edições manuais ou antes de uma
sessão com agente. Ele aponta erros de validação, índice ausente, índice inválido
ou índice desatualizado.

### `cairn search`

Busca no vault e retorna resultados compactos com snippets.

```bash
cairn search "deploy 403 workspace access" --path ~/brain --limit 3
cairn search "deploy token rotation kubernetes secret" --path ~/brain --ranker rrf
```

Use antes de abrir documentos completos. Este é o principal comando para
economizar tokens. O ranker padrão `bm25` é estrito e estável. Use o
experimental `--ranker rrf` quando a busca mistura sinais corretos com termos
extras ou variantes lexicais.

Filtros:

```bash
cairn search "retry timeout" --path ~/brain --type Decision
cairn search "deploy" --path ~/brain --tag deploy
cairn search "timeout" --path ~/brain --system checkout
```

Saída JSON para agentes:

```bash
cairn search "cache stampede" --path ~/brain --json
```

### `cairn retrieve`

Monta um pacote de contexto para LLM dentro de um orçamento aproximado de tokens.

```bash
cairn retrieve "deploy 403" --path ~/brain --limit 3 --budget 800
cairn retrieve "deploy 403" --path ~/brain --mode passages --budget 500
cairn retrieve "deploy token rotation kubernetes secret" --path ~/brain --ranker rrf --budget 800
cairn retrieve "reconnecting cache workers" --path ~/brain --mode passages --ranker rrf --budget 500
```

Use quando um agente precisa de contexto útil imediatamente sem rodar `search` e
`show` manualmente. O orçamento usa uma aproximação simples de 4 caracteres por
token. A recuperação redige valores comuns com aparência de segredo antes de
imprimir o pacote de contexto.

Use `--mode passages` quando o agente precisa das menores seções úteis em vez de
documentos completos. A saída de passagem inclui path, heading e intervalo de
linhas para o agente reabrir o contexto exato se precisar.

Use `--ranker rrf` com documentos ou passagens quando a busca estrita padrão
não retorna nada porque a query mistura sinais corretos com termos extras ou
variantes lexicais seguras. RRF continua opt-in; o caminho padrão `bm25` segue
estrito.

Filtros funcionam como em `search`:

```bash
cairn retrieve "retry timeout" --path ~/brain --type Decision --system checkout --budget 600
```

### `cairn show`

Abre um documento do vault.

```bash
cairn show knowledge/deploy-403.md --path ~/brain
```

Use leituras parciais para reduzir contexto:

```bash
cairn show knowledge/deploy-403.md --path ~/brain --section Diagnosis
cairn show knowledge/deploy-403.md --path ~/brain --snippet "workspace access" --context 2
cairn show knowledge/deploy-403.md --path ~/brain --lines 20:40
```

Leituras parciais são úteis depois que `search` encontrou o documento certo, mas
o agente só precisa de uma seção ou de algumas linhas próximas.

### `cairn similar`

Encontra notas existentes antes de criar uma duplicata. Ele combina busca lexical
indexada com um scan local por fingerprint leve, então ainda consegue encontrar
quase duplicatas quando a nova nota tem termos extras.

```bash
cairn similar "deploy forbidden token" --path ~/brain --limit 5
```

Use antes de adicionar uma nova nota. Se o resultado for próximo o bastante,
atualize a nota existente em vez de criar outra.

Saída JSON para agentes:

```bash
cairn similar "deploy forbidden token" --path ~/brain --json
```

### `cairn stats`

Mostra tamanho do vault, distribuição por tipos/tags e contagem aproximada de
tokens.

```bash
cairn stats --path ~/brain
cairn stats --path ~/brain --json
```

Use para entender se o vault está crescendo em uma forma saudável.

### `cairn export` e `cairn import`

Exporta ou importa um arquivo zip do vault.

```bash
cairn export --path ~/brain --output cairn-vault.zip
cairn import cairn-vault.zip --path ~/restored-brain
```

Arquivos de índice gerados não entram no export. Rode `cairn index` depois de
importar. O export é abortado quando valores comuns com aparência de segredo são
detectados em arquivos que entrariam no arquivo zip.

### `cairn setup-agent` e `cairn refresh-guides`

Cria ou atualiza instruções específicas para agentes dentro do vault.

```bash
cairn setup-agent codex --path ~/brain
cairn setup-agent claude --path ~/brain
cairn setup-agent opencode --path ~/brain
cairn refresh-guides --path ~/brain
```

Use quando o mesmo vault deve ser consumido por diferentes harnesses agenticos.
Cairn mantém Markdown como fonte da verdade; plugins podem vir depois como
adaptadores finos.

## Fluxo Recomendado Para Agentes

1. Rodar `cairn doctor --path <vault>`.
2. Rodar `cairn search "<sintoma ou tarefa>" --path <vault> --json`.
3. Abrir no máximo os três primeiros resultados.
4. Preferir `show --section`, `show --snippet` ou `retrieve --budget` antes de
   abrir documentos completos.
5. Resolver a tarefa.
6. Rodar `cairn similar "<novo conhecimento>" --path <vault>`.
7. Atualizar uma nota existente quando possível; criar uma nova nota só quando o
   conhecimento for reutilizável e ainda não estiver representado.
8. Rodar `cairn validate --path <vault>` e `cairn index --path <vault>`.

## Desenvolvimento do Repositório

Rodar testes:

```bash
python -m unittest discover -v
```

Rodar avaliação determinística de busca:

```bash
python bench/run_eval.py
python bench/run_eval.py --quiet --compare-golden bench/golden.json
```

Tópicos do benchmark podem incluir `mode`, `compare_mode`, `ranker` e
`compare_ranker`. Isso permite medir se `passages` reduz tokens contra
`documents`, e se rankers experimentais melhoram qualidade contra a linha de
base `bm25`. A saída do benchmark inclui um resumo `comparison` para
comparações de redução de tokens.

O runtime usa apenas a biblioteca padrão do Python.
