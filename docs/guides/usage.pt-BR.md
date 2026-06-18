# Guia de Uso do Cairn

Este guia explica para que o Cairn serve, como configurar um vault e quando usar
cada comando.

## Para Que Serve

Cairn é um vault local em Markdown otimizado para fluxos com agentes de IA. Ele
ajuda agentes a salvar conhecimento reutilizável depois de resolver problemas,
tomar decisões, documentar processos ou aprender padrões recorrentes.

Cairn não depende de um produto de agentes específico. Qualquer harness que
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
cairn --help
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

Depois de criar ou editar notas, rode `cairn index`. Busca e recuperação usam o
índice local; se ele estiver ausente ou desatualizado, `cairn doctor` avisa.

## Criando Um Vault

```bash
cairn init --path ~/brain --profile engineering
cairn validate --path ~/brain
cairn index --path ~/brain --rebuild
cairn doctor --path ~/brain
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

O vault também pode ter um `glossary.md` no topo. Cairn trata esse arquivo como
um controle reservado, não como uma nota comum.

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

Cairn mantém a busca padrão conservadora. `search` e `retrieve` primeiro rodam a
consulta BM25 exata. Só quando ela não retorna linhas, Cairn expande termos e
aliases aprovados no glossário e tenta de novo com uma consulta OR barata. Isso
mantém buscas comuns estáveis e ainda cobre gaps de sinônimos curados.

Gerencie o glossário com:

```bash
cairn vocab add-term Kubernetes --alias k8s --alias kube --path ~/brain
cairn vocab add-alias Kubernetes k8s-prod --path ~/brain
cairn vocab add-term Kubernetes --alias k8s --path ~/brain --json
cairn vocab suggest "kubernetes rollback" --path ~/brain --json
cairn vocab validate --path ~/brain --json
```

`vocab suggest` nunca escreve no vault. Ele relata candidatos determinísticos a
partir das notas locais para uma pessoa ou agente decidir se o alias deve virar
vocabulário aprovado.

## Referência de Comandos

### `cairn init`

Cria um novo vault.

```bash
cairn init --path ~/brain --profile engineering
cairn init --path ~/brain --profile engineering --json
```

Use uma vez por vault. Rodar novamente é seguro; arquivos existentes são
preservados.
Com `--json`, o resultado inclui `root`, `created` e `skipped`.

### `cairn validate`

Verifica se as notas Markdown seguem o `SCHEMA.md` e as regras de frontmatter.
Ele também bloqueia valores comuns com aparência de segredo, como access keys,
tokens de provedores e blocos de chave privada, sem imprimir o valor detectado.

```bash
cairn validate --path ~/brain
cairn validate --path ~/brain --json
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
  --body "Deploy falhou depois da rotação do token. Atualize o segredo de CI e rode novamente o job que falhou."
```

`capture` é um alias com o mesmo comportamento. Use depois que uma tarefa foi
resolvida e o conhecimento provavelmente será útil de novo.

Antes de escrever, Cairn valida a nota renderizada contra o `SCHEMA.md` e
escaneia o conteúdo novo por valores comuns com aparência de segredo.
Combinações inválidas de type/tag ou segredos detectados falham antes da criação
do arquivo Markdown. Com `--json`, falhas de policy retornam `ok`, `path`,
`error_count` e `errors`.

O argumento `--body` da CLI é melhor para textos curtos. Para notas com várias
seções, crie o corpo em um arquivo Markdown e passe com `--body-file`:

```bash
cairn capture --path ~/brain \
  --title "Webhook 400 after SDK upgrade" \
  --description "Corrige requests de webhook rejeitados após mudança de schema." \
  --type Runbook \
  --tag bug \
  --system support-api \
  --body-file ./webhook-400-body.md
```

Use `--body-stdin` quando outra ferramenta ou agente gerar o corpo:

```bash
cat ./webhook-400-body.md | cairn capture --path ~/brain \
  --title "Webhook 400 after SDK upgrade" \
  --description "Corrige requests de webhook rejeitados após mudança de schema." \
  --type Runbook \
  --tag bug \
  --body-stdin
