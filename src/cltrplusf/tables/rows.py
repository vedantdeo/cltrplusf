"""A table's body lines made rows: a label wrapped over lines joined, whether it continues the row
above, runs into the row below, or wraps around its own values."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from cltrplusf.config import TABLE_SAME_INDENT
from cltrplusf.printed import number
from cltrplusf.tables.header import NUMBERING, headerish
from cltrplusf.tables.model import Piece, Row

Wrap = Literal["up", "down", "none"]

CONNECTIVE = re.compile(
    r"(?:\b(?:of|and|or|to|for|in|on|at|by|from|with|the|a|an|than|other|under|including|towards"
    r"|between|less|net)|[,(&/–-])$",
    re.I,
)
_OPENER = re.compile(r"^[a-z(]")  # a line opening lowercase or with "(" carries a phrase on
_BULLET = re.compile(r"^[-–—•·*]$")
_NIL_WORDS = ("Nil", "NA", "N.A.", "…")


@dataclass(frozen=True)
class Line:
    """A body line as the wrap rule reads it."""

    text: str
    label: str
    text_x: float
    numbered: bool
    bold: bool
    values: bool


def holds_value(piece: Piece, label_right: float) -> bool:
    """Whether a piece is one of its row's values: right of the label column and a value, a dash
    or a nil word."""
    t = piece.text.strip()
    return piece.box[0] >= label_right and (
        not headerish(t, small_ok=False) or bool(_BULLET.match(t)) or t in _NIL_WORDS
    )


def read_line(line: Sequence[Piece], label_right: float) -> Line:
    """What the wrap rule needs of a line: its label, where its text starts, its style."""
    first = line[0].text
    text_x = next(
        (p.box[0] for p in line if not NUMBERING.match(p.text) and not _BULLET.match(p.text)),
        line[0].box[0],
    )
    return Line(
        text=" ".join(p.text for p in line),
        label=" ".join(p.text for p in line if not holds_value(p, label_right)),
        text_x=text_x,
        numbered=bool(NUMBERING.match(first) or _BULLET.match(first)),
        bold=sum(p.bold for p in line) > len(line) / 2,
        values=any(holds_value(p, label_right) for p in line),
    )


def _opens(line: Line) -> bool:
    return not line.numbered and bool(_OPENER.match(line.text))


def _unclosed(label: str) -> bool:
    return label.count("(") > label.count(")") or label.count("[") > label.count("]")


def _same_indent(a: Line, b: Line) -> bool:
    return abs(a.text_x - b.text_x) <= TABLE_SAME_INDENT


def wrap(lines: Sequence[Line], i: int) -> Wrap:
    """For a line printing only a label: whether it continues the row above (up), runs into the
    row below (down), or stands alone (none). Lines printing only values are passed over above."""
    me = lines[i]
    prev = next((lines[j] for j in range(i - 1, -1, -1) if lines[j].label), None)
    nxt = lines[i + 1] if i + 1 < len(lines) else None
    after = lines[i + 2] if i + 2 < len(lines) else None
    if prev and prev.bold == me.bold and me.text_x >= prev.text_x - 1 and not me.numbered:
        if _opens(me) or CONNECTIVE.search(prev.label) or _unclosed(prev.label):
            return "up"
    if (
        nxt
        and nxt.values
        and not nxt.label
        and after
        and after.label
        and not after.values
        and _same_indent(after, me)
        and not after.numbered
    ):
        if _opens(after) or CONNECTIVE.search(me.label) or _unclosed(me.label):
            return "down"  # the label, its values on a line of their own, the label's second line
    if nxt and nxt.label and nxt.bold == me.bold and _same_indent(nxt, me) and not nxt.numbered:
        if _opens(nxt) or CONNECTIVE.search(me.label) or _unclosed(me.label):
            return "down"
        if nxt.values and not me.bold and not me.label.endswith(":"):
            return "down"  # a plain label over a row at its own indent: that row's first line
    return "none"


def _row(
    line: Line, pieces: Sequence[Piece], columns: Sequence[int], label_right: float, at: int
) -> Row:
    cells: dict[int, str] = {}
    values: dict[int, tuple[float, int]] = {}
    for p, c in zip(pieces, columns, strict=True):
        cells[c] = f"{cells.get(c, '')} {p.text}".strip()
        if holds_value(p, label_right):
            read = number(p.text)
            if read is not None:
                values[c] = (read[0], read[1])
    return Row(line.label, cells, values, line.text_x, line.bold, [at])


def _merge(into: Row, other: Row) -> None:
    into.label = f"{into.label} {other.label}".strip()
    for c, t in other.cells.items():
        into.cells[c] = f"{into.cells.get(c, '')} {t}".strip()
    into.values.update(other.values)
    into.lines.extend(other.lines)


def rows_of(
    body: Sequence[Sequence[Piece]],
    columns: Sequence[Sequence[int]],
    label_right: float,
    first: int = 0,
) -> list[Row]:
    """The body's lines as rows, wrapped labels joined; `first` is the body's first line number,
    so each row records the table lines it came from."""
    read = [read_line(line, label_right) for line in body]
    rows: list[Row] = []
    carry: Row | None = None
    for i, (line, pieces, cols) in enumerate(zip(read, body, columns, strict=True)):
        how: Wrap = wrap(read, i) if not line.values and line.label else "none"
        row = _row(line, pieces, cols, label_right, first + i)
        if how == "up" and rows and carry is None:
            _merge(rows[-1], row)
            continue
        if carry is not None:
            _merge(carry, row)
            row, carry = carry, None
        if how == "down":
            carry = row
            continue
        rows.append(row)
    if carry is not None:
        rows.append(carry)
    return rows
