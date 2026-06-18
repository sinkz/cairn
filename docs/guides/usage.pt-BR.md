# Guia de Uso do ApolloKairn

Este guia explica para que o ApolloKairn serve, como configurar um vault e quando usar
cada comando.

## Para Que Serve

ApolloKairn é um vault local em Markdown otimizado para fluxos com agentes de IA. Ele
ajuda agentes a salvar conhecimento reutilizável depois de resolver problemas,
tomar decisões, documentar processos ou aprender padrões recorrentes.

ApolloKairn não depende de um produto de agentes específico. Qualquer harness que
consiga rodar comandos de CLI pode usar o mesmo vault e os mesmos arquivos
Markdown. Ele entrega mais valor quando um agente busca primeiro, recupera só o
contexto necessário, resolve a tarefa e registra o conhecimento reutilizável.

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

## Instalação E Primeiro Uso

Instale a partir da raiz do repositório:

```bash
python -m pip install -e .
apollokairn --help
```

Ou rode sem instalar:

```bash
export PYTHONPATH="$PWD/src"
python -m cairn --help
```

PowerShell:

```powershell
$env:PYTHONPATH = Join-Path (Resolve-Path .).Path "src"
python -m cairn --help
```

Depois de criar ou editar notas, rode `apollokairn index`. Busca e recuperação usam o
índice local; se ele estiver ausente ou desatualizado, `apollokairn doctor` avisa.

## Criando Um Vault

```bash
apollokairn init --path ~/brain --profile engineering
apollokairn validate --path ~/brain
apollokairn index --path ~/brain --rebuild
apollokairn doctor --path ~/brain
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
| `.cairn/config.json` | Configurações do ApolloKairn |
| `_templates/concept.md` | Template inicial para novas notas |
| pastas de domínio | `knowledge`, `processes`, `decisions`, `references`, `notes`, `inbox` |

O vault também pode ter um `glossary.md` no topo. ApolloKairn trata esse arquivo como
um controle reservado, não como uma nota comum.

## Registry De Vaults

O registry é um estado local do usuário que mapeia nomes curtos para caminhos de
vaults. Ele permite que uma pessoa ou agente trabalhe de qualquer repositório
sem trocar de diretório ou lembrar caminhos longos.

```bash
apollokairn vault add ~/brain --name pessoal --set-active
apollokairn vault add ~/work-brain --name trabalho
apollokairn vault list
apollokairn vault current
apollokairn vault use trabalho
apollokairn vault doctor
```

Depois que um vault está ativo, comandos podem omitir `--path`:

```bash
apollokairn search "deploy 403"
apollokairn retrieve "acesso de producao" --budget 500
```

Agentes e scripts devem descobrir vaults com JSON e depois passar `--vault`
explicitamente:

```bash
apollokairn vault list --json
apollokairn search "deploy 403" --vault trabalho --json
apollokairn capture --vault pessoal --title "Token rotation" --description "..." --tag deploy --body "..."
```

A ordem de resolução de vaults é:

1. `--path CAMINHO`
2. `--vault NOME`
3. vault ativo por `apollokairn vault use NOME`
4. diretório atual

O registry guarda apenas nomes, caminhos absolutos, timestamps e o nome do vault
ativo. Ele não guarda conteúdo de notas nem segredos.

## Configuração

ApolloKairn guarda configurações locais em `.cairn/config.json`.

Exemplo:

```json
{
  "exclude": ["inbox"],
  "generated_guides": ["AGENTS.md"],
  "profile": "engineering",
  "search_limit": 3,
  "usage_tracking": false
}
```

Campos importantes:

| Campo | Função |
| --- | --- |
| `profile` | Perfil usado na inicialização do vault |
| `search_limit` | Limite padrão sugerido para agentes |
| `exclude` | Pastas ou padrões ignorados pela validação e indexação |
| `generated_guides` | Arquivos de guia de agente gerenciados pelo ApolloKairn |
| `usage_tracking` | Métricas locais opt-in em `.cairn/usage/` |

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

## Glossário E Aliases Determinísticos

Use `glossary.md` para diferenças estáveis de vocabulário que a busca lexical
estrita não consegue inferir, como `k8s` e `kubernetes`. O glossário é dado
explícito dentro do vault, então pode ser revisado e versionado como qualquer
arquivo importante.

```markdown
# Glossary

## Kubernetes

