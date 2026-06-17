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

```bash
cairn validate --path ~/brain
```

Use antes de indexar, antes de commitar um vault ou quando um agente criou ou
editou notas.

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
```

Use antes de abrir documentos completos. Este é o principal comando para
economizar tokens.

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
```

Use quando um agente precisa de contexto útil imediatamente sem rodar `search` e
`show` manualmente. O orçamento usa uma aproximação simples de 4 caracteres por
token.

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

Encontra notas existentes antes de criar uma duplicata.

```bash
cairn similar "deploy forbidden token" --path ~/brain --limit 5
```

Use antes de adicionar uma nova nota. Se o resultado for próximo o bastante,
atualize a nota existente em vez de criar outra.

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

O runtime usa apenas a biblioteca padrão do Python.
