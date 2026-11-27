"""A filed PDF's words, read as Docling read it, and its tables re-rowed by their printed lines;
both memoised on disk beside Docling's cached reading."""

from __future__ import annotations

import gzip
import hashlib
import inspect
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from typing import cast

import pypdfium2 as pdfium
from docling_core.types.doc.common.content_layer import ContentLayer
from docling_core.types.doc.document import DoclingDocument
from docling_core.types.doc.items.table.table import TableItem

from cltrplusf import corpus, line_rows, printed
from cltrplusf.chunk import Document, Table
from cltrplusf.config import VERIFY_BAND_MIN_SHARE, VERIFY_LINE_GAP, VERIFY_WRAP_GAP
from cltrplusf.corpus import (
    CACHE_DIR,
    StoredDocument,
    assembled,
    document_from_json,
    elements_of,
    parse_cached,
    rupees_decoded,
    table_rows,
    write_cached,
)

Rows = tuple[tuple[str, ...], ...]


def _docling_tables(parsed: DoclingDocument) -> list[TableItem]:
    """Docling's tables in the order `elements_of` renders them: page by page, reading order."""
    attached = {
        ref.cref
        for item, _ in parsed.iterate_items()
        if isinstance(item, TableItem)
        for ref in (*item.captions, *item.footnotes)
    }
    layers = {ContentLayer.BODY, ContentLayer.FURNITURE}
    found = [
        item
        for item, _ in parsed.iterate_items(traverse_pictures=True, included_content_layers=layers)
        if isinstance(item, TableItem)
        and item.prov
        and item.self_ref not in attached
        and item.content_layer != ContentLayer.FURNITURE
    ]
    return sorted(found, key=lambda item: item.prov[0].page_no)


def _slice_of(rows: Rows, body: Rows) -> int | None:
    """Where `body` sits inside a rendered table's rows, after its caption lines; None if not."""
    for start in range(len(rows) - len(body) + 1):
        if rows[start : start + len(body)] == body:
            return start
    return None


def with_line_rows(
    document: Document, parsed: DoclingDocument, words: Mapping[int, Sequence[line_rows.Word]]
) -> Document:
    """A rendered PDF with each table's body re-rowed from its printed lines (`line_rows`), given
    the words of each page with a table; its captions, footnotes and Docling's header rows kept,
    and a table it cannot re-row left as Docling read it. ValueError when a rendered table
    matches none of Docling's."""
    items = _docling_tables(parsed)
    tables: list[Table] = []
    k = 0
    for table in document.tables:
        while k < len(items) and _slice_of(table.rows, table_rows(items[k].data)) is None:
            k += 1
        if k == len(items):
            raise ValueError(f"{document.doc_id}: a rendered table matches none of Docling's")
        item, k = items[k], k + 1
        body = table_rows(item.data)
        start = _slice_of(table.rows, body) or 0
        page_no = item.prov[0].page_no
        shape = line_rows.layout(item, body, parsed.pages[page_no].size.height)
        rebuilt = (
            None
            if shape is None
            else line_rows.line_rows(body[: shape.header], shape, words.get(page_no, ()))
        )
        if shape is None or rebuilt is None:
            tables.append(table)
            continue
        kept = start + shape.header
        tables.append(
            replace(
                table,
                rows=table.rows[:start] + rebuilt + table.rows[start + len(body) :],
                header_rows=min(table.header_rows, kept),
                sections=tuple(s for s in table.sections if s < kept),
            )
        )
    return replace(document, tables=tuple(tables))


def _opened(path: Path) -> pdfium.PdfDocument:
    """A PDF opened with its rupee fonts read as ₹, as Docling read it."""
    decoded = rupees_decoded(path)
    return pdfium.PdfDocument(decoded if isinstance(decoded, Path) else decoded.stream.getvalue())


def read_words(path: Path, pages: Sequence[int]) -> dict[int, list[line_rows.Word]]:
    """The words of these 1-based pages of a PDF, placed on each page as displayed, boxes rounded
    to a hundredth of a point."""
    pdf = _opened(path)
    try:
        out: dict[int, list[line_rows.Word]] = {}
        for page_no in pages:
            page = pdf[page_no - 1]
            left, bottom, right, top = line_rows.crop_box(page)
            placed = line_rows.on_display(
                line_rows.page_words(page), page.get_rotation(), right - left, top - bottom
            )
            out[page_no] = [
                (text, (round(a, 2), round(b, 2), round(c, 2), round(d, 2)), spaced)
                for text, (a, b, c, d), spaced in placed
            ]
        return out
    finally:
        pdf.close()


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