aliases: k8s, kube
status: approved
scope: engineering
```

ApolloKairn mantém a busca padrão conservadora. `search` e `retrieve` expandem
termos e aliases aprovados em grupos determinísticos de consulta, então
variações lexicais competem no mesmo conjunto ranqueado sem sinônimos chumbados
em Python.

Gerencie o glossário com:

```bash
apollokairn vocab add-term Kubernetes --alias k8s --alias kube --path ~/brain
apollokairn vocab add-alias Kubernetes k8s-prod --path ~/brain
apollokairn vocab add-term Kubernetes --alias k8s --path ~/brain --json
apollokairn vocab suggest "kubernetes rollback" --path ~/brain --json
apollokairn vocab validate --path ~/brain --json
```

`vocab suggest` nunca escreve no vault. Ele relata candidatos determinísticos a
partir das notas locais para uma pessoa ou agente decidir se o alias deve virar
vocabulário aprovado.

## Referência de Comandos

### `apollokairn vault`

Registra e seleciona vaults nomeados fora do próprio vault.

```bash
apollokairn vault add ~/brain --name pessoal
apollokairn vault add ~/work-brain --name trabalho --set-active
apollokairn vault list
apollokairn vault list --json
apollokairn vault current
apollokairn vault current --json
apollokairn vault use pessoal
apollokairn vault show trabalho --json
apollokairn vault remove trabalho
apollokairn vault doctor --json
```

Use `vault add` depois de `init`. `--set-active` marca o novo registro como
padrão para comandos seguintes. `vault doctor` verifica se caminhos registrados
ainda existem e ainda parecem vaults do ApolloKairn.

Comandos operacionais aceitam `--path` e `--vault`. `--path` é o mais explícito
e sempre ganha. `--vault` é útil para agentes depois de rodar
`vault list --json`. O vault ativo é conveniente para sessões humanas de CLI e
fluxos futuros de TUI.

### `apollokairn init`

Cria um novo vault.

```bash
apollokairn init --path ~/brain --profile engineering
apollokairn init --path ~/brain --profile engineering --json
```

Use uma vez por vault. Rodar novamente é seguro; arquivos existentes são
preservados.
Com `--json`, o resultado inclui `root`, `created` e `skipped`.

### `apollokairn validate`

Verifica se as notas Markdown seguem o `SCHEMA.md` e as regras de frontmatter.
Ele também bloqueia valores comuns com aparência de segredo, como access keys,
tokens de provedores e blocos de chave privada, sem imprimir o valor detectado.

```bash
apollokairn validate --path ~/brain
apollokairn validate --path ~/brain --json
```

Use antes de indexar, antes de commitar um vault ou quando um agente criou ou
editou notas.

### `apollokairn add` e `apollokairn capture`

Cria uma nota reutilizável com frontmatter válido do ApolloKairn.

```bash
apollokairn add --path ~/brain \
  --title "Deploy 403 after token rotation" \
  --description "Corrige autorização antiga de CI após rotação de token." \
  --type Runbook \
  --tag bug \
  --tag deploy \
  --system ci \
  --signal "HTTP 403" \
  --body "Deploy falhou depois da rotação do token. Atualize o segredo de CI e rode novamente o job que falhou."
```

`capture` é um alias com o mesmo comportamento. Use depois que uma tarefa foi
resolvida e o conhecimento provavelmente será útil de novo.

Antes de escrever, ApolloKairn valida a nota renderizada contra o `SCHEMA.md` e
escaneia o conteúdo novo por valores comuns com aparência de segredo.
Combinações inválidas de type/tag ou segredos detectados falham antes da criação
do arquivo Markdown. Com `--json`, falhas de policy retornam `ok`, `path`,
`error_count` e `errors`.

O argumento `--body` da CLI é melhor para textos curtos. Para notas com várias
seções, crie o corpo em um arquivo Markdown e passe com `--body-file`:

```bash
apollokairn capture --path ~/brain \
  --title "Webhook 400 after SDK upgrade" \
  --description "Corrige requests de webhook rejeitados após mudança de schema." \
  --type Runbook \
  --tag bug \
  --system support-api \
  --body-file ./webhook-400-body.md
```

Use `--body-stdin` quando outra ferramenta ou agente gerar o corpo:

```bash
cat ./webhook-400-body.md | apollokairn capture --path ~/brain \
  --title "Webhook 400 after SDK upgrade" \
  --description "Corrige requests de webhook rejeitados após mudança de schema." \
  --type Runbook \
  --tag bug \
  --body-stdin
```

Se o corpo começa com um heading Markdown, ApolloKairn preserva como está. Se for
texto simples, ApolloKairn envolve em uma seção `# Context`.

Para fluxos com agentes, use `--json` para receber o resultado da escrita e
`--dry-run` para prever o caminho de destino sem criar o arquivo:

```bash
apollokairn capture --path ~/brain --title "Nota rascunho" --description "Preview." --tag workflow --body "..." --dry-run --json
```

