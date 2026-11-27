"""What a table read from its printed words is: pieces of text on lines, rows with their cells, and
the section tree over the rows."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Box = tuple[float, float, float, float]  # left, top, right, bottom on the page as displayed
Checked = Literal["sum", "layout"]


@dataclass(frozen=True)
class Piece:
    """A run of words printed together on one line, its box, and whether most of it is bold."""

    text: str
    box: Box
    bold: bool = False


@dataclass(frozen=True)
class Cell:
    """One of Docling's cells, boxed: where the reading's columns are taken from."""

    text: str
    row: int
    col: int
    row_end: int
    col_end: int
    box: Box | None


@dataclass
class Row:
    """A body row: its label, its cells by column, where it sits, and its place in the tree.

    `values` holds each column's printed number (value, decimal places); `children` the rows of the
    section it opens; `total` the row that closes that section, and `checked` how the tree knows."""

    label: str
    cells: dict[int, str]
    values: dict[int, tuple[float, int]]
    x: float
    bold: bool
    lines: list[int]
    children: list[Row] = field(default_factory=list["Row"])
    total: Row | None = None
    checked: Checked = "layout"

    @property
    def section(self) -> bool:
        """A row printing no value: a label opening the rows below it."""
        return not self.values


@dataclass
class Table:
    """A table read from its printed words: every printed line in it, how many of them are header,
    where its label column ends, its body rows in print order, and the root of its section tree
    (a row with no label whose children are the top level)."""

    page: int
    box: Box
    lines: list[list[Piece]]
    header_lines: int
    label_right: float
    rows: list[Row]
    root: Row

    @property
    def header(self) -> list[list[Piece]]:
        return self.lines[: self.header_lines]
