# Should a 5-Person Bank Team Adopt Google's Open Knowledge Format (OKF)? An Evaluation and Implementation Guide

## TL;DR

- **Adopt OKF's vendor-neutral core as your frontmatter contract — but only a subset, and on your own terms.** OKF is genuinely open (Apache 2.0), trivially simple (a directory of Markdown files + YAML frontmatter where the only required field is `type`), and runs 100% locally with zero GCP dependency for reading/writing. It is a near-perfect match for a Markdown+Git "second brain," so writing OKF-compatible docs from day one costs almost nothing and buys you future interoperability.
- **Ignore everything GCP-attached, which is exactly what you already decided.** The enrichment agent is BigQuery/Gemini-bound and useless to you; the only portable reference tool, the static HTML visualizer, generates a graph viewer but ships inside the heavyweight Python package and pulls its JS libraries (Cytoscape.js + marked) from a CDN — so it is NOT a clean offline Obsidian replacement without modification.
- **Don't adopt OKF "wholesale" — it's a v0.1 draft (published June 12, 2026), Google is currently its only major speaker, and it deliberately omits a controlled type taxonomy, typed relationships, and any validator.** Design your own schema as a strict superset of OKF's required surface (`type` + the five recommended fields), keep your folders and controlled tag vocabulary, and you remain convertible to any future OKF tool at zero migration cost.

## Key Findings

**What OKF actually is.** The Open Knowledge Format is an open specification published by Google Cloud's Data Cloud team — Sam McVeety (Tech Lead, Data Analytics, Google Cloud) and Amir Hormati (Tech Lead, BigQuery, Google Cloud), per the Google Cloud Blog announcement of June 12, 2026 — under the Apache 2.0 license, in the `GoogleCloudPlatform/knowledge-catalog` repo at `okf/SPEC.md`. It formalizes the "LLM-wiki" pattern from Andrej Karpathy's April 2026 gist (which has 5,000+ stars; as explainx.ai put it on June 14, 2026, "Karpathy's LLM Wiki gist predicted this shape; Google formalized the interoperability layer"). An OKF "bundle" is just a directory tree of UTF-8 Markdown files. Each file is one "concept"; the file's path (minus `.md`) is its "concept ID" (so `processos/pipeline-fail-x.md` → ID `processos/pipeline-fail-x`). The spec is 451 lines / 14.7 KB and explicitly states: "There is no schema registry, no central authority, and no required tooling. If you can `cat` a file, you can read OKF; if you can `git clone` a repo, you can ship it."

**The exact frontmatter schema (§4.1).** Every concept file is YAML frontmatter (delimited by `---`) + a Markdown body. Fields:

- `type` — **REQUIRED**. A short string identifying the kind of concept. Used for routing/filtering/presentation. NOT centrally registered. Example values given in the spec: `BigQuery Table`, `BigQuery Dataset`, `API Endpoint`, `Metric`, `Playbook`, `Reference`.
- `title` — _recommended, optional_. Human display name; consumers may derive from filename if omitted.
- `description` — _recommended, optional_. Single-sentence summary; used in index generation, search snippets, previews.
- `resource` — _recommended, optional_. A canonical URI for the underlying asset; absent for abstract concepts.
- `tags` — _recommended, optional_. A YAML list of short strings.
- `timestamp` — _recommended, optional_. ISO 8601 datetime of last meaningful change.
- **Extensions**: producers MAY add any additional keys; consumers SHOULD preserve unknown keys and MUST NOT reject documents with unrecognized fields.

There is no separate ID field (the path IS the ID), and no versioning field on concepts — but a bundle MAY declare `okf_version: "0.1"` in the frontmatter of a root `index.md` (the only place an `index.md` is allowed frontmatter).

**Types are NOT an enum.** This is a critical and often-misreported point: OKF does **not** define a fixed taxonomy of concept types. The spec lists examples (`BigQuery Table`, `API Endpoint`, `Metric`, `Playbook`, `Reference`) but a stated non-goal of the spec is "Defining a fixed taxonomy of concept types." Producers invent their own type strings; consumers must tolerate unknown ones. So your team picks its own types (e.g., `Runbook`, `Permission Request`, `Internal Library`, `BFF Pattern`, `Frontend Component`).