### `apollokairn update`

Adiciona texto a uma nota existente se o mesmo texto ainda não estiver lá.

```bash
apollokairn update knowledge/deploy-403.md --path ~/brain --append "Adicionar o novo passo de verificação."
apollokairn update knowledge/deploy-403.md --path ~/brain --append-file ./deploy-403-update.md
cat ./deploy-403-update.md | apollokairn update knowledge/deploy-403.md --path ~/brain --append-stdin
```

Use quando `apollokairn similar` encontrar uma nota existente que deve ser expandida
em vez de duplicada. O documento pode ser um caminho relativo ao vault ou um
caminho absoluto dentro dele. Updates são idempotentes e atualizam o timestamp
da nota só quando texto novo é realmente adicionado.

Agentes podem pedir resultados estruturados, prever escritas e proteger contra
arquivos desatualizados:

```bash
apollokairn update knowledge/deploy-403.md --path ~/brain --append-file ./deploy-403-update.md --dry-run --json
apollokairn update knowledge/deploy-403.md --path ~/brain --append-file ./deploy-403-update.md --expect-sha256 <SHA256_ATUAL> --json
```

O JSON inclui `changed`, `would_change`, `dry_run`, `reason`, `sha256_before` e
`sha256_after`. Quando o texto já existe na nota, `reason` é `already_present`.
O texto anexado é escaneado por valores comuns com aparência de segredo antes da
escrita. Com `--json`, falhas de policy usam o mesmo formato `ok`, `path`,
`error_count` e `errors` do `capture`.

### `apollokairn index`

Cria ou atualiza o índice local SQLite FTS.

```bash
apollokairn index --path ~/brain --rebuild
apollokairn index --path ~/brain
apollokairn index --path ~/brain --json
```

Use `--rebuild` na primeira configuração ou se o índice estiver corrompido. Sem
`--rebuild`, a indexação é incremental: arquivos alterados são atualizados,
arquivos removidos saem do índice e arquivos iguais são ignorados.

### `apollokairn doctor`

Verifica a saúde do vault e se o índice está atualizado.

```bash
apollokairn doctor --path ~/brain
apollokairn doctor --path ~/brain --json
```

Use quando a busca parecer estranha, depois de edições manuais ou antes de uma
sessão com agente. Ele aponta erros de validação, índice ausente, índice inválido
ou índice desatualizado.

### `apollokairn search`

Busca no vault e retorna resultados compactos com snippets.

```bash
apollokairn search "deploy 403 workspace access" --path ~/brain --limit 3
apollokairn search "deploy token rotation kubernetes secret" --path ~/brain --ranker rrf
```

Use antes de abrir documentos completos. Este é o principal comando para
economizar tokens. O ranker padrão `bm25` é estrito e estável. Use o
experimental `--ranker rrf` quando a busca mistura sinais corretos com termos
extras ou variantes lexicais.
Se existir um `glossary.md` no topo do vault, aliases aprovados entram no mesmo
fluxo determinístico de busca. Assim, termos como `k8s` e `kubernetes`
conseguem recuperar as mesmas notas sem sinônimos chumbados em Python.

Filtros:

```bash
apollokairn search "retry timeout" --path ~/brain --type Decision
apollokairn search "deploy" --path ~/brain --tag deploy
apollokairn search "timeout" --path ~/brain --system checkout
```

Saída JSON para agentes:

```bash
apollokairn search "cache stampede" --path ~/brain --json
apollokairn search "cache stampede" --path ~/brain --json --explain
```

`--explain` envolve os resultados com diagnósticos determinísticos de ranking:
score, campos encontrados, termos da consulta encontrados e uma nota explícita
de que score não é confiança.

### `apollokairn retrieve`

Monta um pacote de contexto para LLM dentro de um orçamento aproximado de tokens.

```bash
apollokairn retrieve "deploy 403" --path ~/brain --limit 3 --budget 800
apollokairn retrieve "deploy 403" --path ~/brain --mode passages --budget 500
apollokairn retrieve "deploy token rotation kubernetes secret" --path ~/brain --ranker rrf --budget 800
apollokairn retrieve "deploy token rotation kubernetes secret" --path ~/brain --ranker auto --budget 800
apollokairn retrieve "reconnecting cache workers" --path ~/brain --mode passages --ranker rrf --budget 500
apollokairn retrieve "reconnecting cache workers" --path ~/brain --mode passages --ranker auto --budget 500
apollokairn retrieve "deploy 403" --path ~/brain --mode passages --budget 500 --json
apollokairn retrieve "deploy 403" --path ~/brain --mode passages --budget 500 --json --explain
```

