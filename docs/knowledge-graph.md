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
| `tables.model` | `Piece`, `Cell`, `Row` (label, cells, values, children, total, `checked`), `Table` | nothing |
| `tables.lines` | words into lines of pieces inside a box; dates made whole; bold from the glyphs | `line_rows`, `filed`, `config` |
| `tables.grid` | Docling's columns by its cells' boxes, split where two printed figure columns sit in one; every piece placed | `printed`, `config` |
| `tables.header` | where the body begins (`header_rows`); the label column's edge (`label_right`) | `printed`, `config` |
| `tables.rows` | body lines into rows; a wrapped label joined up, down or around its values (`wrap`) | `header`, `printed`, `config` |
| `tables.nest` | the section tree; totals checked by their sums (`adds_up`, `addends`), the section a total closes chosen by them | `config` |
| `tables.read` | `read_table`, `read_tables`, `keys` | the above, `filed` |
| `testing` | fakes for tests here and in aigent | `corpus`, `embed`, `tables.model` |

## Invariants

- Nothing here imports aigent, and nothing calls a hosted model.
- The Docling cache is keyed by the source of the functions that decide a reading; editing one
  forces a ~92-minute re-parse.
- Every setting lives in `config`.

## How `tables` decides

- **Lines and columns** (2026-11-27, Vedant: "words-first to get the coarse table, then Docling's
  table margins to make the cells correct"): every word in Docling's table box is kept, one row per
  printed line, each piece in the Docling column it overlaps most; a Docling column holding two
  printed figure columns is split at them. On 850 bake-off tables the prototype lost no number
  against Docling V1's 1.42%; TableFormer V2 lost 10.3%, cell matching off 12.1%, Granite Vision
  2.1% on the 8 pages it finished at ~4 minutes a page.
- **Header rows:** the lines above the first value line, less one-phrase section labels; a small
  number is a value only under a row label; a column-number line ("234567") counts only when its
  digits rise by one each, no separator (a test found "1,234" read as column numbers).
- **Wraps:** a lowercase opener, a connective or an open bracket joins lines; a plain label over a
  row at its own indent is that row's first line; a label may wrap around its values.
- **Nesting** (Vedant: index the innermost level; a parent's own rows are a section of their own;
  the layout proposes, arithmetic decides): numbered note titles on top, then indent, bold and
  capitals; a label under a label is its child; a value row with rows indented under it is a
  parent; a total closes the open section whose rows add up to it, marked `checked="sum"`.
- **Scores** (`scripts/table_eval.py`, labels blind, held-out apart): header rows 45/49 tuned,
  29/33 held out; wraps 38/40, 32/36; nesting rows 93.4%, 91.5% (two tables a side unscored, their
  rows now split otherwise than when labelled). Over every born-digital filed PDF: 12,074 tables,
  0 of 580,382 printed numbers lost; 4,073 of 6,814 testable totals add up (59.8%); the rest are
  mostly formula rows (net = gross - depreciation), figures labelled "Total", and lists continued
  from another page.

## History

Moved out of aigent on 2026-11-27 with its git history (`aigent.retrieval` search and parsing,
`aigent.facts.printed`, `line_rows`, and the words half of `facts.documents`, now `filed`).


## Nodes moved from aigent's graph (2026-11-27)

Copied as they stood in aigent's `docs/knowledge-graph.md`, ids renamed to this package (`retrieval.chunk` is `chunk` here, `facts.printed` is `printed`). Their generated `At:` lines are dropped: this file has no generator. History stays, so work is not redone.

#### `line_rows`
- **Is:** module. **A filed PDF's tables re-laid by where their printed words sit**: Docling keeps each table's box, its header cells and its columns of words; the figure columns, the header over them and each body row come from the PDF's own text. `page_words(page)` reads a page's characters and pdfium's text runs, `split_runs` splits each run at the spaces between its characters (a piece boxed by its own, found through a `GRID`-point index; a run none of whose characters lie in it kept whole), each word flagged with whether a space follows it, measured from the crop box (`crop_box`, the media box when there is none); `displayed`/`on_display` place them on the page as displayed by its stated rotation. `layout(item, rows, height)` is what Docling settled: the box, the header (every row above the first `printed.figure_row`, so a row of bare years is header), the body's top, each column's edges as the median of its single-column cells, each header cell's row, column, span and box, and its `text` columns (body cells mostly words, a dash or a cell of figures counting as figures). `line_rows(header, layout, words)` keeps the words in the table's box and below its header, groups them into lines (a word within `VERIFY_LINE_GAP` of a line's height of its middle shares it), joins a word with no space after it to the next within a line's height (`joined`), cuts a run of several figures where its characters fall (`split_figures`), then finds the **figure columns** (`bands`: figures and dashes clustered by right edge, neighbours never sharing a line joined, one on under `VERIFY_BAND_MIN_SHARE` of the figure lines or centred in a column of words dropped, and of two overlapping the one on fewer lines). `grid_of` lays them among Docling's columns of words (one across the left when it placed none); `Grid.place` puts a figure in the column it overlaps, a word in the figure column holding its middle, a word left of every figure in its nearest label column (so a long label's last word stays in it), else the nearest column. `header_rows` lays Docling's header over that grid: a cell of a word column kept there, a cell over one figure column (or spanning several, or with no box) at Docling's column when that maps to one, and a cell Docling merged over several split into `phrases` and `stacks` (a heading over several lines read as one), a stack over one column given to it, top down when several fall in one column (Tata's shared `September 30,` over its column's `2025`), and stacks over several placed by `grouped` (equal blocks of the columns no heading of their own names, else the first each is printed over). `wrapped` joins a label wrapped over lines within `VERIFY_WRAP_GAP` line heights: a label line ending in a joining word (`of`, `and`, `at`, `-`, ...) or followed by one starting in lower case (not an enumerator `a)`/`(ii)`/`9.`, nor `less`/`add`/`of which`), a lower-case or joined line below a row's figures, and two label lines with the figures printed between them; only the label columns left of the figures count, a nil mark in one is no label text, and a line opening an item never joins a row that opened one (`(a)` then `(b)`, `8.` then `9.`), though an item's marker centred on its label's second line still joins. Columns empty throughout are dropped, and spaced separators closed (`17 , 009` to `17,009`). With no figure column found, or text printed up the page (`_upright`), Docling's columns and header are kept and each word goes to the column it overlaps most (`column`).
- **Contract:** `layout` is None for a table split across pages, with no row of two figures, or under two placed columns; `line_rows` is None when no word lies in the body. Words are in points from the displayed page's top-left, as Docling's top-left boxes are. A table's width is its printed columns', not Docling's.
- **Gotchas:** pdfium returns a row of figures in a space-laid table as one run (HDFC Bank's ten-year table), hence the split; an OCR layer prints a word as letters and figures as fragments (`11 ,216.4`), hence the join and the separators. Character-level words with gap rules merged far more cells than runs split at spaces. The page's stated rotation was right on all 7,862 pages with tables, so the check against Docling's figure cells was dropped. Docling's column edges can be only as wide as a column's dashes, so a column is judged a column of words by its cells, not its edges. A wrapped line sits about 2.0 line heights below the one before and a new row about 2.4 (Reliance), so wraps are told by their words, not the gap. ITC prints each year's heading over the last two of its three columns, hence `grouped`'s equal blocks.
- **History:** 2026-11-24: created (Vedant: improve the parsing; every table, not only those Docling merged, for one reading). 17,724 to 18,114 of 38,510 agree; merged figure cells in OCR layers 5,850 to 3,232, totals footing 47% to 56%. 2026-11-25: figure columns, header and wrapped labels from the printed words (Vedant: recreate the original table as closely as possible, after the table pages' top-ten faults): 18,115 to 19,624 of 38,510 agree, 1,529 gained and 20 lost (OCR-layer edge cases: a serial number now its own column, Power Grid's EPS lines run together, a garbled `φ` label); see LOG.md 11-25 for the audit flags. Rotated tables kept on Docling's columns, which read them no better. 2026-11-26: header phrases top down in a column, nil marks out of labels, sibling items kept apart, with `printed`'s braces and note numbers: 20,730 to 20,738 agree, none lost.
- **Decided in:** LOG.md 11-24, 11-26

#### `printed`
- **Is:** module. `is_figure(word)` and `figures_only(cell)`, the one figure test (`FIGURE`, used by `line_rows`, `facts.table_page` and, with `NIL`, the HTML reader; OCR's braces as brackets, `{99)`, and a whole number ending in a point, a note's `1.`, no figure), `MAIN_LINE` and `ENUMERATOR` (`a)`, `(ii)`, `9.`, followed by a space or nothing), the prefixes of printed labels; `number(text)`, a printed figure read to its value, decimal places and whether it is a percentage (OCR's `[555)`, `{99)`, `(12.45}` and `1;331` read as `(555)`, `(99)`, `(12.45)` and `1,331`), with `ZERO`, `NUMERIC_DATE`, `WORDED_DATE` and `YEAR` (a header's year alone, `2025` or `2024*`); `figure_row(row)`, two or more figures not all years, where a table's body begins. Free of the cross-check, so `line_rows` (under `facts.documents`, which `facts.crosscheck` imports) can use it without a cycle.
- **History:** 2026-11-24: moved out of `facts.crosscheck`. 2026-11-25: `figure_row` and `YEAR`, so Tata Motors' `2025 | 2025* | 2024*` line is header. 2026-11-26: braces read as brackets, note numbers no figures, `ENUMERATOR` takes numbered items.
- **Decided in:** LOG.md 11-24, 11-26

#### `chunk`
- **Is:** module. `Document` (with the `Table`s and `Heading`s the parser found, each a span of its text; a `Table` keeps its cells row by row and its `header_rows`), `Chunk`, `Inventory`, and the five splitters: fixed, fixed-with-overlap, by sentence, by heading, and **by element**.
- **Contract:** `Inventory.containing` resolves a labelled quote to the ids that hold it.
- **Invariants:** Imports `config` and nothing else internal (checked: §3 rules).
- **History:** **By element** (2026-10-20).
- **Decided in:** LOG.md 10-20

#### `embed`
- **Is:** module. The `Embedder` protocol and `LocalEmbedder`, `sentence-transformers` on MPS, loaded at `LOCAL_MODEL_DTYPE` with the query prefix `query_prefix_of` gives.
- **Contract:** The one part of aigent that thinks with someone else's weights, and the only capability module that spends nothing at all.
- **History:** Dtype and per-model prefix (2026-10-21).
- **Decided in:** LOG.md 10-21

#### `dense`
- **Is:** module. `DenseIndex`: ids, a normalised matrix, and brute-force cosine search. No approximate index, no database, exact answers.
- **Contract:** **Keeps a copy on disk**: `build_cached` stores the vectors in `corpus/.cache/`, keyed by everything that produced them, so an inventory embedded once is read back in 0.01s rather than embedded again in 48s. **Vectors are cached per text**: one store per embedder, `vectors-{model}-{key}.npz`, keyed by each text's hash, shared by every index, so an index embeds only text no index has embedded before (a vector depends on its text alone: batched against one at a time on 64 chunks, cosine ≥ 0.9999999).
- **History:** Disk copy (2026-09-28). Per-text vectors (2026-10-21).
- **Decided in:** LOG.md 09-28, 10-21

#### `corpus`
- **Is:** module. Annual report PDFs into `Document`s: **Docling per page**, its text, headings and tables in reading order, normalised, furniture stripped from text but never from a heading or a table, joined while recording page offsets and each table's and heading's span (`assembled`). Plus the opt-in disk cache, which stores the tables and headings too.
- **Contract:** The only module that touches the parser. Docling labels page headers and footers as furniture, which `iterate_items` leaves out.
- **Gotchas:** Editing its parse-step code forces a full re-parse (~92 minutes).
- **History:** Docling since 2026-10-20, Vedant; it was `pypdf`. **Why Docling** (2026-10-20, measured on the three eval reports, free): the retrieval labels' quotes found in the text, pypdf 54/54 with tables scattered a cell a line, pdfplumber's plain text 14/54 (it reads a printed line straight across two columns), pdfminer's layout analysis with pdfplumber's table finder 48/54 (columns merged into one flow on side-by-side profiles, and the finder took Bajaj's page frames for tables and missed its borderless statements), **Docling 54/54** rendered by us, with 1,364 tables read as grids with their header rows; about 1.3 s a page with OCR off on the Mac's GPU.
- **Decided in:** LOG.md 10-20

#### `sparse`
- **Is:** module. `SparseIndex`: BM25 as an inverted index over the same `Inventory` the dense index holds. The lexical half of hybrid retrieval, written out rather than imported.

#### `fuse`
- **Is:** module. Reciprocal rank fusion: several rankings of the same ids into one, using ranks because the scores are not commensurable.

#### `rerank`
- **Is:** module. A `Reranker` protocol and a local cross-encoder.
- **Contract:** The expensive second stage: reads query and passage *together*, so it cannot be precomputed and never runs over the corpus.

#### `hits`
- **Is:** module. `Hit` and `rank_ids`: what every index, ranker, fusion and reranker returns.
- **Invariants:** Its own module so none of them imports another to get the type.

#### `rank`
- **Is:** module. **The rankers.** `build_ranker(method, indexes)` turns any of the six method names into a `Ranker`, whose one method is `rank(query, k, doc_id=)`.
- **Contract:** `DenseRanker` and `SparseRanker` each wrap one index; `HybridRanker` holds the two and fuses them; `Reranked` wraps any of the three. The indexes are built once in `Indexes` and shared.
- **Invariants:** The eval ranks through these and so does anything else (invariant 21).

#### `keys`
- **Is:** module. **Search keys and the keyed search.** Every `by_element` chunk is indexed under several short texts that point back to it: its own text, one key per labelled table row (section path, basis, row label, column years; **no figures**), one per table piece listing its rows, and one per sentence of a text chunk of two or more.
- **Contract:** `keyed_search(name, documents, cache=)` builds the chunks, the keys and their `Indexes`, ranks keys by `SEARCH_METHOD`'s base read to `KEY_DEPTH`, returns each chunk once at its best key (`ParentRanker`), and has the reranker read whole chunks. Every production search uses it, under its own index name.
- **History:** 2026-10-21, Vedant: created; no figures in keys (Vedant: "the numbers dont have a place there"). **Measured 2026-10-21 on the 88 questions, `bge-large` + `bge-reranker-v2-m3`, each in its own report:** chunks only hit@5 0.909 (tables 0.82); with row and table keys 0.909 (0.85); with sentence keys too 0.920 (0.85), MRR 0.743 → 0.764; before reranking 0.761 → 0.841, tables 0.59 → 0.74. The stronger the reranker, the less the keys add (MiniLM on the full index 0.818, `bge-reranker-base` 0.886).
- **Decided in:** LOG.md 10-21

#### `config.EMBED_MODEL`
- **Is:** constant. `BAAI/bge-large-en-v1.5` — 1024 dimensions, 512 tokens, 335M parameters, runs on MPS, free.
- **History:** Since 2026-10-21 (Vedant; `bge-small-en-v1.5` before). **Screened 2026-10-21 on the 88 questions, `by_element`, each in its own report, hybrid hit@5:** `bge-small` 0.636 (tables 0.47), `bge-large` 0.773 (0.62), `gte-modernbert-base` 0.602 (0.47; its half-precision load checked against full: cosine ≥ 0.9994, same top 5s), `Qwen3-Embedding-0.6B` 0.773 (0.68, prose 0.83, 2.5× slower to embed). Only models that run no downloaded code were screened.
- **Decided in:** LOG.md 10-21

#### `config.EMBED_LOG_EVERY`
- **Is:** constant. 1,024: texts `DenseIndex.build` embeds between progress lines.

#### `config.EMBED_SAVE_EVERY`
- **Is:** constant. 4,096: texts `DenseIndex.build_cached` embeds between writes of its store, about three minutes of `bge-large` on the Mac; a stopped build loses at most the batch in progress.
- **History:** 2026-10-22, Vedant: a run stopped at 91% on 10-21 had saved nothing.
- **Decided in:** LOG.md 10-21, 10-22

#### `config.EMBED_QUERY_PREFIXES`
- **Is:** dict. The query prefix of each model that does not declare one in its `prompts`, from its card, keyed by model; `""` for one that wants none.
- **Invariants:** **A model on neither is refused** (`query_prefix_of`).
- **Gotchas:** A query embedded without its prefix, or with another model's, still ranks plausibly, just worse, with nothing to say so.
- **History:** `EMBED_QUERY_PREFIX` used to be every undeclared model's fallback and so handed BGE's instruction to any other model.

#### `config.LOCAL_MODEL_DTYPE`
- **Is:** constant. `float32`: what the local embedder and reranker load at, **whatever their files declare**.
- **Gotchas:** `transformers` loads a checkpoint at its declared precision: Qwen3-Embedding declares bfloat16, whose normalised vectors missed unit length by ~0.3% and were refused by `DenseIndex`; gte-modernbert declares float16, which passed that check unnoticed.
- **History:** 2026-10-21: created.
- **Decided in:** LOG.md 10-21

#### `config.TOP_K`
- **Is:** constant. `5`. How many chunks a retriever returns, and therefore how many an answer can cite.

#### `config.BM25_K1`
- **Is:** constants `BM25_K1` / `BM25_B`: `1.5` and `0.75`, where the literature settled. `K1` is where term frequency saturates, `B` how hard a long chunk is penalised.
- **Invariants:** Not tuned here — tuning them on the eval set is how you overfit a retriever to 54 questions.

#### `config.FUSE_DEPTH`
- **Is:** constant. `100`. How deep each ranker's list goes into fusion.
- **Contract:** Fusing the whole corpus adds runtime and tail noise; cutting at `TOP_K` would throw away the rank-20-lexically, rank-4-densely chunk that fusion exists to promote.

#### `config.RRF_K`
- **Is:** constant. `60`. **The constant that decides what fusion means.**
- **Contract:** At 0, rank 1 scores 1.0 against rank 2's 0.5, so whichever ranker shouted first wins. At 60 the two are 1/61 and 1/62, so agreement across rankers outweighs a single first place.
- **History:** Measured consequence: on the original question set that property *cost* four rows, because BM25 had them at rank 1 and dense had them nowhere.

#### `config.KEY_DEPTH`
- **Is:** constant. 400: how many keys a keyed search reads from each of its rankers, enough to reach `RERANK_CANDIDATES` distinct chunks when one chunk owns many keys.

#### `config.SEARCH_METHOD`
- **Is:** constant. `hybrid+rerank`, the method to rank with outside the eval, and the method `keyed_search` ranks the keys by.
- **Contract:** A test holds it to `METHODS`.
- **Invariants:** **Chosen on the paraphrased set, not the original**: a caller's queries are written by a user or a model, never from the passages. The banner's finding, applied.
- **History:** On questions not written from the passages `hybrid+rerank` was the best of six (hit@5 0.481 against `bm25+rerank`'s 0.426), where on the original set it came second. Since 2026-10-21 it ranks the keys.
- **Decided in:** LOG.md 10-21

#### `config.PAGE_SEPARATOR`
- **Is:** constant. `\n\n`. What joins two pages into one document text, so a page break reads as a paragraph break to every splitter.

#### `config.DOCLING_OCR`
- **Is:** constants `DOCLING_OCR` / `DOCLING_DEVICE` / `DOCLING_QUEUE_MAX_SIZE`, and `PDF_RUPEE_KEYS`. Docling's settings: OCR off, the reports carrying a text layer; the device `auto`, Docling's pick of what the machine has, MPS here and CPU in CI.
- **Contract:** `DOCLING_OCR` and `DOCLING_DEVICE` feed the cache fingerprint, with Docling's version. **`DOCLING_QUEUE_MAX_SIZE`** (8) does not: it bounds the pages held between Docling's pipeline stages, memory only, set by `corpus._queue_capped` before each parse. **`PDF_RUPEE_KEYS`**: the fonts that draw ₹ on a keyboard key, by family, and the keys each draws it on — `` ` `` for `Rupee`, `RupeeForadian` and `IndianRupee`, `CDEHIJKL` for `ITFRupee` — every one seen before an amount across the 15 reports, and also fingerprinted.
- **Gotchas:** With OCR on, 17 s a page against 0.9 to 1.3 s off. Foradian is a full font: TATAMOTORS-FY25 sets chart labels and digits in it, ITC-FY24 its nil dashes, HDFCBANK-FY24 a printed "R 23,768", so nothing beyond the listed keys maps.
- **History:** 2026-10-20: created; **`PDF_RUPEE_KEYS`** (2026-10-20); `DOCLING_QUEUE_MAX_SIZE` (2026-11-08: Docling's 100 pages in flight per stage grew one process to 17 GB on a 16 GB Mac and froze it; 8 held Power Grid FY25 at 9 GB).
- **Decided in:** LOG.md 10-20

#### `chunk.Document`
- **Is:** frozen dataclass. `doc_id`, `text`, `source`, `page_starts`.
- **Contract:** `page_of(offset)` turns a character offset back into a 1-indexed page by bisect, which is what lets a retrieved passage be cited rather than only quoted.

#### `chunk.Chunk`
- **Is:** frozen dataclass. `id`, `text`, `doc_id`, `ordinal`, `start`, `page`, `heading`.
- **Contract:** `citation` renders `doc · p.N · heading`.

#### `chunk.Inventory`
- **Is:** frozen dataclass. Every chunk of every document under **one** strategy, plus `by_id`.
- **Contract:** All three splitters must drop fragments under `CHUNK_MIN_CHARS` (a marooned heading, a surviving page number) and number the survivors contiguously — so a heading has to travel with its span rather than its ordinal, or one dropped fragment shifts every heading after it by one. `build` refuses two documents sharing a `doc_id`.
- **Gotchas:** `name` is load-bearing: ids are positional, so two inventories built by different splitters use the same ids for different text. Two documents sharing a `doc_id` would collide: `by_id` would keep whichever came last, and every label naming one would resolve to the wrong text with nothing raised. Same shape as the `setdefault` near-miss in the ticker directory a week earlier.

#### `chunk.squeeze`
- **Is:** function. The comparison two texts meet in: whitespace collapsed, case folded, curly quotes and dashes folded to ASCII, and **whitespace before punctuation closed up**.
- **Contract:** Leniency is safe *here* and nowhere else — it is the matching function, not the text a citation shows.
- **History:** Public since 2026-09-18, when `questions.verify` became a second caller. Each rule answers a real corpus artefact: a hand-typed label writes `ITC's` where the PDF holds `ITC’s`, and extraction leaves `lawyers .` and `52 %` on 10% of passages.
- **Decided in:** LOG.md 09-18

#### `chunk.Inventory.containing`
- **Is:** method. A labelled quote → the ids that hold it, whitespace-, typography- and case-insensitively.
- **Contract:** `squeeze` folds curly quotes and dashes to ASCII before comparing, because a label is typed by hand and a PDF is not: the corpus holds `ITC’s` and `—`, a label holds `ITC's` and `-`, and without the fold a correct label silently resolves to nothing. An empty list is a finding, not a bug — the quote straddles a boundary, so no single chunk can answer, and the strategy has capped its own recall before the embedder runs.
- **Invariants:** **This is how a label survives a re-chunk** and the Week 2 instance of invariant 13: the dataset names the sentence that answers the question, code resolves it to ids in *this* inventory, and the model is never asked where the answer lives.

#### `chunk.fixed`
- **Is:** factory. A sliding window, stepping `size - overlap`.
- **Contract:** `overlap=0` is the plain split; the roadmap's "fixed with overlap" is the same function with a second number.
- **Invariants:** **Does not snap to word boundaries, on purpose**: it is the baseline the other three are measured against, and a baseline quietly improved flatters everything compared to it.

#### `chunk.sentences`
- **Is:** function. Sentence spans by regex with an abbreviation guard.
- **Contract:** **Only `_ABBREVIATION_LOOKBACK` (64) characters before a break are examined.** `_ABBREVIATIONS` is annual-report specific — `Rs.` and `Cr.` open every other line of one, and breaking on them shears a figure off its unit. Single initials (`J. K. Sharma`) are guarded too.
- **Gotchas:** Not a parser and does not pretend to be; that is an argument for measuring it against the others, not for importing one.
- **History:** Slicing the whole prefix to read one word made this quadratic and cost 46.9s on this corpus against 0.05s now — it was the single most expensive thing in the pipeline, more than parsing 1,148 PDF pages, and it looked like a caching problem until it was profiled.

#### `chunk.by_sentence`
- **Is:** factory. Packs whole sentences to `max_chars`, stepping back `overlap_sentences`.
- **Contract:** No chunk ends mid-clause, which is what makes a passage quotable. **A span holding no sentence break is cut on the character budget** (`emit_capped`). **`whole_sentences=True`** (`by_element` only) splits such a span at its line breaks instead, packing whole lines to the budget and keeping a line past it whole: in Docling's text a line ends a paragraph or list item, and the spans it is for are lists and address blocks without a full stop (193 of 60,417 sentences over 1,000 characters across 12 reports, up to 5,347), whose longest line is 2,086 characters, under the embedder's 512 tokens.
- **Gotchas:** The embedder reads 512 tokens, so text past that is not indexed while its chunk goes on claiming to contain it — an uncut mega-chunk is not a fairer comparison, it is a chunk that lies.
- **History:** `emit_capped` (2026-09-18), reversing the earlier rule that such a span became one chunk however long it ran. The earlier rule was argued from the comparison with `fixed` and was wrong about the corpus: financial tables carry almost no sentence-ending punctuation, so 172 chunks came out over 2,000 characters holding 11.5% of the corpus, the largest of them 14,947 characters with seven breaks in it. Cutting took truncated chunks from 185 to 47 and recall@5 from 0.581 to 0.609. **`whole_sentences=True`** (2026-10-22).
- **Decided in:** LOG.md 09-18, 10-22

#### `chunk.headings`
- **Is:** function. Heading detection over text whose markup extraction destroyed.
- **Contract:** Three signals: short, does not end like a sentence, and either numbered or mostly capitalised.

#### `chunk.by_heading`
- **Is:** factory. One chunk per section, sub-split by sentence when a section runs long; every piece keeps its heading.
- **Contract:** **Degrades to `by_sentence` when no headings are found**, which is the honest behaviour — a structural splitter cannot find structure that ingestion destroyed, and a plausible chunk count would hide a broken ingest.
- **History:** **Kept but not run as an eval variant, decided 2026-09-18.** It is dominated on both axes: 85.3% of sentences survive it against `by_sentence`'s 100%, while it produces the most chunks of any strategy (7,506, averaging 538 characters) — the signature of heading detection firing on kerning damage (`ST ANDALONE FINANCIAL ST A TEMENTS`) and fragmenting sections. Worth improving later, not worth a column now.
- **Decided in:** LOG.md 09-18

#### `chunk.by_element`
- **Is:** factory. **A chunk starts at every heading and every table the parser found.** Budgets `ELEMENT_TABLE_CHARS` 1,000 and `ELEMENT_TEXT_CHARS` 1,000.
- **Contract:** Text runs pack by whole sentence up to `ELEMENT_TEXT_CHARS` (`by_sentence(whole_sentences=True)`), each piece keeping its section heading (a heading alone, with its table next, is no chunk). A table is one chunk opened by `table_label`, `[Table · {doc} p.{page} · {section} · {basis} · {scale} · columns: {years}]`: the scale copied verbatim from its top rows or its section above and followed by the multiplier it names as a plain number (`(H In Crore) = ×10000000`, `multiplier_of`, "lakh crore" read before "crore"), so the model copies the multiplier rather than converting a word, and not as a power of ten, so a scale that is none can be added as a row; `check_call` still reads only powers of ten; the phrase stays, for its exceptions such as "except per share data" and because `check_call` reads the scale as a word. The basis is the last `consolidated`/`standalone` its section names, nothing made up when none is stated. Failing its top rows and its section, the scale is any its page states. **A text chunk opens with a line too** (`text_label`), `[{doc} p.{page} · {section} · {scale} = ×{multiplier}]`, when a scale stated above it in its section or on its page governs its amounts and it names none itself (no "in crore" phrase, no scale word after a number); 2,173 of 14,127 text chunks over the training reports. `_SCALE` reads a currency sign (₹, Rs, INR, US$, $) then the scale word, inside brackets, an amount between them not a scale. **The scale is copied tidy**: a bracketed phrase with "in" to its closing bracket, exceptions kept ("(C in millions, except per share data)", "(Amount in ₹ crore)"), a bracketed currency and scale ("(₹ crore)"), or an unbracketed "₹ in Million" / "In Crore" ending at its word, so a label no longer carries a header row's stray digits and dates ("025 ₹ in Million As at March 31, 2024"). Past `ELEMENT_TABLE_CHARS` a table splits at rows (a rendered row is one line; a row past the budget stays whole in its own piece), every piece repeating the label, the column-header rows and **the section row it continues under** (rows Docling marks `row_section`, such as "Quoted:", kept as `Table.sections`; one matched by its first cell, so a row with figures is never repeated). **The basis falls back to the page's running header** (`Document.running`: Docling's `page_header` furniture and the lines stripped as furniture, such as "Notes to standalone financial statements … (Contd.)"); text labels carry the basis too. **Labels name the section path** (`section_path`): Docling gives every heading level 1, so depth comes from numbering — lettered (`a)`) and roman (`ii.`) subsections nest under a numbered note ("16. Segment reporting › a) Treasury › i. Digital banking"), `i`/`v`/`x` read as a letter after `h`/`u`/`w`, and any other heading starts afresh. The label is what lets a scaled figure be checked against its own chunk (`underhood.tooldata.labels.check_call` reads the scale there); underhood's `check_call` reads the `= ×N` (`_MULTIPLIER`).
- **Gotchas:** Docling's reading order can put a page's "(C in millions …)" line after the table, hence the whole-page lookup. The median citation barely moves with smaller budgets: most chunks were already under the budget, so citing a row needs a unit inside the chunk.
- **History:** 2026-10-20, Vedant, approaches 2 to 4 of the literature: element chunking, whole tables split only at rows, a context line. Multiplier as a plain number: Vedant, 2026-10-20. **Measured 2026-10-20 on the 47 figures v4's first full teacher run dropped for an unproven scale**: provable from one chunk under pypdf `by_sentence` 18, Docling `by_sentence` 32, `by_element` with table labels 34, with text labels 37, with the whole-page lookup 39; of the 8 left, 4 are the teacher's wrong scale or arithmetic, rightly refused, 1 a dash read as 0, and 3 with no scale the labels read: Wipro's two AOC-1 forms, whose only scale is the footnote "Value is less than One Million Rupees" at the form's end, and an HDFC segment table whose page does say `(₹ crore)`, which `_SCALE` missed for want of "in" (HDFC writes it so about 105 times a report); `_SCALE` reads it since 2026-10-20. Tidy scale (2026-10-20, later): over the nine training reports 5,271 chunks name a multiplier, 49 more than before; none of them is blind to `check_call`'s unscaled-money check, where 1,008 were. Inheriting a scale from the section before was examined and not taken: for the AOC-1 tables the nearest is the Notes', a different section, right only by coincidence. Hybrid + rerank retrieval unchanged by the labels (hit@5 0.889, recall@5 0.881, MRR 0.745). Section rows carried (2026-10-20). Running-header basis: on BAJAJ-AUTO-FY25 table labels with a basis rose from 29 to 166 of 265, on HDFCBANK-FY24 from 78 to 84 of 398, whose running headers name sections, not a basis. Section path: a first version that also nested unnumbered headings and treated "Notes to …" and the auditor's report as parts gave wrong parents throughout (a never-closing auditor's report over the notes, "Notes to Investments" over notes 42 and 43, prose's numbered points adopting headings), so it was narrowed. The 44 v4 trajectories dropped on 2026-10-19 for a scale their chunk did not name were what labels fix. **Budgets 1,000 and 1,000 since 2026-10-22** (Vedant, the first step toward citing a row or a sentence, not a whole table; was 2,000 for tables and 1,200 for text). Measured on the 88 questions, keyed search, each in its own report: tables at 1,000 alone left hit@5 at 0.920 and cut a search's top 5 from a median 1,693 Qwen3 tokens (90th 3,091) to 1,432 (2,190) and the largest cited chunk from 1,130 to 753; tables at 600 lost a table question (0.909) for a 90th of 1,615 and a largest of 442. Both at 1,000: hit@5 0.909, recall@5 0.903, MRR 0.760, tables 29/34, prose 51/54; median 1,352 tokens a search (90th 2,197), cited chunk median 220, max 753; 7,712 chunks, 34,416 keys. The prose question lost, `rq-003`, cites the same unchanged chunk, now 6th behind smaller pieces of the ITCMAARS prose.
- **Decided in:** LOG.md 10-19, 10-20, 10-22

#### `embed.Embedder`
- **Is:** Protocol. `name`, `dimensions`, `embed_documents`, `embed_query`.
- **Contract:** A protocol so a test can hand the dense index a deterministic fake without importing torch, and so a hosted provider drops in later as a second column in the same table.

#### `embed.query_prefix_of`
- **Is:** function. The prefix a model's queries take: the one it declares, else `EMBED_QUERY_PREFIXES`'s, else a ValueError naming the model.
- **History:** 2026-10-21: created.
- **Decided in:** LOG.md 10-21

#### `embed.LocalEmbedder`
- **Is:** class. `sentence-transformers` on MPS when available, else CPU. Returns L2-normalised float32.
- **Contract:** Heavy imports are **deferred into `__init__`** — importing torch costs seconds, and no test of the chunker or the harness should pay that. Weights load at `LOCAL_MODEL_DTYPE`.
- **History:** Dtype (2026-10-21).
- **Decided in:** LOG.md 10-21

#### `embed.LocalEmbedder.embed_query`
- **Is:** method. Prefixes the model's own query prefix (`query_prefix_of`); `embed_documents` does not.
- **Gotchas:** The asymmetry is the model's training, not a preference.

#### `embed.LocalEmbedder.count_truncated`
- **Is:** method. How many chunks the 512-token limit actually cut.
- **Gotchas:** Text past the limit is not down-weighted or summarised — it is **not read**, while the chunk goes on claiming to contain it. Run it once over a new inventory; a chunking strategy whose recall looks bad should be checked here before it is blamed.

#### `hits.Hit`
- **Is:** frozen dataclass. `chunk_id`, `score`.
- **Gotchas:** **What the score means is the ranker's own** — cosine, BM25, a fused rank, a cross-encoder logit — so scores compare only within one ranking.

#### `dense.DenseIndex`
- **Is:** frozen dataclass. Ids and a normalised matrix, aligned row for row.
- **Contract:** Holds no chunks — `Inventory` does — so the two rebuild independently.

#### `dense.DenseIndex.build`
- **Is:** classmethod.
- **Contract:** Refuses two shapes rather than trusting them: a vector count that does not match the inventory (a misalignment returns real ids attached to another chunk's vector — every score plausible, every citation wrong, nothing raised), and un-normalised rows, which would make cosine wrong by a different factor per chunk. Both checks live in `_checked`, which `load` goes through too. **Embeds `EMBED_LOG_EVERY` (1,024) texts at a time, logging each slice** to `aigent.retrieval.dense` (count, percent, model, elapsed), since a first build with `bge-large` runs tens of minutes.
- **Gotchas:** The slicing lives here, not in `embed_documents`, whose source is part of the cache key.
- **History:** Slice logging (2026-10-21).
- **Decided in:** LOG.md 10-21

#### `dense.DenseIndex.search`
- **Is:** method. `matrix @ query`, then a **stable** sort.
- **Contract:** Ties break by position in the inventory: arbitrary, but not free to wobble between two identical runs — the same rule that turned thinking off for evals, applied to the one place NumPy would otherwise decide it.

#### `dense.DenseIndex.build_cached`
- **Is:** classmethod. `build`, embedding only the texts the embedder's store lacks.
- **Contract:** Logs how many texts it reused and how many it embeds, **writes the store every `EMBED_SAVE_EVERY` new texts and at the end** (`embedded`'s `save` callback, each write whole through `.partial`, so a stopped build keeps every batch it saved and the next embeds only the rest), and serves each row by its text's key, so order, duplicates and other indexes' texts cannot misalign it. A missing or damaged store is started afresh, never raised on.
- **History:** Per-text store (2026-10-21; a whole-index file per inventory before, so one changed chunk re-embedded all of them and two indexes holding the same report each embedded it). Periodic writes (2026-10-22).
- **Decided in:** LOG.md 10-21, 10-22

#### `dense.store_file`
- **Is:** functions `store_file` / `text_key` / `read_store` / `write_store`. The store is `vectors-{model}-{key}.npz`, the key a hash of the embedder's name, dimensions and **the source of its `embed_documents`**, so another model or an edit to how a passage is embedded opens a new store.
- **Contract:** `write_store` writes it whole or not at all and deletes that model's older versions. A text's key is its SHA-256 (32 hex digits; a test holds 5,000 near-identical texts to 5,000 keys). `read_store` refuses keys and rows that disagree and a key held twice.
- **History:** On 2026-10-21 the eval's two whole-index caches were moved in after each text was proven identical by recomputing the old file's hash: 39,031 vectors became 29,623, chunks being their own keys.
- **Decided in:** LOG.md 10-21

#### `hits.rank_ids`
- **Is:** function. Hits → the ranked list of ids the retrieval graders read.

#### `corpus.read_pages`
- **Is:** function. Raw extracted text, one string per page: each page's `Element`s joined, a table one row a line. `read_elements` is the pages as elements.
- **Contract:** `convert` is **the only function that touches the parser**, handed the PDF through `rupees_decoded`: each font `config.PDF_RUPEE_KEYS` names gets a ToUnicode reading its keys as ₹ — an existing map edited entry by entry (`_rupee_entries`, only entries already reading as a key), a WinAnsi font without one given a map built from its encoding and `/Differences` (`_simple_font_map`), any other encoding untouched — in memory, the path passed on unchanged when no font needed it. **Every font a page's resources reach, form XObjects included** (`_fonts_of`). **Then `captions_restored`**: with `generate_parsed_pages` on, Docling's own printed lines are kept, and each line inside a table's box, in none of its cells and level with or above its first row (`_stray_caption`), becomes a caption *of that table* (`table.captions`), not loose text; one already its caption is not added again. `elements_of` prints a table's captions (Docling's own, such as "Table 6: Standalone Profit and Loss Statement", and the restored) as its first rows, counted as header rows, and its footnotes as its last rows (`_notes`; `_captions` is the parse step's own copy, kept apart so rendering can change without re-parsing), so they ride in its chunk, repeat on every split and are read for its scale. Then a `DocumentConverter` built once (`_converter`, OCR `DOCLING_OCR` off, device `DOCLING_DEVICE`); `elements_of` turns a `DoclingDocument` into elements, text, heading (`SectionHeaderItem`, `TitleItem`) or table, text drawn inside a picture included (`traverse_pictures`: ITC's "6.50 per share (Interim)" dividend sits in one), a page with nothing on it kept as an empty page (invariant 19); `table_rows` gives a cell spanning columns once, in its first; `header_rows` counts the leading rows Docling marked as column headers.
- **Invariants:** Tests run on a fake converter over `DoclingDocument`s built in code (`tests/retrieval/conftest.py`), so CI never downloads Docling's models.
- **Gotchas:** Every report sets ₹ in a legacy font that draws it on a keyboard key, so the text layer said `` ` ``, `C`, `H`… and no parser could read ₹ — hence `rupees_decoded`. WIPRO-FY25 draws its statements' "(C in millions …)" from XObjects holding 8 ITFRupee font objects no page lists, which a page-level walk left as "C" 273 times. Docling's table model often draws a table's box around its caption and scale line, and its cell matching drops what falls in no cell — "(₹ crore)" over an HDFC investments table, column-group headers such as "Gross block" — hence `captions_restored`.
- **History:** `rupees_decoded` (2026-10-20). Measured over the 15 reports by pypdf text before and after: about 19,000 characters changed, every one a listed key to ₹. `_fonts_of` (2026-10-20): an exhaustive audit of every run in a rupee font over the 15 reports, and of the text for stand-ins, found nothing else (HDFC's three "C"s and one Sun Pharma backtick in Lato are printed as such). After the fix the other 14 reports decode to identical text. `captions_restored` (2026-10-20): on BAJAJ-AUTO-FY24: 29 lines restored, rendered ₹ 415 → 422 of pypdf's 426; the rest are "(₹" pieces dropped from inside a header cell whose scale words survive, which every label on those pages still reads as ×10000000. `traverse_pictures` (2026-10-20).
- **Decided in:** LOG.md 10-20

#### `corpus.normalise`
- **Is:** function. One page, cleaned of what extraction did to it and nothing else: NFKC (ligatures, thin and non-breaking spaces, `CO₂`→`CO2`), tabs to spaces, runs of spaces collapsed, a word hyphenated across a line break rejoined, blank-line runs collapsed.
- **Invariants:** **It deliberately does not fold curly quotes or dashes** — those are what the document says, not an artefact, so they stay in the citation and `_squeeze` handles them at match time.

#### `corpus._skeleton`
- **Is:** function. A line with its digits masked.
- **Contract:** Small, and the reason the furniture rule works at all: `\d+` collapses a run to one `#`, so two printings of one header match and page 9 matches page 147.

#### `corpus.strip_furniture`
- **Is:** function. Running headers, footers and page numbers, by repetition among **edge lines with digits masked**.
- **Contract:** Candidacy is decided at the edges — `(Rs. in crore)` repeats on 86 ITC pages mid-table and is content — but a skeleton that qualifies is then removed wherever it appears, since extraction sometimes drops a footer mid-stream. Counted over a **set per page**, so a header printed twice on one page is one page, not two. A page that was nothing but furniture stays, empty: dropping it would renumber every citation after it. **`furniture` finds the lines and `assembled` strips them from text elements only.**
- **Gotchas:** Known cost — Reliance's `CONSOLIDATED FINANCIAL STATEMENTS` runs on 52 pages and goes with them, so `by_heading` loses that section label. With Docling a statement page opens with its heading and its table's scale row, `(H In Crore)`, the very edge lines that repeat on a hundred Bajaj pages, so stripping them from tables would delete every scale.
- **History:** Measured on the corpus: 326 lines out of ITC, 434 out of Reliance, 1,778 out of Tata Motors. **Since 2026-10-20** text elements only.
- **Decided in:** LOG.md 10-20

#### `corpus.to_document`
- **Is:** function. Joins pages with `PAGE_SEPARATOR`, recording the offset each starts at.
- **Invariants:** `page_starts` must be built **while joining the normalised pages**.
- **Gotchas:** Computed from the raw ones it is wrong by however much normalisation removed, which shows up as citations drifting a page late in long documents and as nothing at all in a short test.

#### `corpus.load_pdf`
- **Is:** function. `read_elements`, then `assembled`: normalise each element, strip furniture from text, join, record the spans.
- **Gotchas:** `doc_id` defaults to the filename stem, so renaming a file renames every chunk in it.

#### `corpus.cache_file`
- **Is:** function. Where a PDF's extracted text is kept, named `{doc_id}-{pdf digest}-{ingest fingerprint}`.
- **Contract:** **Both halves are load-bearing.** The bytes catch a company republishing a report; the fingerprint — a hash of `read_pages`, `normalise`, `_skeleton`, `strip_furniture`, `to_document` and the constants they read — catches an edit to the ingestion code. There is no version number to remember to bump.
- **Gotchas:** A filename-keyed or bytes-only cache would serve text the current code never produced, and would do it silently.

#### `corpus.load_pdf_cached`
- **Is:** function. `load_pdf` memoised on disk in `corpus/.cache/` (git-ignored). Reached only through `load_corpus(cache=True)`, never by default.
- **Contract:** Written to a `.partial` and moved into place, so an interrupted run leaves nothing readable behind; a corrupt or truncated entry is deleted and re-parsed rather than raised on; superseded entries for the same document are swept. **Two layers**, `parse_fingerprint()` naming the lower one's key: beneath the rendered document, `parse_cached` keeps Docling's own reading of the PDF (`{doc}.{digest}-{parse fingerprint}.docling`, Docling's JSON) keyed by `_PARSE_FINGERPRINT` alone — the converter, `rupees_decoded` and its helpers, Docling's version, `DOCLING_OCR`, `PDF_RUPEE_KEYS` — so a change to rendering (`elements_of` down to `assembled`) re-renders from the kept parse in seconds rather than re-parsing for hours; `_INGEST_FINGERPRINT` hashes the parse fingerprint with the rendering code. Same `.partial`, truncation and sweep rules for both layers. `parse_cached` caps Docling's queue (`_queue_capped`, outside the fingerprint) before converting.
- **Gotchas:** **The cache keeps one entry per `doc_id`**, sweeping the rest, so two different PDFs under one name evict each other; hence `facts.documents.doc_id_of`. **Cold 27.8s, warm 0.04s** (pypdf; Docling's cold parse is about 8 minutes a report on MPS).
- **History:** **Two layers since 2026-10-20.**
- **Decided in:** LOG.md 10-20

#### `corpus.load_corpus`
- **Is:** function. Every PDF directly in a directory, in filename order.
- **Contract:** **Directly, not recursively**: the fine-tune's training reports live in `corpus/training/` (`TRAINING_DIR`), listed in `evals/reference/training-manifest.json` (`TRAINING_MANIFEST`), so they never enter retrieval, `search_reports` or an eval; a test fails if a report in that folder is loaded. **`cache=False` by default, opt-in only**: reading the PDFs is always correct, while a cache is correct until it is not, and a stale hit is wrong *quietly* — the one failure mode the keying works hard to prevent but cannot rule out. 28 seconds is a price worth paying unless a caller has a reason, and then the caller says so at the call site where it can be seen. A test pins the default, so it cannot drift back. **Raises on an empty directory** rather than returning nothing — an empty corpus scores zero recall on every question and reads exactly like a bad retriever. **`doc_ids`** loads exactly the reports named and raises on one that is missing, so a typo cannot shrink the corpus; every published eval passes `FY25_REPORTS` (`ITC-FY25`, `RELIANCE-FY25`, `TATAMOTORS-FY25`), and only the capstone reads all six.
- **History:** Not recursive (2026-10-10). Opt-in cache (decided 2026-09-18). **`doc_ids`** (2026-10-12), since the FY24 reports joined `corpus/`.
- **Decided in:** LOG.md 09-18, 10-10, 10-12

#### `sparse.tokenise`
- **Is:** function. Lowercased words and numbers, with `34,000` and `52.3` surviving as one token — splitting them hands the digits back to the same blur BM25 exists to fix.
- **Contract:** No stemming, no stopword list: `idf` already discounts a term that appears everywhere, which is what a stopword list approximates.

#### `sparse.SparseIndex`
- **Is:** frozen dataclass. An inverted index over an `Inventory`: `postings` maps a term to the rows holding it, so scoring touches only chunks sharing a term.
- **Contract:** Ids are the inventory's ids, which is what makes a hit here fusable with a `DenseIndex` hit (invariant 17). `score` returns a **sparse dict on purpose** — an absent row is *no match*, distinguishable from *matched badly* without a threshold, and `search` therefore drops zero-scorers rather than padding out to k. The `+1` in the idf keeps a term present in every chunk at a small positive weight; without it, a chunk would rank higher for **not** containing a query word.

#### `fuse.reciprocal_rank_fusion`
- **Is:** function. Ranks only, never scores.
- **Contract:** Cosine lives in [-1, 1] and BM25 is unbounded and corpus-dependent, so averaging them is meaningless and normalising them is a per-corpus tuning problem. Ties break by first appearance so two identical runs cannot disagree — the same rule `DenseIndex.search` follows.
- **Gotchas:** The fused number is a position, not a similarity; do not read it as one.

#### `rerank.Reranker`
- **Is:** Protocol. `name` and `scores(query, passages)`.
- **Contract:** A protocol for the reason `Embedder` is one: a test substitutes a fake ordering without importing torch.

#### `rerank.LocalReranker`
- **Is:** class. A `sentence-transformers` CrossEncoder, heavy imports deferred into `__init__`, weights at `LOCAL_MODEL_DTYPE`.
- **Gotchas:** Returns unbounded logits — not probabilities, not comparable across models; only their order within one call means anything.
- **History:** Dtype (2026-10-21).
- **Decided in:** LOG.md 10-21

#### `keys.build_keys`
- **Is:** function. The keys of an inventory's chunks, with each key's parent and kind (`Keyed`).
- **Contract:** A row key points at the piece of a split table that prints it, else the first piece; a row whose label is a placeholder (`row_label`: no cell of words with two letters) gets none. Key ids are `{doc}#k{n}`, the inventory `{name}-keys`.

#### `keys.table_context`
- **Is:** function. A table label's section path and basis: report and page, scale (`chunk.scale_of`) and column years dropped.

#### `keys.ParentRanker`
- **Is:** dataclass. Wraps a ranker over keys: reads `KEY_DEPTH` of them, returns each parent chunk once at its best key's place and score.
- **Contract:** A table with five matching rows scores as its best row.

#### `keys.keyed_search`
- **Is:** function. Chunks by element, builds keys and `Indexes` over them (cached as `{name}-keys`), and composes `SEARCH_METHOD`: its base over keys in a `ParentRanker`, then `Reranked` over the **chunks** when the method ends `+rerank`.
- **Contract:** Returns the chunk inventory and the ranker.

#### `rerank.rerank`
- **Is:** function. Reorder candidates and keep k.
- **Contract:** Takes the candidate *texts* rather than an `Inventory`, so the module stays testable against plain strings. Ties break by the first stage's order, so the cheap ranker settles what the expensive one is indifferent about.
- **Invariants:** **It cannot retrieve**: a chunk outside the candidate set cannot be reordered into it, so this moves MRR and precision and moves recall only as far as `RERANK_CANDIDATES` does. A test asserts exactly that.

#### `rank.METHODS`
- **Is:** tuple. The six retrieval arms: three bases (`dense`, `bm25`, `hybrid`) each with and without `+rerank`.
- **Contract:** A grid rather than a list, so the table separates what **reach** buys from what **ordering** buys. All six rank one `by_sentence` inventory, so they share labels and are six tasks of **one** run — unlike the chunking strategies, which disagree about the labels and need `combine`.
- **History:** Lived in `evaluate` until 2026-09-21.
- **Decided in:** LOG.md 09-21

#### `rank.Ranker`
- **Is:** Protocol. One method: `rank(query, k, *, doc_id=None) -> list[Hit]`.
- **Contract:** A protocol, as `Embedder` and `Reranker` are, because the rankers share an interface and no code.

#### `rank.Indexes`
- **Is:** frozen dataclass. The inventory, the embedder, the `DenseIndex` and the `SparseIndex`, built once and handed to every ranker.
- **Contract:** `cache=True` takes the dense half from `DenseIndex.build_cached`; off by default, as the corpus cache is, and `agent_tasks` and `evaluate` pass their `--cache` through.
- **Gotchas:** Embedding the corpus is the slow part — **~65s** on the M4 — so building it per ranker would cost the eval six times over.
- **History:** `--cache` passed through (2026-09-28).
- **Decided in:** LOG.md 09-28

#### `rank.DenseRanker`
- **Is:** frozen dataclasses `DenseRanker` / `SparseRanker`. One index each.
- **Gotchas:** `DenseRanker` embeds the query itself, which means the eval's four dense-based methods each embed a question the eval used to embed once; identical vectors, a few seconds, and the rerun proved it.

#### `rank.HybridRanker`
- **Is:** frozen dataclass. Holds a dense and a sparse ranker, reads each to `FUSE_DEPTH` rather than to `k`, and fuses by reciprocal rank — dense first, since fusion breaks ties by first appearance.

#### `rank.Reranked`
- **Is:** frozen dataclass. Wraps **any** ranker: takes its best `candidates`, has the cross-encoder reorder them, keeps `k`.
- **Contract:** This is what makes `+rerank` a suffix on any base rather than three more kinds of ranker. The base decides what is reachable; the reranker only decides order within it.

#### `rank.scoped`
- **Is:** function. **A scope ranks every chunk, then drops the other reports** — rather than filtering the global top k, which returns nothing for a report that ranks low overall and reads as "the report does not say".
- **Contract:** Exact rather than approximate, because a matrix-vector product and a BM25 pass over 5,193 chunks are cheap. Idf stays corpus-wide under a scope. Without a scope it is exactly the ranking the eval measured, and a test pins that. A scope (`Scope`) is one report, a set of them (the capstone's 'ITC, both years') or None for all.
- **History:** Sets of reports since 2026-10-12.
- **Decided in:** LOG.md 10-12

#### `rank.build_ranker`
- **Is:** function. Method name → ranker.
- **Contract:** `"bm25+rerank"` is `Reranked(SparseRanker(...))`, `"hybrid"` is `HybridRanker(DenseRanker(...), SparseRanker(...))`, and a test asserts all six compositions as written-out strings. A `+rerank` method loads the local cross-encoder unless handed one; the eval hands one, so it loads once.

#### `chunk.context_block`
- **Is:** function. The passages, one XML element each, tagged with the chunk id the model must cite it by.
- **Contract:** One element per passage rather than a concatenated blob: a citation that names no passage cannot be checked against the label, and an unfalsifiable citation is worse than none because it reads as evidence.
- **History:** Moved from `answer` on 2026-09-21, and lives beside `Chunk.citation`, which it prints.
- **Decided in:** LOG.md 09-21

#### `tests.conftest.KeywordReranker`
- **Is:** fixture class. The shared fake cross-encoder: score a passage by how many query words it holds.
- **Contract:** Crude, and crucially a **different ordering** from `BagOfWordsEmbedder`'s, so a rerank test can prove the second stage moved something.

#### `tests.test_chunk`
- **Is:** test module, free. The four splitters as tables over the text they must survive.
- **Contract:** The abbreviation table is the load-bearing one — `Rs.` opens every other sentence in an annual report, and a splitter that breaks on it shears the figure off its unit, which surfaces as a retrieval failure three layers later. Then: the fixed window's mid-word cut asserted rather than apologised for, headings recognised in text that lost its markup, ordinals staying contiguous across a dropped fragment, a page number derived from an offset, and the two ends of quote resolution — a quote found in the chunk that holds it, and a quote **split across a boundary resolving to nothing**, which is the finding that a chunking strategy has capped its own recall.

#### `tests.test_corpus`
- **Is:** test module, free. The corpus, 24 tests.
- **Contract:** `normalise` is an eleven-row table of extraction artefacts, each row naming the one thing it fixes. `build_pdf` writes a real uncompressed PDF in the test — byte offsets, xref and all — so `load_pdf` and `read_pages` are covered end to end without a binary in the repo. The load-bearing test is the page-offset one: every citation downstream names a page, and offsets taken before normalisation are wrong in a way nothing else in the pipeline notices. Then the cache, tested for the ways it could go *silently* wrong rather than loudly: a second load that does not re-parse (counted, not timed), a republished report invalidating on bytes, an ingestion-code change invalidating on fingerprint, a truncated entry re-parsed instead of raised on, superseded entries swept, and **the default pinned as no-cache** so an opt-in convenience cannot quietly become the norm. Every guard mutation-checked.
- **History:** **The rupee sign** (2026-10-20): `build_pdf` draws a part of a line in braces in a second font, with its own encoding and optional ToUnicode, and a fourteen-row table holds what becomes ₹ and what must not — each rupee font's keys, a key moved by `/Differences`, an existing map changing only its key; Foradian's R, letters, digits and dashes, ITFRupee's other keys, a non-rupee font, a family merely containing "Rupee", a non-WinAnsi encoding all unchanged — plus `Picture` pieces in `conftest.docling`, text inside one read where it stands; grids laid out on the page (`box`, a caption `band`, an empty `margin`) and a caption Docling found, with a nine-row table of printed lines a table takes as its leading header rows or leaves — a scale line in the band, several lines top to bottom, one level with the first row beside its cells taken; text beside lower rows, a line in a cell, one outside the box, a table without cell boxes left — and a found caption made the first row and not restored twice; running headers as a page's context and never its text; a footnote as a table's last row and section rows counted past its caption; the cache keeping `running` and `sections`; and in `test_chunk` the basis from the running header and the section's first, the section path in a label, an eight-row table of heading sequences and their paths, a text label's basis, and a split table repeating the section row each piece continues under; the parse layer of the cache — a rendering change reading the kept parse, a parsing change re-parsing, a truncated parse re-parsed, one parse per document — a rupee font inside a form XObject repaired too, and a form that draws itself walked once; plus the written map checked by code (pypdf's extractor decodes `/Differences` before the map, which hides a missing entry), a PDF with no rupee font passed on as its path, and a decoded one keeping its file name.
- **Decided in:** LOG.md 10-20

#### `tests.test_sparse`
- **Is:** test module, free. BM25's two jobs a dense retriever cannot do.
- **Contract:** The rare-token test is the reason the module exists — `SACE` beating a chunk that merely shares `the`, `company` and `year` is idf doing the work. The no-match test is what keeps a fused ranking honest: a chunk sharing no query term is absent, not ranked last. Plus a tokeniser table where the grouped-figure rows (`34,000`, `52.3`) are the whole argument for having a lexical ranker.

#### `tests.test_fuse`
- **Is:** test module, free. Arithmetic over positions.
- **Contract:** The damping test is load-bearing and exact: same inputs, `damping=0` lets a single first place win, `damping=60` lets presence in both rankings win. It also records what RRF does **not** promise — given equal rank sums it prefers the lopsided pair, since `1/(k+r)` is convex, so (1,3) beats (2,2).
- **History:** That was a wrong assumption in the first draft of this file, caught by the test.

#### `tests.test_rerank`
- **Is:** test module, free. Against `conftest.KeywordReranker`, which deliberately **disagrees** with `BagOfWordsEmbedder` — a fake reranker that agreed with the fake retriever could not show reranking changed anything.
- **Contract:** The last test is the one that matters: reranking cannot retrieve what the first stage missed, without which someone reads a rerank column as if it fixed misses.

#### `tests.test_keys`
- **Is:** test module, free. The keys over Docling documents built in code.
- **Contract:** Every chunk its own key; a table's number-free row keys and one table key, none for placeholder or figure-only rows; row keys homed to the piece of a split table that prints them; sentence keys under the heading without repeating it, none for a one-sentence chunk; `table_context`, `row_label`, `column_headers`/`years_in` as tables; `ParentRanker`'s dedupe, depth and scope; `keyed_search` with and without a reranker over the fakes, chunk ids out and whole chunks reranked. Every guard mutation-checked.
- **History:** 2026-10-21: created.
- **Decided in:** LOG.md 10-21

#### `tests.test_embed`
- **Is:** test module, free.
- **Contract:** `query_prefix_of` as a table (declared, configured, an empty declaration, a model wanting none), an unknown model refused, the configured `EMBED_MODEL` listed, and both local models loaded at `LOCAL_MODEL_DTYPE` against fake sentence-transformers classes.
- **History:** 2026-10-21: created.
- **Decided in:** LOG.md 10-21

#### `tests.test_rank`
- **Is:** test module, free. Three tables.
- **Contract:** **Each method builds the composition its name says**, asserted as a written-out string (`"Reranked(HybridRanker(DenseRanker, SparseRanker))"`), so the design is readable from the test. **A scoped ranking stays in its report**, a row per method, over a corpus built so the *other* report ranks higher overall; the dense and bm25 rows fail if scoping degrades to filtering the global top k (checked by mutation — the hybrid and rerank rows cannot, since their depth covers a four-chunk corpus). **An unscoped ranking is exactly what the eval measured**, one row per base plus one for the rerank wrapper. Then an unknown method refused, `SEARCH_METHOD` held to `METHODS`, and `Indexes` reusing stored vectors only when asked, two rows.

#### `tests.test_dense`
- **Is:** test module, free. The dense index's arithmetic and its two guards, against the fake.
- **Contract:** Ranking, k larger and smaller than the inventory, an empty index, ties breaking identically across five runs, and the two builds it refuses: un-normalised vectors, and a matrix one row short the way a batching bug drops the last batch. The store: only unseen text embedded (a changed, added or reordered chunk, another model, other embedding code, as exact counts), indexes sharing text sharing vectors, a repeated text embedded once, a damaged store (truncated, empty, foreign, misaligned, a key twice) started afresh, one file per model written whole, its log line, and near-identical texts never sharing a key; every guard mutation-checked.
- **Gotchas:** Whether a *real* model ranks the right chunk first is a question for an eval over labelled data — confusing the two produces a suite that passes while retrieval is broken.
- **History:** **The copy on disk** (2026-09-28): a round trip; a loaded file held to the two guards, two rows; a second build served without embedding, counted rather than timed; a five-row table of what must rebuild the cache — nothing changed, a chunk's text changed under the same id, a chunk added, another model, another `embed_documents` — whose second row is the case a cache keyed on ids alone serves stale, as the scratch one was; four damaged files rebuilt rather than raised on; and one file kept per strategy. Checked by mutation: keying on ids alone, leaving the code out of the key, trusting a loaded file's ids, skipping the sweep, handing `np.savez` a path and loading without the guards each failed the row written for it. Since 2026-10-21 the store tests.
- **Decided in:** LOG.md 09-28, 10-21