**File/folder structure & linking (§3, §5).** The directory layout is domain-independent — "producers organize concepts however makes sense." Two reserved filenames carry meaning at any directory level and MUST NOT be used for concepts: `index.md` (a directory listing for "progressive disclosure," no frontmatter except the optional version declaration at root) and `log.md` (a chronological, newest-first changelog with `## YYYY-MM-DD` headings and bold action markers like `**Update**`, `**Creation**`, `**Deprecation**`). Cross-references use **standard Markdown links, not wikilinks**. Bundle-relative absolute links (`[customers](/tables/customers.md)`) are recommended over relative links because they survive file moves. Links are untyped — "the specific kind of relationship... is conveyed by the surrounding prose, not by the link itself." Broken links are explicitly permitted (they may represent not-yet-written knowledge). A conventional `# Citations` section (numbered) holds external sources.

**Conformance is trivially easy (§9).** A bundle is conformant if: (1) every non-reserved `.md` file has parseable YAML frontmatter, (2) every frontmatter block has a non-empty `type`, and (3) `index.md`/`log.md` follow their structure when present. Consumers MUST NOT reject a bundle for missing optional fields, unknown types, unknown keys, broken links, or missing `index.md`. One nuance worth knowing: a reviewer (Marc Bara, Medium) found that Google's own reference parser is stricter than the spec and rejects files missing `type`, `title`, `description`, and `timestamp` — so even the "required surface" isn't fully settled at v0.1.

**Licensing — safe for a bank.** Everything in the repo (spec + reference implementations) is Apache 2.0. The format itself is an open specification with no SDK, account, or runtime required. The repo carries the standard Google "not an official Google product" disclaimer, which (as one analyst noted) Google puts on most of its open-source sample repos and means the _code_ is unsupported, not that the _format_ is unofficial. For a Brazilian bank, Apache 2.0 (permissive, patent grant, no copyleft) is about as safe as it gets, and because the format is pure files there is no dependency to vet — nothing leaves your network.

**Vendor-neutrality reality check.** The format is genuinely portable. The _tooling_ splits cleanly into a "portable layer" (spec + visualizer) and an "enterprise layer" (the BigQuery enrichment agent + Google Cloud Knowledge Catalog ingestion + the `kcmd` catalog-sync CLI). The three reference implementations:

- (a) **Enrichment agent** — GCP-bound. Walks a BigQuery dataset, drafts one OKF doc per table, then a second LLM pass crawls docs to enrich. Built on Google's Agent Development Kit (ADK) + Gemini; requires `gcloud auth`, a billing project, and a Gemini/Vertex API key. (Amir Hormati committed it on June 11, 2026, commit `ee67a5c`, per PPC Land's timeline.) **Ignore entirely** (matches your decision).
- (b) **Static HTML visualizer** — the `visualize` subcommand of the same `enrichment_agent` Python package. Renders any local bundle into a single self-contained HTML graph view. Crucially: the _generation_ step reads only local files (no BigQuery, no Gemini, no credentials), but it lives inside the same heavyweight package (Python 3.13 + ADK/google-cloud deps), and the **output HTML loads Cytoscape.js and marked from a CDN** — so it is not truly offline without manual editing to inline those libraries. There is no documented `--no-web`/offline flag for `visualize`.
- (c) **Three sample bundles** (GA4 e-commerce, Stack Overflow, Bitcoin) committed to the repo as living conformant examples, each with a committed `viz.html`.

**Maturity & trajectory.** Published June 12, 2026; explicitly labeled "v0.1... a starting point, not a finished standard." The repo is young but attracting attention fast — 3,000 stars and 187 forks per the GoogleCloudPlatform/knowledge-catalog GitHub page header ("Star 3k" / "Fork 187"), with open issues into the high-70s, all within days of launch. Google made itself the first "speaker": per the announcement, "We have also updated Google Cloud's Knowledge Catalog to be able to ingest Open Knowledge Format and serve it to our agents" (the reference catalog demo bundle is a GA4 sample of 17 markdown files published via the `kcmd` tool under `toolbox/mdcode/demo`). No other catalog vendor has announced OKF support yet — and notably Collibra and Snowflake are backing a _different_ semantic-interop effort, the Open Semantic Interchange (OSI), "an open source initiative created by Snowflake" (Collibra press release, Dec 9, 2025), whose working group now includes AWS, BlackRock, JPMC, dbt Labs, Salesforce, Informatica and Starburst. The open design questions Google itself flags for future OKF versions: contradiction/merge semantics, typed relationships, trust tiers, richer/faceted tagging, and a registered type vocabulary. There is no official validator/linter or JSON Schema in the repo — validation is spec-prose only; community sites (openknowledgeformat.com, okf.md) advertise validators but those are third-party and early.

