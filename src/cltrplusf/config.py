"""Settings for parsing, chunking and search: models, budgets of characters, and ranking depths.

Values only. The corpus location is not a setting: a caller names it in `CLTRPLUSF_HOME`.
"""

from __future__ import annotations

# Its 1024 dimensions and 512-token limit are read off the model, not set here.
EMBED_MODEL = "BAAI/bge-large-en-v1.5"

EMBED_BATCH = 64

EMBED_LOG_EVERY = 1024  # texts embedded between progress lines

EMBED_SAVE_EVERY = 4096  # texts a cached build embeds between writes of its store

# Query prefixes for models that do not declare one in `prompts`, from each model card; a model
# neither declares nor lists here is refused. "" is a model that wants none.
EMBED_QUERY_PREFIXES: dict[str, str] = {
    "Alibaba-NLP/gte-modernbert-base": "",
    "BAAI/bge-large-en-v1.5": "Represent this sentence for searching relevant passages: ",
    "BAAI/bge-small-en-v1.5": "Represent this sentence for searching relevant passages: ",
}

# Local models load at this precision, whatever their files declare.
LOCAL_MODEL_DTYPE = "float32"

# In characters, not tokens: the tokenizer belongs to the embedding model. ~1200 chars is ~300
# tokens, leaving room under the model's 512 before it starts truncating.
CHUNK_CHARS = 1200

CHUNK_OVERLAP_CHARS = 200

CHUNK_OVERLAP_SENTENCES = 1

CHUNK_MAX_CHARS = 2000

CHUNK_MIN_CHARS = 80

# `by_element` budgets: a piece ends only between rows, sentences or lines; one longer stays whole.
ELEMENT_TABLE_CHARS = 1000

ELEMENT_TEXT_CHARS = 1000

# What `by_heading` accepts as a heading in PDF text, where no markup survives to say so.
HEADING_MAX_CHARS = 80

HEADING_MAX_WORDS = 12

HEADING_MIN_CAPITAL_RATIO = 0.6

# How many chunks a retriever returns, and therefore how many an answer can cite.
TOP_K = 5

# BM25's two shape parameters, at the values the literature settled on. `K1` is where term
# frequency saturates; `B` is how hard a long chunk is penalised (0 not at all, 1 fully).
BM25_K1 = 1.5

BM25_B = 0.75

# How deep each ranker's list goes into fusion. Past this the reciprocal contributions are all
# but identical, so the tail adds runtime and noise rather than signal.
FUSE_DEPTH = 100

# Reciprocal rank fusion's damping constant. At 60 the gap between rank 1 and rank 2 is small, so
# a chunk both rankers like beats one that only the loudest ranker put first. Lower it to trust
# first places more.
RRF_K = 60

# The reranker reads every candidate with the query, so this is a forward pass per row, not a
# lookup. Retrieve this many cheaply, score them all, keep the best TOP_K.
RERANK_MODEL = "BAAI/bge-reranker-v2-m3"

RERANK_CANDIDATES = 20

RERANK_BATCH = 32

# The method to rank with outside the eval: the best on questions not written from the passages.
SEARCH_METHOD = "hybrid+rerank"

# How many keys a keyed search reads from each ranker, enough to reach RERANK_CANDIDATES chunks.
KEY_DEPTH = 400

# What counts as page furniture in a PDF, where no markup survives to say what is a running header.
# Only lines this close to the top or bottom of a page are candidates; one whose digits-masked form
# reaches this fraction of the pages is furniture. Below the page floor, nothing is.
FURNITURE_MIN_PAGES = 4

FURNITURE_EDGE_LINES = 2

FURNITURE_RATIO = 0.2

# What joins two pages into one document text. Read as a paragraph break by every splitter.
PAGE_SEPARATOR = "\n\n"

# Docling, every chunker's parser: the reports carry a text layer, so OCR stays off; the device
# is Docling's choice of what the machine has (MPS here, CPU in CI).
DOCLING_OCR = False

DOCLING_DEVICE = "auto"

DOCLING_QUEUE_MAX_SIZE = 8  # pages held between Docling's pipeline stages; its 100 outgrew 16 GB

# Fonts drawing ₹ on a keyboard key, by family, and the keys each draws it on; nothing else maps.
PDF_RUPEE_KEYS: dict[str, str] = {
    "ITFRupee": "CDEHIJKL",
    "IndianRupee": "`",
    "Rupee": "`",
    "RupeeForadian": "`",
}

VERIFY_LINE_GAP = 0.5  # a word this many line heights below a line's middle starts the next line

VERIFY_BAND_MIN_SHARE = 0.15  # a figure column prints on at least this share of figure lines

VERIFY_WRAP_GAP = 2.6  # a label wraps onto a line at most this many line heights below
