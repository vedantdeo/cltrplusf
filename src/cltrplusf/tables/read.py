"""A table read from the words its page prints, with Docling's cells for its box and columns."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from pathlib import Path

from docling_core.types.doc.document import DoclingDocument

from cltrplusf import filed, line_rows
from cltrplusf.tables.grid import placed
from cltrplusf.tables.header import header_rows, label_right
from cltrplusf.tables.lines import Glyph, lines_in, read_glyphs
from cltrplusf.tables.model import Box, Cell, Row, Table
from cltrplusf.tables.nest import nest
from cltrplusf.tables.rows import rows_of

Key = tuple[tuple[str, ...], list[Row]]


def read_table(
    page: int,
    box: Box,
    cells: Sequence[Cell],
    words: Sequence[line_rows.Word],
    glyphs: Sequence[Glyph] = (),
) -> Table | None:
    """The table in `box`: every word printed there, on its line and in a column, its header
    lines apart, its body as rows nested into sections. None when no word lies in the box."""
    lines = lines_in(box, words, glyphs)
    if not lines:
        return None
    edge = label_right(cells, lines, box[0])
    n = header_rows(lines, edge) or 0
    columns = placed(lines, cells)
    rows = rows_of(lines[n:], columns[n:], edge, first=n)
    return Table(page, box, lines, n, edge, rows, nest(rows))


def read_tables(path: Path, parsed: DoclingDocument) -> list[Table]:
    """Every table Docling found in a PDF, read from the PDF's own words, in Docling's order."""
    items = filed._docling_tables(parsed)
    pages = sorted({item.prov[0].page_no for item in items})
    words = filed.read_words(path, pages)
    glyphs = read_glyphs(path, pages)
    out: list[Table] = []
    for item in items:
        page = item.prov[0].page_no
        height = parsed.pages[page].size.height
        box = item.prov[0].bbox.to_top_left_origin(height).as_tuple()
        cells = [
            Cell(
                c.text,
                c.start_row_offset_idx,
                c.start_col_offset_idx,
                c.end_row_offset_idx,
                c.end_col_offset_idx,
                c.bbox.to_top_left_origin(height).as_tuple() if c.bbox else None,
            )
            for c in item.data.table_cells
        ]
        table = read_table(page, box, cells, words.get(page, []), glyphs.get(page, []))
        if table is not None:
            out.append(table)
    return out


def keys(table: Table, title: str) -> list[Key]:
    """The table's innermost sections, each as its path from `title` down and the rows it holds.

    A section whose own sections hold rows gets no key of its own; the rows printed directly
    under it, beside those sections, form a section at its path."""
    return list(_walk(table.root, (title,)))


def _walk(node: Row, path: tuple[str, ...]) -> Iterator[Key]:
    inner = [c for c in node.children if c.children]
    own = [c for c in node.children if not c.children]
    if node.total is not None:
        own.append(node.total)
    for c in inner:
        yield from _walk(c, (*path, c.label))
    if own:
        yield path, own
