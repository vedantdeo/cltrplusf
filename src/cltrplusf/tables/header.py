"""Where a table's body begins: the lines above its first value line are its header, less the
section labels printed right above the body."""

from __future__ import annotations

import re
import statistics
from collections.abc import Sequence

from cltrplusf.config import TABLE_PHRASE_GAP
from cltrplusf.printed import is_figure
from cltrplusf.tables.model import Cell, Piece

_SPACED_SEP = re.compile(r"(?<=\d)\s*,\s*(?=\d{2,3}(?!\d))")
_YEAR = re.compile(r"^(?:FY\s?)?(?:19|20)\d{2}(?:[-–/]\d{2,4})?$", re.I)
_MONTH = re.compile(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b", re.I)
_NUMERIC_DATE = re.compile(r"\d{1,2}[./-]\d{1,2}[./-]\d{2,4}")
_SMALL = re.compile(
    r"[(-]?\d{1,2}\)?(?:\s*-\s*\d{1,2})?"
)  # 3, (2), -1, 1-2: a column's number or range
_ASCENDING = re.compile(
    r"^(?:1?2?3?4?5?6?7?8?9?)$"
)  # 234567: column numbers printed close together
NUMBERING = re.compile(r"^\(?(?:\d{1,2}|[ivxlc]{1,5}|[IVXLC]{1,5}|[a-zA-Z])[.)]?\)?$")
HEADING_WORDS = re.compile(
    r"^(particulars|description|name|sr\.?|sl\.?|s\.?\s?no\.?|no\.?|term|category|currency|nature"
    r"|type|item|less|more|up|upto|within|beyond|not|over|between|due|unbilled)$",
    re.I,
)
DASH = re.compile(r"^[-–—]$")


def headerish(text: str, small_ok: bool = True) -> bool:
    """Whether a piece may sit in a header line: words, a year, a date, column numbers; a small
    number only when `small_ok`, which a line with a row label is not."""
    t = _SPACED_SEP.sub("", text).strip()
    if not is_figure(t):
        return True
    if _YEAR.match(t) or _MONTH.search(text) or _NUMERIC_DATE.fullmatch(t):
        return True
    if _column_numbers(text.strip()):
        return True
    return small_ok and bool(_SMALL.fullmatch(t))


def _column_numbers(text: str) -> bool:
    """Whether a piece is column numbers run together as printed, "234567": three or more digits,
    no separator, each one more than the last."""
    return (
        len(text) >= 3
        and text.isdigit()
        and all(int(b) == int(a) + 1 for a, b in zip(text, text[1:], strict=False))
    )


def value(piece: Piece) -> bool:
    """Whether a piece prints a value a row can hold, not a year, date or column number."""
    return not headerish(piece.text, small_ok=False)


def _row_label(line: Sequence[Piece], label_right: float) -> bool:
    head = [
        p.text
        for p in line
        if p.box[0] < label_right
        and not is_figure(_SPACED_SEP.sub("", p.text))
        and not NUMBERING.match(p.text)
    ]
    return bool(head) and not HEADING_WORDS.match(head[0])


def body_line(line: Sequence[Piece], label_right: float) -> bool:
    """Whether a line prints a value: a figure that is not a year, date or column number, or a
    labelled row whose values are all dashes."""
    labelled = _row_label(line, label_right)
    if any(not headerish(p.text, small_ok=not labelled) for p in line):
        return True
    right = [p.text for p in line if p.box[0] >= label_right]
    return labelled and bool(right) and all(DASH.match(t.strip()) for t in right)


def one_phrase(line: Sequence[Piece], label_right: float) -> bool:
    """Whether a line is one phrase set from the label column: no column-sized gap inside it, a
    hanging number ("5.", "(ii)") allowed its tab."""
    if line[0].box[0] > label_right:
        return False
    height = max(p.box[3] - p.box[1] for p in line) or 1.0
    rest = list(line[1:]) if len(line) > 1 and NUMBERING.match(line[0].text.strip()) else list(line)
    return all(
        b.box[0] - a.box[2] <= TABLE_PHRASE_GAP * height
        for a, b in zip(rest, rest[1:], strict=False)
    )


def label_right(cells: Sequence[Cell], lines: Sequence[Sequence[Piece]], left: float) -> float:
    """The right edge of the label column: Docling's first column by its cells' median right edge,
    widened up to the first printed value column; `left` when Docling has no first column."""
    rights = [c.box[2] for c in cells if c.box and c.col == 0 and c.col_end == 1 and c.text.strip()]
    edge = statistics.median_high(rights) if rights else left
    starts = [
        p.box[0] for line in lines for p in line if value(p) and len(re.sub(r"\D", "", p.text)) >= 3
    ]
    return max(edge, min(starts) - 1) if starts else edge


def header_rows(lines: Sequence[Sequence[Piece]], label_right: float) -> int | None:
    """How many lines are header: those before the first body line, less the one-phrase label
    lines right above it. None when no line prints a value, a table of text."""
    n = next((i for i, line in enumerate(lines) if body_line(line, label_right)), None)
    if n is None:
        return None
    while n and one_phrase(lines[n - 1], label_right):
        n -= 1
    return n