# Everything that decides a filed PDF's words: rarely changed, so kept below the re-rowing.
_WORDS_FINGERPRINT = hashlib.sha256(
    (
        "".join(
            inspect.getsource(f)
            for f in (
                line_rows.split_runs,
                line_rows.page_words,
                line_rows.crop_box,
                line_rows.displayed,
                line_rows.on_display,
                _docling_tables,
                _opened,
                read_words,
            )
        )
        + f"|{corpus.parse_fingerprint()}|{line_rows.GRID}"
    ).encode()
).hexdigest()[:12]


# Everything that decides how a filed PDF's tables are re-rowed, above its words and rendering.
_LINES_FINGERPRINT = hashlib.sha256(
    (
        inspect.getsource(line_rows)
        + "".join(inspect.getsource(f) for f in (_slice_of, with_line_rows, printed))
        + f"|{VERIFY_LINE_GAP}|{VERIFY_BAND_MIN_SHARE}|{VERIFY_WRAP_GAP}"
        + f"|{_WORDS_FINGERPRINT}|{corpus.ingest_fingerprint()}"
    ).encode()
).hexdigest()[:12]


def words_file(path: Path, doc_id: str, cache_dir: Path = CACHE_DIR) -> Path:
    """Where a filed PDF's words are kept, keyed by its bytes and the words fingerprint."""
    return cache_dir / f"{doc_id}-words-{_digest(path)}-{_WORDS_FINGERPRINT}.json.gz"


def lines_file(path: Path, doc_id: str, cache_dir: Path = CACHE_DIR) -> Path:
    """Where a filed PDF re-rowed is kept, keyed by its bytes and the re-rowing fingerprint."""
    return cache_dir / f"{doc_id}-lines-{_digest(path)}-{_LINES_FINGERPRINT}.json"


def load_words_cached(
    path: Path,
    doc_id: str,
    parsed: DoclingDocument,
    cache_dir: Path = CACHE_DIR,
    read: Callable[[Path, Sequence[int]], dict[int, list[line_rows.Word]]] = read_words,
) -> dict[int, list[line_rows.Word]]:
    """The words of each page of a filed PDF that Docling found a table on (`read_words`),
    memoised on disk, gzipped; a file that does not read back is rebuilt, superseded ones swept."""
    kept = words_file(path, doc_id, cache_dir)
    if kept.exists():
        try:
            stored = json.loads(gzip.decompress(kept.read_bytes()))
            return {
                int(page): [(str(t), (b[0], b[1], b[2], b[3]), bool(s)) for t, b, s in words]
                for page, words in stored.items()
            }
        except (OSError, ValueError, TypeError, IndexError):
            kept.unlink(missing_ok=True)
    pages = sorted({item.prov[0].page_no for item in _docling_tables(parsed)})
    words = read(path, pages)
    for stale in cache_dir.glob(f"{doc_id}-words-*.json.gz"):
        stale.unlink(missing_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
    partial = kept.with_suffix(".partial")
    partial.write_bytes(gzip.compress(json.dumps(words).encode()))
    partial.replace(kept)
    return words


def load_lines_cached(
    path: Path,
    doc_id: str,
    cache_dir: Path = CACHE_DIR,
    parsed: Callable[[Path, str, Path], DoclingDocument] = parse_cached,
    words: Callable[[Path, str, DoclingDocument, Path], dict[int, list[line_rows.Word]]] = (
        load_words_cached
    ),
) -> Document:
    """A filed PDF as the cross-check reads it: rendered from Docling's cached reading, its tables
    re-rowed from its cached words (`with_line_rows`), memoised on disk; a file that does not
    read back is rebuilt, superseded ones swept."""
    kept = lines_file(path, doc_id, cache_dir)
    if kept.exists():
        try:
            return document_from_json(cast(StoredDocument, json.loads(kept.read_text("utf-8"))))
        except (json.JSONDecodeError, KeyError, TypeError):
            kept.unlink(missing_ok=True)
    reading = parsed(path, doc_id, cache_dir)
    document = assembled(doc_id, elements_of(reading), source=str(path))
    rebuilt = with_line_rows(document, reading, words(path, doc_id, reading, cache_dir))
    for stale in cache_dir.glob(f"{doc_id}-lines-*.json"):
        stale.unlink(missing_ok=True)
    write_cached(kept, rebuilt)
    return rebuilt
