# cltrplusf

Find anything in a company's filings. cltrplusf reads annual reports and results PDFs with Docling,
keeps every printed number, re-rows tables by their printed lines, chunks the text and tables, and
searches them: BM25, dense embeddings, fusion and a cross-encoder reranker, plus keyed search over
table rows.

It calls no hosted model and imports nothing from [aigent](https://github.com/vedantdeo/aigent),
which depends on it, asks the questions and grades the answers.

## Layout

| Module | What it does |
|---|---|
| `corpus` | PDFs through Docling, cached by a fingerprint of the parse code; rupee fonts decoded; furniture dropped |
| `printed` | A printed cell as a number: brackets, dashes, separators, percentages |
| `line_rows`, `filed` | A PDF's words as displayed; Docling's tables re-rowed by their printed lines |
| `chunk` | Documents into chunks: by sentence, heading or element |
| `embed`, `dense`, `sparse`, `fuse`, `rerank`, `rank`, `hits` | The rankers and how they combine |
| `keys` | Keyed search over table rows and sections |
| `testing` | Fakes for tests: Docling documents built in code, an embedder and a reranker |

## Where the corpus lives

cltrplusf reads `corpus/` under the directory named by `CLTRPLUSF_HOME`, or under the working
directory when it is unset. aigent sets it to its own checkout.

## Checks

```sh
uv sync
uv run ruff check . && uv run pyright && uv run pytest -q
```