Use quando um agente precisa de contexto útil imediatamente sem rodar `search` e
`show` manualmente. O orçamento usa uma aproximação simples de 4 caracteres por
token. A recuperação redige valores comuns com aparência de segredo antes de
imprimir o pacote de contexto.

Use `--mode passages` quando o agente precisa das menores seções úteis em vez de
documentos completos. A saída de passagem inclui path, heading e intervalo de
linhas para o agente reabrir o contexto exato se precisar.

Use `--ranker auto` quando quiser um fallback seguro: ApolloKairn tenta o `bm25`
estrito primeiro e só gasta o trabalho extra do RRF quando nenhum contexto é
retornado. Use `--ranker rrf` quando quiser ranking lexical fundido sempre.

A saída JSON retorna o mesmo pacote de contexto com metadados: query, modo,
ranker pedido, ranker realmente usado, orçamento de tokens, tokens estimados
usados, quantidade de fontes, contexto renderizado e metadados por fonte.
Com `--explain`, a saída JSON é `{ "packet": ..., "explanations": [...] }`, e
cada explicação inclui campos/termos encontrados mais a nota diagnóstica do
score.

Filtros funcionam como em `search`:

```bash
apollokairn retrieve "retry timeout" --path ~/brain --type Decision --system checkout --budget 600
```

### `apollokairn show`

Abre um documento do vault.

```bash
apollokairn show knowledge/deploy-403.md --path ~/brain
```

Use leituras parciais para reduzir contexto:

```bash
apollokairn show knowledge/deploy-403.md --path ~/brain --section Diagnosis
apollokairn show knowledge/deploy-403.md --path ~/brain --snippet "workspace access" --context 2
apollokairn show knowledge/deploy-403.md --path ~/brain --lines 20:40
apollokairn show knowledge/deploy-403.md --path ~/brain --section Diagnostico --json
```

Leituras parciais são úteis depois que `search` encontrou o documento certo, mas
o agente só precisa de uma seção ou de algumas linhas próximas.
Seletores de seção e snippet ignoram acentos, então consultas ASCII encontram
headings em português como `Solução` ou `Diagnóstico`.

### `apollokairn similar`

Encontra notas existentes antes de criar uma duplicata. Ele combina busca lexical
indexada com um scan local por fingerprint leve, então ainda consegue encontrar
quase duplicatas quando a nova nota tem termos extras.

```bash
apollokairn similar "deploy forbidden token" --path ~/brain --limit 5
```

Use antes de adicionar uma nova nota. Se o resultado for próximo o bastante,
atualize a nota existente em vez de criar outra.

Saída JSON para agentes:

```bash
apollokairn similar "deploy forbidden token" --path ~/brain --json
```

Resultados incluem o campo `kind`. `duplicate_candidate` indica que o match é
forte o bastante para preferir atualizar a nota existente. `related` indica que
a nota é contexto útil, mas o agente deve inspecionar antes de decidir entre
atualizar ou criar uma nova nota.

### `apollokairn vocab`

Gerencia o glossário determinístico no topo do vault.

```bash
apollokairn vocab add-term Kubernetes --alias k8s --alias kube --path ~/brain
apollokairn vocab add-alias Kubernetes kube --path ~/brain
apollokairn vocab add-alias Kubernetes kube --path ~/brain --json
apollokairn vocab suggest "kubernetes rollback" --path ~/brain --limit 5
apollokairn vocab validate --path ~/brain
```

Use quando várias pessoas ou agentes descrevem o mesmo conceito com termos
diferentes. Busca e recuperação usam apenas termos com `status: approved`.
Sugestões são somente leitura e devem ser revisadas antes de adicionar um novo
alias.

### `apollokairn stats`

Mostra tamanho do vault, distribuição por tipos/tags e contagem aproximada de
tokens.

```bash
apollokairn stats --path ~/brain
apollokairn stats --path ~/brain --json
```

Use para entender se o vault está crescendo em uma forma saudável.

### `apollokairn usage`

Controla métricas locais opt-in e gera um relatório estático do vault.

```bash
apollokairn usage status --path ~/brain
apollokairn usage enable --path ~/brain
apollokairn usage report --path ~/brain
apollokairn usage report --path ~/brain --html
apollokairn usage report --path ~/brain --json
apollokairn usage disable --path ~/brain
```

Quando ativado, ApolloKairn grava eventos redigidos em
`.cairn/usage/events.jsonl`. `usage report --html` grava uma página estática
local em `.cairn/reports/usage.html` e um resumo JSON em
`.cairn/reports/usage-summary.json`.