```

Se o corpo começa com um heading Markdown, Cairn preserva como está. Se for
texto simples, Cairn envolve em uma seção `# Context`.

Para fluxos com agentes, use `--json` para receber o resultado da escrita e
`--dry-run` para prever o caminho de destino sem criar o arquivo:

```bash
cairn capture --path ~/brain --title "Nota rascunho" --description "Preview." --tag workflow --body "..." --dry-run --json
```

### `cairn update`

Adiciona texto a uma nota existente se o mesmo texto ainda não estiver lá.

```bash
cairn update knowledge/deploy-403.md --path ~/brain --append "Adicionar o novo passo de verificação."
cairn update knowledge/deploy-403.md --path ~/brain --append-file ./deploy-403-update.md
cat ./deploy-403-update.md | cairn update knowledge/deploy-403.md --path ~/brain --append-stdin
```

Use quando `cairn similar` encontrar uma nota existente que deve ser expandida
em vez de duplicada. O documento pode ser um caminho relativo ao vault ou um
caminho absoluto dentro dele. Updates são idempotentes e atualizam o timestamp
da nota só quando texto novo é realmente adicionado.

Agentes podem pedir resultados estruturados, prever escritas e proteger contra
arquivos desatualizados:

```bash
cairn update knowledge/deploy-403.md --path ~/brain --append-file ./deploy-403-update.md --dry-run --json
cairn update knowledge/deploy-403.md --path ~/brain --append-file ./deploy-403-update.md --expect-sha256 <SHA256_ATUAL> --json
```

O JSON inclui `changed`, `would_change`, `dry_run`, `reason`, `sha256_before` e
`sha256_after`. Quando o texto já existe na nota, `reason` é `already_present`.
O texto anexado é escaneado por valores comuns com aparência de segredo antes da
escrita. Com `--json`, falhas de policy usam o mesmo formato `ok`, `path`,
`error_count` e `errors` do `capture`.

### `cairn index`

Cria ou atualiza o índice local SQLite FTS.

```bash
cairn index --path ~/brain --rebuild
cairn index --path ~/brain
cairn index --path ~/brain --json
```

Use `--rebuild` na primeira configuração ou se o índice estiver corrompido. Sem
`--rebuild`, a indexação é incremental: arquivos alterados são atualizados,
arquivos removidos saem do índice e arquivos iguais são ignorados.

### `cairn doctor`

Verifica a saúde do vault e se o índice está atualizado.

```bash
cairn doctor --path ~/brain
cairn doctor --path ~/brain --json
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
Se existir um `glossary.md` no topo do vault, o BM25 estrito recebe
automaticamente uma tentativa de fallback com aliases aprovados apenas quando a
consulta exata não retorna linhas.

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
cairn retrieve "deploy token rotation kubernetes secret" --path ~/brain --ranker auto --budget 800
cairn retrieve "reconnecting cache workers" --path ~/brain --mode passages --ranker rrf --budget 500
cairn retrieve "reconnecting cache workers" --path ~/brain --mode passages --ranker auto --budget 500
cairn retrieve "deploy 403" --path ~/brain --mode passages --budget 500 --json
```

Use quando um agente precisa de contexto útil imediatamente sem rodar `search` e
`show` manualmente. O orçamento usa uma aproximação simples de 4 caracteres por
token. A recuperação redige valores comuns com aparência de segredo antes de
imprimir o pacote de contexto.

Use `--mode passages` quando o agente precisa das menores seções úteis em vez de
documentos completos. A saída de passagem inclui path, heading e intervalo de
linhas para o agente reabrir o contexto exato se precisar.

Use `--ranker auto` quando quiser um fallback seguro: Cairn tenta o `bm25`
estrito primeiro e só gasta o trabalho extra do RRF quando nenhum contexto é
retornado. Use `--ranker rrf` quando quiser ranking lexical fundido sempre.

