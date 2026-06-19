# Experimentos De Ranking E Embeddings

Este guia define a barra para mudar o ranking de recuperação do ApolloKairn. Ele
serve para issues e pull requests que ajustam pesos de BM25, variantes de query,
RRF, recuperação por passagens ou adapters opcionais de embeddings.

O core padrão deve continuar local-first, sem dependências de runtime e
determinístico. Embeddings e chamadas a modelo ficam em limites opcionais, não
como comportamento obrigatório do core.

## Knobs Atuais De Ranking

ApolloKairn expõe estes controles de ranking hoje:

| Área | Controle atual | Local |
| --- | --- | --- |
| BM25 de documentos | Pesos por coluna passados para SQLite FTS5 `bm25(docs, ...)` | `src/cairn/indexer.py` |
| BM25 de passagens | Pesos por coluna passados para SQLite FTS5 `bm25(passages, ...)` | `src/cairn/indexer.py` |
| Variantes de query | Variantes estrita, ampla e prefixo/inflection usadas pelo RRF | `src/cairn/ranking.py` |
| Tokenizer | FTS5 `unicode61 remove_diacritics 2` para busca sem acento | `src/cairn/indexer.py` |
| Expansão de glossário | Aliases aprovados em `glossary.md` para fallback determinístico | `src/cairn/vocabulary.py` |
| RRF | `k = 60` fixo para fusão de documentos e passagens | `src/cairn/indexer.py` |
| Fallback de retrieve | `--ranker auto` tenta BM25 primeiro e depois RRF | `src/cairn/retriever.py` |

O `bm25()` embutido do SQLite FTS5 aceita pesos para colunas indexadas. As
constantes BM25 `k1` e `b` não são knobs configuráveis no caminho atual do core
do ApolloKairn. Mudar isso exigiria uma função de ranking customizada ou outro
backend de recuperação, então deve ser tratado como trabalho de arquitetura, não
como uma issue pequena de ajuste de pesos. Veja a documentação do SQLite FTS5:
https://sqlite.org/fts5.html#the_bm25_function.

## Rodadas Obrigatórias Do Experimento

Rode estes comandos antes de propor ou aceitar mudanças de ranking:

```bash
python -m unittest discover
python bench/run_eval.py --quiet --compare-golden bench/golden.json
python bench/run_eval.py --fixture bench/fixtures/vault-large --topics bench/topics-large.jsonl --qrels bench/qrels-large.tsv --quiet --compare-golden bench/golden-large.json
python bench/agent/run_agent_eval.py --dry-run --fixture bench/fixtures/vault-large --tasks bench/agent/tasks-large.jsonl --topics bench/topics-large.jsonl --quiet
python bench/agent/run_agent_eval.py --mock --fixture bench/fixtures/vault-large --tasks bench/agent/tasks-large.jsonl --topics bench/topics-large.jsonl --quiet
python bench/run_grep_baseline.py --quiet --compare-golden bench/grep-golden.json
python bench/run_writeback_eval.py --quiet --compare-golden bench/writeback/golden.json
python bench/run_perf_eval.py --quiet --repeat 1
python bench/publish_metrics.py --output docs/data/benchmarks.json --tests 228
git diff --check
```

Para trabalho sensível a tempo de execução, rode também a suíte de performance
com mais repetições na mesma máquina:

```bash
python bench/run_perf_eval.py --quiet --repeat 3
```

## Baseline A Ser Batido

Estes são os baselines commitados em 2026-06-19:

| Suíte | Corpus | Resultado atual |
| --- | --- | --- |
| Recuperação pequena | 25 arquivos Markdown, 28 tópicos | `Recall@3 = 1.0`, `MRR@3 = 1.0`, `nDCG@3 = 0.9941` |
| Recuperação grande | 304 arquivos Markdown, 80 tópicos | `Recall@3 = 1.0`, `MRR@3 = 0.9375`, `nDCG@3 = 0.8631` |
| Agent L1 mock | 80 tarefas sobre o corpus grande | `context_sufficiency = 1.0`, `abstention_accuracy = 1.0` |
| Baseline grep raw-read | 25 arquivos Markdown, 28 tópicos | `Recall@20 = 0.7857`, `nDCG@20 = 0.7857`, `tokens = 3988` |
| Writeback | Casos determinísticos de create/update/no-op/conflito | `decision_accuracy = 1.0` |

Os slices do corpus grande são `exact_error`, `paraphrase`, `cross_doc`,
`role_workflow`, `pt_br`, `noisy_query`, `filtered`, `passage_budget` e
`no_answer`. O L1 mock de agente usa o mesmo conjunto de slices.