As métricas são locais e vêm desativadas por padrão. Eventos incluem nome do
comando, queries redigidas, paths retornados ou alterados, tempo de execução,
contagens de resultado e uso estimado de tokens. Eles não guardam corpos de
notas nem snippets. `usage enable` também adiciona `.cairn/usage/` e
`.cairn/reports/` ao `.gitignore` do vault.

### `apollokairn export` e `apollokairn import`

Exporta ou importa um arquivo zip do vault.

```bash
apollokairn export --path ~/brain --output apollokairn-vault.zip
apollokairn import apollokairn-vault.zip --path ~/restored-brain
apollokairn export --path ~/brain --output apollokairn-vault.zip --json
apollokairn import apollokairn-vault.zip --path ~/restored-brain --json
```

Arquivos de índice gerados não entram no export. Rode `apollokairn index` depois de
importar. O export é abortado quando valores comuns com aparência de segredo são
detectados em arquivos que entrariam no arquivo zip.
A saída JSON informa o caminho `output` do arquivo ou o caminho `root` importado.

### `apollokairn setup-agent` e `apollokairn refresh-guides`

Cria ou atualiza instruções específicas para agentes dentro do vault.

```bash
apollokairn setup-agent codex --path ~/brain
apollokairn setup-agent claude --path ~/brain
apollokairn setup-agent opencode --path ~/brain
apollokairn setup-agent hermes --path ~/brain
apollokairn setup-agent copilot --path ~/brain
apollokairn refresh-guides --path ~/brain
apollokairn setup-agent codex --path ~/brain --json
apollokairn refresh-guides --path ~/brain --json
```

Use quando o mesmo vault deve ser consumido por diferentes harnesses de agentes.
ApolloKairn é agnóstico de agentes por design: guias gerados e plugins futuros são
adaptadores sobre o mesmo vault local em Markdown, não bases de conhecimento
separadas.
Guias gerados orientam agentes a usar busca JSON, recuperação por passagens com
`--ranker auto`, `apollokairn vocab suggest` para gaps de vocabulário, types/tags
compatíveis com o schema, `--body-file` ou `--body-stdin` para Markdown
multi-linha, e `validate` mais `index` depois de toda escrita bem-sucedida.
A saída JSON informa os caminhos dos guias gerados.
Veja [Adapters para agentes](adapters.pt-BR.md) para targets suportados e
caminhos gerados.

## Fluxo Recomendado Para Agentes

1. Resolver um vault com `--path <vault>`, `--vault <nome>` ou
   `apollokairn vault current --json`.
2. Rodar `apollokairn doctor --vault <nome>` ou `apollokairn doctor --path <vault>`.
3. Rodar `apollokairn search "<sintoma ou tarefa>" --vault <nome> --json`.
4. Abrir no máximo os três primeiros resultados.
5. Preferir `show --section`, `show --snippet` ou `retrieve --budget` antes de
   abrir documentos completos.
6. Resolver a tarefa.
7. Rodar `apollokairn similar "<novo conhecimento>" --vault <nome>`.
8. Atualizar uma nota existente quando possível; criar uma nova nota só quando o
   conhecimento for reutilizável e ainda não estiver representado.
9. Rodar `apollokairn validate --vault <nome>` e `apollokairn index --vault <nome>`.

## Desenvolvimento do Repositório

Rodar testes:

```bash
python -m unittest discover -v
```

Rodar avaliações determinísticas:

```bash
python bench/run_eval.py
python bench/run_eval.py --quiet --compare-golden bench/golden.json
python bench/run_writeback_eval.py --quiet --compare-golden bench/writeback/golden.json
python bench/publish_metrics.py --output docs/data/benchmarks.json --tests 194
```

Tópicos do benchmark podem incluir `category`, `mode`, `compare_mode`, `ranker`
e `compare_ranker`. Isso permite medir se `passages` reduz tokens contra
`documents`, se rankers experimentais melhoram qualidade contra a linha de base
`bm25`, e qual classe de workflow cada tópico protege. A saída do benchmark
inclui um resumo `comparison` para comparações de redução de tokens.

O benchmark de escrita usa casos determinísticos para criar, atualizar, no-op,
conflito, prevenção de duplicatas e acurácia do caminho alvo. Ele não chama
modelo; exercita os primitivos locais de similaridade e escrita do ApolloKairn.

`bench/publish_metrics.py` é a etapa de publicação para o dashboard do GitHub
Pages. Ele roda as duas suítes determinísticas, atualiza os valores atuais,
deduplica a linha mais recente do histórico por data e rótulo e adiciona deltas
das métricas contra a rodada anterior.

O runtime usa apenas a biblioteca padrão do Python.
