# cltrplusf — module map

For agents: what each module holds, what it imports, and the rules that keep it honest. Grep it
before reading the tree.

## Modules

| Module | Holds | Imports (internal) |
|---|---|---|
| `config` | every setting: chunk budgets, models, ranking depths, Docling options, re-rowing gaps | nothing |
| `printed` | a printed cell as a number (`number`, `is_figure`, `figure_row`) | nothing |
| `chunk` | `Document`, `Table`, `Heading`, `Chunk`, `Inventory`; the chunkers | `config` |
| `corpus` | Docling conversion and its cache (`parse_fingerprint`, `ingest_fingerprint`), rupee fonts, furniture, `load_corpus`; the corpus root from `CLTRPLUSF_HOME` | `config`, `chunk` |
| `line_rows` | a PDF page's words as displayed; Docling's tables re-rowed by printed line | `config`, `printed` |
| `filed` | a filed PDF's words and re-rowed tables, memoised (`load_words_cached`, `load_lines_cached`) | `corpus`, `chunk`, `line_rows`, `printed`, `config` |
| `hits` | `Hit`, `rank_ids` | nothing |
| `embed` | `Embedder`, `LocalEmbedder` | `config` |
| `dense`, `sparse`, `fuse`, `rerank` | the rankers | `config`, `chunk`, `hits`, `embed`, `corpus` (`dense`, for its cache dir) |
| `rank` | `build_ranker`: the methods combined | the rankers |
| `keys` | keyed search over table rows | `rank`, `chunk`, `embed`, `rerank` |
| `testing` | fakes for tests here and in aigent | `corpus`, `embed` |

## Invariants

- Nothing here imports aigent, and nothing calls a hosted model.
- The Docling cache is keyed by the source of the functions that decide a reading; editing one
  forces a ~92-minute re-parse.
- Every setting lives in `config`.

## History

Moved out of aigent on 2026-11-27 with its git history (`aigent.retrieval` search and parsing,
`aigent.facts.printed`, `line_rows`, and the words half of `facts.documents`, now `filed`).