## Critérios De Aceite

Um experimento de ranking ou embedding só é aceitável quando todos os gates
aplicáveis forem satisfeitos:

| Gate | Resultado exigido |
| --- | --- |
| Golden checks | As comparações de `bench/golden.json`, `bench/golden-large.json`, `bench/grep-golden.json` e `bench/writeback/golden.json` passam. |
| Qualidade global | Métricas de recuperação pequena e grande não regridem contra o baseline commitado, a menos que a issue aceite explicitamente o trade-off. |
| Qualidade por slice | Nenhum slice crítico regride mais que `0.01` absoluto em nDCG ou MRR sem justificativa escrita. |
| Sem resposta | `no_answer.false_positive_rate` do corpus grande fica em `0.0`; `abstention_accuracy` do L1 mock fica em `1.0`. |
| Orçamentos | `budget_compliance_rate` fica em `1.0` nas suítes de recuperação e L1 mock. |
| Custo de contexto | `returned_tokens` não aumenta mais que 5%, salvo ganho de pelo menos `0.02` nDCG absoluto ou trade-off documentado na issue. |
| Performance | p95 de search/retrieve, tempo de índice completo, tempo incremental e tamanho do índice não devem regredir mais que 20% na mesma máquina sem justificativa. |
| Limite do core | `pyproject.toml` mantém `dependencies = []` em runtime, salvo ADR explícito mudando a arquitetura. |

Não trate score de ranking como confiança. Métricas de ranking mostram se a
fonte esperada foi retornada e bem ordenada; elas não provam que um agente
respondeu corretamente.

## L1 E L2 De Agente

`bench/agent/run_agent_eval.py --mock` é um gate L1 determinístico. Ele valida
schema de tarefa, agregação, acurácia de paths, fatos esperados no contexto
recuperado, tarefas de abstenção e orçamento. Ele mede suficiência de contexto,
não comportamento de modelo real.

Avaliação L2 paga ou com modelo real deve ficar fora do CI rígido. Ela pode
calibrar se mudanças de ranking reduzem tokens reais de agente ou melhoram a
qualidade da resposta. No mínimo, registre provider, modelo, temperatura,
contagem de repetições, tokens, custo e o contrato do provider-command. Quando o
provider usar seed, política de retry ou juiz LLM, inclua esses detalhes no
relatório do eval. L2 deve comparar ApolloKairn contra baseline raw-read ou grep
no mesmo conjunto de tarefas.

O runner suporta um contrato explícito de provider externo:

```bash
python bench/agent/run_agent_eval.py --live \
  --provider-command "python path/to/provider.py" \
  --provider-name local-eval \
  --model fixed-model \
  --repeat 5 \
  --output docs/data/agent-evals.json
```

O comando provider lê JSON de request pelo stdin. O request inclui pergunta,
contexto recuperado, paths das fontes, estratégia, modelo, temperatura e
repetição. Ele não inclui `expected_paths` nem `expected_facts`. O provider
escreve JSON de resposta com `answer`, `cited_paths`, `abstained`,
`tool_calls`, `input_tokens`, `output_tokens` e `cost_usd`.

## Experimentos Com Embeddings

Trabalho com embeddings só deve virar issue de plugin ou adapter quando preserva
o contrato do core:

- desativado por padrão e não obrigatório para instalar, indexar, buscar,
  recuperar, escrever ou testar;
- nenhum corpo de nota enviado para serviços de rede sem opt-in explícito do
  usuário;
- índice local continua reconstruível a partir do Markdown como fonte da
  verdade;
- fallback lexical BM25/RRF continua disponível e coberto por testes
  determinísticos;
- nome do modelo, dimensões, tamanho em disco, tempo de indexação, latência de
  query e comportamento de refresh são reportados;
- melhoria concentrada em slices em que busca lexical deve ter dificuldade,
  como `paraphrase`, `cross_doc`, `pt_br` ou `role_workflow`;
- slices de erro exato, filtros, orçamento e sem resposta não regridem.

## Template De Issue Para Experimentos

Toda issue de experimento de ranking deve incluir:

```text
Hipótese:
Knobs alterados:
Slices que devem melhorar:
Slices de risco:
Comandos rodados:
Métricas globais antes/depois:
Métricas por slice antes/depois:
Delta de tokens retornados:
Delta de performance:
Resultado do L1 mock:
Decisão:
```

Se a issue propõe customizar BM25 `k1` ou `b`, criar ranker customizado ou mover
embeddings para o pacote core, ela precisa de uma decisão de arquitetura antes.