A saída JSON retorna o mesmo pacote de contexto com metadados: query, modo,
ranker pedido, ranker realmente usado, orçamento de tokens, tokens estimados
usados, quantidade de fontes, contexto renderizado e metadados por fonte.

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
cairn show knowledge/deploy-403.md --path ~/brain --section Diagnostico --json
```

Leituras parciais são úteis depois que `search` encontrou o documento certo, mas
o agente só precisa de uma seção ou de algumas linhas próximas.
Seletores de seção e snippet ignoram acentos, então consultas ASCII encontram
headings em português como `Solução` ou `Diagnóstico`.

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

Resultados incluem o campo `kind`. `duplicate_candidate` indica que o match é
forte o bastante para preferir atualizar a nota existente. `related` indica que
a nota é contexto útil, mas o agente deve inspecionar antes de decidir entre
atualizar ou criar uma nova nota.

### `cairn vocab`

Gerencia o glossário determinístico no topo do vault.

```bash
cairn vocab add-term Kubernetes --alias k8s --alias kube --path ~/brain
cairn vocab add-alias Kubernetes kube --path ~/brain
cairn vocab add-alias Kubernetes kube --path ~/brain --json
cairn vocab suggest "kubernetes rollback" --path ~/brain --limit 5
cairn vocab validate --path ~/brain
```

Use quando várias pessoas ou agentes descrevem o mesmo conceito com termos
diferentes. Busca e recuperação usam apenas termos com `status: approved`.
Sugestões são somente leitura e devem ser revisadas antes de adicionar um novo
alias.

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
cairn export --path ~/brain --output cairn-vault.zip --json
cairn import cairn-vault.zip --path ~/restored-brain --json
```

Arquivos de índice gerados não entram no export. Rode `cairn index` depois de
importar. O export é abortado quando valores comuns com aparência de segredo são
detectados em arquivos que entrariam no arquivo zip.
A saída JSON informa o caminho `output` do arquivo ou o caminho `root` importado.

### `cairn setup-agent` e `cairn refresh-guides`

Cria ou atualiza instruções específicas para agentes dentro do vault.

```bash
cairn setup-agent codex --path ~/brain
cairn setup-agent claude --path ~/brain
cairn setup-agent opencode --path ~/brain
cairn refresh-guides --path ~/brain
cairn setup-agent codex --path ~/brain --json
cairn refresh-guides --path ~/brain --json
```

Use quando o mesmo vault deve ser consumido por diferentes harnesses de agentes.
Cairn é agnóstico de agentes por design: guias gerados e plugins futuros são
adaptadores sobre o mesmo vault local em Markdown, não bases de conhecimento
separadas.
Guias gerados orientam agentes a usar busca JSON, recuperação por passagens com
`--ranker auto`, `cairn vocab suggest` para gaps de vocabulário, types/tags
compatíveis com o schema, `--body-file` ou `--body-stdin` para Markdown
multi-linha, e `validate` mais `index` depois de toda escrita bem-sucedida.
A saída JSON informa os caminhos dos guias gerados.

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

Rodar avaliações determinísticas:

```bash
python bench/run_eval.py
python bench/run_eval.py --quiet --compare-golden bench/golden.json
python bench/run_writeback_eval.py --quiet --compare-golden bench/writeback/golden.json
```

Tópicos do benchmark podem incluir `category`, `mode`, `compare_mode`, `ranker`
e `compare_ranker`. Isso permite medir se `passages` reduz tokens contra
`documents`, se rankers experimentais melhoram qualidade contra a linha de base
`bm25`, e qual classe de workflow cada tópico protege. A saída do benchmark
inclui um resumo `comparison` para comparações de redução de tokens.

O benchmark de escrita usa casos determinísticos para criar, atualizar, no-op,
conflito, prevenção de duplicatas e acurácia do caminho alvo. Ele não chama
modelo; exercita os primitivos locais de similaridade e escrita do Cairn.

O runtime usa apenas a biblioteca padrão do Python.
