"""Columns for a table's pieces: Docling's columns by the boxes of its cells, each split where two
printed figure columns sit inside it, and every piece placed in one."""

from __future__ import annotations

import re
import statistics
from collections.abc import Sequence

from cltrplusf.config import TABLE_BAND_GAP, TABLE_BAND_MIN_LINES
from cltrplusf.printed import is_figure
from cltrplusf.tables.model import Box, Cell, Piece

_SPACED_SEP = re.compile(
    r"(?<=\d)\s*,\s*(?=\d{2,3}(?!\d))"
)  # "2 ,121.80" as a text layer spaces it

Span = tuple[float, float]


def figure(text: str) -> bool:
    """Whether a piece prints a figure, its thousands separators spaced or not."""
    return is_figure(_SPACED_SEP.sub("", text))


def docling_columns(cells: Sequence[Cell]) -> dict[int, Span]:
    """Each of Docling's columns as the median left and right edges of its one-column cells."""
    spans: dict[int, list[Span]] = {}
    for c in cells:
        if c.box is not None and c.col_end - c.col == 1 and c.text.strip():
            spans.setdefault(c.col, []).append((c.box[0], c.box[2]))
    return {
        j: (statistics.median_high([a for a, _ in v]), statistics.median_high([b for _, b in v]))
        for j, v in spans.items()
    }


def bands(lines: Sequence[Sequence[Piece]]) -> list[float]:
    """The printed figure columns: figures' right edges grouped within `TABLE_BAND_GAP`, kept where
    at least `TABLE_BAND_MIN_LINES` figures print, as each group's mean edge."""
    edges = sorted(p.box[2] for line in lines for p in line if figure(p.text))
    groups: list[list[float]] = []
    for e in edges:
        if groups and e - groups[-1][-1] <= TABLE_BAND_GAP:
            groups[-1].append(e)
        else:
            groups.append([e])
    return [statistics.fmean(g) for g in groups if len(g) >= TABLE_BAND_MIN_LINES]


def _overlap(box: Box, span: Span) -> float:
    return min(box[2], span[1]) - max(box[0], span[0])


def _home(piece: Piece, columns: dict[int, Span], printed: Sequence[float]) -> float:
    """The column a piece falls in: Docling's it overlaps most, else the nearest by middle; a
    figure inside a column holding two printed figure columns takes the one at its right edge."""
    if not columns:
        return 0.0
    middle = (piece.box[0] + piece.box[2]) / 2
    best = max(
        columns,
        key=lambda j: (_overlap(piece.box, columns[j]), -abs(middle - sum(columns[j]) / 2)),
    )
    if _overlap(piece.box, columns[best]) <= 0:
        best = min(columns, key=lambda j: abs(middle - sum(columns[j]) / 2))
    if figure(piece.text):
        left, right = columns[best]
        inner = [x for x in printed if left - TABLE_BAND_GAP <= x <= right + TABLE_BAND_GAP]
        if len(inner) >= 2:
            band = min(range(len(inner)), key=lambda i: abs(inner[i] - piece.box[2]))
            return best + band / 10  # a sub-column of Docling's column, kept in order
    return float(best)


def placed(lines: Sequence[Sequence[Piece]], cells: Sequence[Cell]) -> list[list[int]]:
    """For each line, the column of each of its pieces, columns numbered left to right."""
    columns = docling_columns(cells)
    printed = bands(lines)
    homes = [[_home(p, columns, printed) for p in line] for line in lines]
    order = {c: i for i, c in enumerate(sorted({c for line in homes for c in line}))}
    return [[order[c] for c in line] for line in homes]