**OKF vs. Karpathy LLM-wiki vs. ad-hoc Markdown+YAML.** Karpathy's pattern (raw sources → an LLM-maintained `wiki/` of Markdown → a `CLAUDE.md`/`AGENTS.md` schema, with `index.md` + `log.md`) is the _intellectual parent_ of OKF — but it is a personal convention with no fixed field contract, and it commonly uses `[[wikilinks]]`. OKF is that same pattern _specified_: it pins down one required field (`type`), reserves two filenames (`index.md`, `log.md`), and mandates standard Markdown links instead of wikilinks. Versus rolling your own ad-hoc frontmatter: adopting OKF's conventions costs you almost nothing (you were going to put `title`/`tags`/`timestamp` in frontmatter anyway) and buys a _stable contract_ — the day an OKF-aware tool, agent, or auditor appears, your vault is already readable. The cost is mild rigidity (the `type`-on-every-file rule; standard links instead of the nicer `[[wikilinks]]` if you prefer Obsidian's autocomplete) and the risk of designing around a spec that may change or stall.

**The skeptical take.** Critics (Marc Bara on Medium, the Hacker News thread) make a fair point: OKF v0.1 standardizes _structural_ interoperability (a container — folder layout, one required field, two filenames) but not _semantic_ interoperability (shared vocabulary of types and relationships). Two fully-conformant bundles can share no common type vocabulary, so an agent built for one may get little from another. "A standard, or just a folder?" is a legitimate framing. For comparison, Bara notes "AGENTS.md, released by OpenAI in August 2025 and now used by more than 60,000 projects, is the nearest convention by shape." OKF is also, realistically, a soft vendor play: Google rebranded Dataplex to "Knowledge Catalog," published a format that conveniently flows into that product, and is currently the only major adopter. For your purposes this risk is largely irrelevant: you are not betting your architecture on cross-org interoperability or on Google's catalog — you are using OKF as a sensible, well-thought-out convention for files you already own. If OKF is abandoned tomorrow, your Markdown files are unaffected.

## Details

### What an OKF entry looks like for your team

A realistic "pipeline failure" runbook as a conformant OKF concept file, e.g. `processos/pipeline-falha-ingestao-tedw.md`:

```markdown
---
type: Runbook
title: Falha de ingestão na pipeline TEDW
description: Triagem e correção quando a pipeline TEDW falha com erro de permissão no bucket.
resource: https://git.intranet.banco/dados/pipeline-tedw
tags: [pipeline, ingestao, permissoes, on-call]
timestamp: 2026-06-15T14:30:00Z
---

# Sintoma

A pipeline `tedw-ingestao` falha na etapa de escrita com `AccessDenied`. Ver a
[biblioteca interna de auth](/libs-internas/auth-gcs-wrapper.md).

# Causa raiz

Rotação de credencial da service account derruba o acesso ao bucket. Relacionado
ao [processo de solicitação de acesso](/acessos/solicitar-acesso-bucket.md).

# Passos

1. Verificar validade da credencial no cofre interno.
2. Reabrir chamado no [fluxo de tickets de suporte](/processos/abrir-ticket-suporte.md).
3. Reprocessar a janela com o runbook de backfill.

# Citations

[1] [Postmortem INC-4821 (wiki interna)](https://wiki.intranet.banco/inc-4821)
```

A "permission request" entry, `acessos/solicitar-acesso-bucket.md`:

```markdown
---
type: Permission Request
title: Solicitar acesso a bucket de dados
description: Procedimento e aprovadores para conceder acesso de escrita a um bucket interno.
tags: [acessos, permissoes, bucket]
timestamp: 2026-05-30T09:00:00Z
---

# Quando usar

Quando uma service account ou usuário precisa de escrita em um bucket gerenciado
pelo time de dados.

# Aprovadores

...
```

Note: no `resource` field on the second example (it's an abstract process, not a physical asset) — fully legal under the spec.

### How your planned structure maps onto OKF

Your chosen design maps almost 1:1:

- **Folders (`processos`, `libs-internas`, `frontend`, `bff`, `acessos`)** → OKF subdirectories. No change needed; OKF imposes no folder taxonomy. Optionally add an `index.md` per folder for agent "progressive disclosure."
- **Atomic one-problem-per-file Markdown** → exactly OKF's "one concept = one file" model. Perfect alignment.
- **Controlled tag vocabulary** → OKF's `tags` field. OKF does NOT define a tag taxonomy or a tag-aggregation file format (the spec says producers synthesize tag views at consumption time by scanning frontmatter), so your controlled vocabulary lives in your own `CLAUDE.md`/schema doc, not in OKF — which is fine and recommended.

Where you must _adapt_ (small):

1. Add a `type` field to every file (it's the one hard requirement). Define your own type set: e.g., `Runbook`, `Process`, `Permission Request`, `Internal Library`, `Frontend Component`, `BFF Pattern`, `Reference`.
2. If you were planning `[[wikilinks]]` (Obsidian-style), switch cross-references to standard Markdown links with bundle-relative paths (`/libs-internas/x.md`) to be OKF-conformant. (You can keep wikilinks too; they just won't be OKF-portable.)
3. Adopt the reserved `index.md` and `log.md` filenames for those purposes only.
4. If you want strict conformance with Google's _reference parser_ (stricter than the spec), always populate `type`, `title`, `description`, and `timestamp` — good hygiene anyway.

### Can your AI agent skill read/write OKF natively?

Yes, with zero special tooling. OKF is just Markdown + YAML, and an agent with filesystem access (Claude Code, Copilot, Kiro) reads and writes it natively — exactly how the Karpathy pattern and `CLAUDE.md` runbooks already work. Your `CLAUDE.md` skill simply encodes the conventions: "every new doc gets `type` + `title` + `description` + `tags` + `timestamp`; cross-link with `/path.md` links; update `index.md` and prepend to `log.md` on each change; use the controlled tag vocabulary below." There is **no required validator** — and importantly, **no official OKF validator/linter or JSON Schema exists** in Google's repo. Validation is prose-only in the spec. If you want enforcement, you write a ~30-line local script (Python `pyyaml` + `pathlib`, or a `ripgrep`/`awk` check) that asserts each non-reserved `.md` has frontmatter with a non-empty `type` against your controlled type/tag lists. Community validators (openknowledgeformat.com, okf.md) exist but are third-party, early, and — for a bank that bars un-homologated tools — best avoided in favor of your own tiny in-repo checker run in CI.

### Local-only architecture (no GCP)

Everything you planned works unchanged on OKF:

- **Authoring/consumption**: Claude Code / Copilot / Kiro read & write `.md` files directly.
- **Versioning**: Git in your org repo (the spec recommends git as the preferred bundle distribution — history, diffs, blame, PR review for knowledge).
- **Search**: `ripgrep` over the tree for literal/regex; or a local **SQLite FTS5** index for ranked full-text (BM25) — both operate directly on the source files, no service. The FTS5 path is well-trodden for Markdown knowledge bases and stays entirely local. Your `type`/`tags` frontmatter is grep-/FTS-filterable for faceted queries.
- **Browsing**: GitHub renders the Markdown natively in your org repo; for a graph view, see below.
- **Validation (optional)**: a tiny local conformance script in CI.

No BigQuery, no Knowledge Catalog, no `kcmd`, no Ollama/RAG, no network egress. This is the "portable layer" Google itself describes as working "standalone, no GCP required."

### The static HTML viewer: good fit or not?

Partially. The reference visualizer produces a single self-contained HTML graph viewer (force-directed concept graph, type-colored nodes, search, type filter, backlinks, rendered Markdown bodies). Attractive in principle and genuinely local at _generation_ time. But two caveats matter for a locked-down bank:

1. It ships _inside_ the `enrichment_agent` Python package (Python 3.13 + Google ADK/google-cloud dependencies), so installing it drags in the same heavyweight, GCP-oriented dependency tree you want to avoid — even though `visualize` itself never calls BigQuery/Gemini.
2. The generated HTML **loads Cytoscape.js and marked from a CDN**, i.e., it makes outbound network calls at view time. That violates "nothing leaves the network / runs offline" unless you manually edit the HTML to inline those libraries.

**Verdict**: it is not a clean Obsidian replacement for you out of the box. Better options: (a) use GitHub's native Markdown rendering in your repo for day-to-day browsing; (b) if you want a graph/backlink view, Obsidian pointed at the repo folder works on plain Markdown (note: Obsidian's graph is nicest with `[[wikilinks]]`, which trade off against OKF's standard-link conformance — pick one, or let your agent maintain both); (c) if you want the OKF viewer specifically, have your agent generate a _self-contained_ HTML with the JS inlined (no CDN) so it runs fully offline — a small, one-time ask. Given your "no un-homologated plugins" constraint, the GitHub-render + ripgrep/FTS5 + agent path is the cleanest.

### Migration path

Because OKF is a _superset-compatible_ convention rather than a framework, the "write OKF from day one vs. roll your own then convert" dilemma mostly dissolves. The conversion cost between an ad-hoc frontmatter scheme and OKF is low (a published Substack case study showed an agent converting an 18-page wiki to OKF conformance — renaming `created`/`updated` to `timestamp`, adding `type`/`description`, moving sources to a `# Citations` section, and replacing every `[[wikilink]]` with a standard Markdown link — in a single agent session). So either order is safe. The recommended hedge: **design your own schema now as a strict superset of OKF's required surface** so you're conformant by construction and never owe a migration.

## Recommendations

**Adopt a subset of OKF as your schema baseline now — do not adopt it wholesale, and do not ignore it.** Concretely:

1. **Make your frontmatter OKF-conformant from day one.** Require `type` on every file; always also fill `title`, `description`, `tags`, `timestamp` (matches Google's stricter reference parser and is good hygiene). Use `resource` only where a doc points at a real asset. This is the entire "cost" of OKF and it's near-zero.
2. **Keep your own folder taxonomy and controlled tag vocabulary** in your `CLAUDE.md`/`SCHEMA.md`. OKF doesn't govern these; you should. Define your own `type` enum there (e.g., `Runbook`, `Process`, `Permission Request`, `Internal Library`, `Frontend Component`, `BFF Pattern`, `Reference`).
3. **Use standard Markdown bundle-relative links** (`/processos/x.md`), reserve `index.md` and `log.md`, and have the agent maintain both on every change. Decide explicitly whether you also want `[[wikilinks]]` for Obsidian ergonomics (if so, let the agent keep both in sync).
4. **Build a ~30-line local conformance check** (Python or ripgrep/awk) and run it in CI/pre-commit. Do not depend on community validators. This gives you the "stable contract" benefit with no external dependency.
5. **Ignore the entire enterprise layer** (BigQuery enrichment agent, Knowledge Catalog ingestion, `kcmd`) — already your decision, and correct.
6. **For browsing, default to GitHub render + ripgrep/SQLite FTS5.** Treat the OKF HTML viewer as optional; if used, regenerate it with JS inlined so it's truly offline, or just open the folder in Obsidian.

**Benchmarks that would change this recommendation:**

- _Upgrade to deeper OKF adoption_ if/when: (a) OKF reaches ≥v1.0 with a stable required-field set and a registered type/relationship vocabulary; (b) a second major, non-Google vendor (e.g., Collibra, Databricks, or an Obsidian/IDE plugin you can homologate) ships native OKF support; or (c) an official, dependency-light, offline validator/linter appears in the repo.
- _Reconsider and stay purely ad-hoc_ if: OKF shows no commits or community traction over the next 2–3 quarters (a sign it's stalling), in which case treat its conventions as merely "one sensible schema among many" — which costs you nothing since your files are already plain Markdown.
- _Re-evaluate the viewer_ if a standalone, offline, no-CDN OKF renderer (or a homologated Obsidian plugin) becomes available.

## Caveats

- **OKF is a v0.1 draft, only days old at the time the source material was published.** Required fields, type vocabulary, and relationship semantics may change. Treating it as a frozen standard is premature; treating its v0.1 core as a sensible convention is safe.
- **"Vendor-neutral" applies to the format, not the tooling.** The only shipped tools are a GCP-bound enrichment agent and a viewer that (a) lives in a GCP-flavored Python package and (b) calls a CDN at view time. Neither is a turnkey local tool for you.
- **No semantic interoperability yet.** Conformance guarantees structure, not shared meaning; two conformant bundles needn't share a type vocabulary. The interoperability promise is currently mostly potential, with Google as the only major adopter.
- **Name collision**: "OKF" also denotes the unrelated Open Knowledge Foundation and an unrelated supply-chain spec (OKF-SCIS) — don't conflate them when searching internally.
- **Stats are fast-moving and snapshot-dependent** (stars/forks/issues were climbing daily right after launch; the 3k-star/187-fork figure is a mid-June 2026 GitHub header snapshot, not a fixed value). Exact commit and contributor counts could not be confirmed from primary sources.
- This analysis is built from the OKF `SPEC.md`, the official Google Cloud announcement, the repo `README`, and secondary technical coverage; some repo internals (exact `pyproject.toml` dependencies) could not be verified directly because GitHub blocks automated fetching.
