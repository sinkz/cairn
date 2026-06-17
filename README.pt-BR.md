# Cairn

**Cairn é um segundo cérebro pronto para agentes, para pessoas e times.**

Cairn é um vault local-first em Markdown para humanos e agentes de IA
registrarem, buscarem e reutilizarem conhecimento sem desperdiçar contexto.
Ele é agnóstico de ferramenta: o mesmo vault pode ser usado com Codex, Claude
Code, OpenCode, GitHub Copilot ou qualquer harness agentico que consiga ler
arquivos e executar uma CLI.

English version: [README.md](README.md)

## Por Que Existe

Conhecimento útil costuma se perder em chats, tickets, sessões de terminal e
conversas com agentes. Meses depois, o mesmo bug, processo, acesso ou decisão
de biblioteca aparece de novo e o trabalho de descoberta começa do zero.

Cairn guarda esse conhecimento reutilizável em um vault Markdown estruturado e
pesquisável:

- arquivos locais que podem ficar no seu próprio repositório Git;
- convenções compatíveis com OKF usando Markdown e frontmatter;
- busca rápida com SQLite FTS;
- filtros por metadados e recuperação com orçamento de tokens;
- leitura parcial para agentes abrirem menos contexto;
- checagem de notas similares antes de criar duplicatas.

## Começo Rápido

```bash
python -m pip install -e .
cairn init --path .sandbox/my-vault --profile personal
cairn validate --path .sandbox/my-vault
cairn index --path .sandbox/my-vault --rebuild
cairn doctor --path .sandbox/my-vault
cairn search "deploy 403" --path .sandbox/my-vault --limit 3
cairn retrieve "deploy 403" --path .sandbox/my-vault --budget 800
```

Em um checkout fonte sem instalar, configure `PYTHONPATH=src` e use
`python -m cairn ...`.

## Documentação

- [Guia de uso em PT-BR](docs/guides/usage.pt-BR.md)
- [English usage guide](docs/guides/usage.md)
- [PRD](docs/prd.md)
- [Notas de design](docs/plans/2026-06-17-cairn-design.md)
- [Pesquisa sobre OKF](docs/pesquisa.md)

## Referência OKF

Cairn usa ideias do Open Knowledge Format como uma base leve de
interoperabilidade. Ele não depende de Google Cloud, Gemini, BigQuery ou da
implementação de referência do OKF.

- [Anúncio do Google Cloud sobre OKF](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing)
- [GoogleCloudPlatform/knowledge-catalog](https://github.com/GoogleCloudPlatform/knowledge-catalog)
- [Diretório OKF](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf)
- [Especificação OKF v0.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)

## Status

Cairn já tem um Core MVP funcional com melhorias pós-MVP de busca:

- inicialização de vault com perfis;
- validação;
- índice local incremental;
- busca com filtros;
- recuperação com orçamento de tokens;
- leitura parcial de documentos;
- checagem de notas similares;
- diagnóstico do vault e do índice.

O runtime usa apenas a biblioteca padrão do Python.

## Licença

MIT. Veja [LICENSE](LICENSE).
