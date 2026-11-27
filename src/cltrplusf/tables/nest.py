"""A table's rows nested into sections by how they are printed, each total checked against the
rows it should add, and the section a total closes chosen by that arithmetic where it can be."""

from __future__ import annotations

import re
from collections.abc import Sequence

from cltrplusf.config import TABLE_INDENT_STEP, TABLE_RANK_GRID
from cltrplusf.tables.model import Row

NOTE_TITLE = re.compile(r"^\d{1,2}[A-Z]?(?:\.\d{1,2})?\.\s+\S")  # "15. Borrowings", "3A. ..."
LESS = re.compile(r"^(?:\(?[a-z0-9ivx]{1,4}[.)]\s*)?less\b", re.I)
CLOSER = re.compile(
    r"^(?:\(?[a-z0-9ivx]{1,4}[.)]\s*)?(?:total|sub[- ]?total|grand total)\b|[-–]\s*total$"
    r"|\btotal\s*(?:\(.*\))?$",
    re.I,
)

Rank = tuple[float, int, int]


def closer(row: Row) -> bool:
    """Whether a row closes a section: values under no label, or a label naming a total."""
    label = row.label.strip()
    return bool(row.values) and (not label or bool(CLOSER.match(label)))


def rank(row: Row) -> Rank:
    """Where a row sits in the tree, lower holding higher: a numbered note title above all, then
    by indent, bold over plain, capitals over not."""
    text = row.label.strip()
    if row.section and NOTE_TITLE.match(text):
        return (-1.0, 0, 0)
    caps = sum(1 for w in text.split() if len(w) > 2 and w.isupper()) >= 2
    grid = round(row.x / TABLE_RANK_GRID) * TABLE_RANK_GRID
    return (grid, 0 if row.bold else 1, 0 if caps else 1)


def adds_up(parts: Sequence[Row], total: Row, strict: bool = False) -> bool | None:
    """Whether the parts sum to the total in every column the total prints, a "Less:" part
    subtracting, within the printed rounding; None when no column can be tested. `strict` refuses
    a zero total and a column no part prints, as an unlabelled subtotal must."""
    checked = 0
    for k, (v, places) in total.values.items():
        if strict and not v:
            return None
        printed = [p.values[k] for p in parts if k in p.values]
        if v == 100 and all(0 <= c <= 100 for c, _ in printed):
            continue  # a share column: each row's 100 per cent is no addend
        col = [
            ((-1 if LESS.match(p.label.strip()) else 1) * p.values[k][0], p.values[k][1])
            for p in parts
            if k in p.values
        ]
        if not col:
            if strict:
                return None
            continue
        tol = 0.5 * 10 ** -max([places] + [q for _, q in col]) * (len(col) + 1) + 1e-9
        got = sum(c for c, _ in col)
        if abs(got - v) > tol and abs(got + v) > tol:
            return False
        checked += 1
    return True if checked and len(parts) >= 2 else None


def addends(section: Row) -> list[Row]:
    """The rows a section's total adds: its value rows, each inner section by its total or, when
    it prints none, by its own addends; a value row equal to the sum of the rows right above it
    is an unlabelled subtotal and stands in for them."""
    out: list[Row] = []
    for c in section.children:
        if c.section:
            out.extend([c.total] if c.total else addends(c))
        elif not closer(c) or (c is not section.total and c.x > section.x + TABLE_INDENT_STEP):
            if any(v for v, _ in c.values.values()):
                for start in range(0, len(out) - 1):
                    if adds_up(out[start:], c, strict=True):
                        out = out[:start]
                        break
            out.append(c)
    return out


def _root_scope(root: Row) -> list[Row]:
    kids = root.children
    last = max([i for i, c in enumerate(kids) if closer(c)], default=-1)
    return addends(Row("", {}, {}, 0.0, False, [], children=kids[last + 1 :]))


def nest(rows: Sequence[Row]) -> Row:
    """The section tree over the rows, as a root row whose children are the top level.

    A section opens at a label-only row, or at a value row whose next row is indented under it,
    and holds the rows ranked below it; a label right under another label is its child whatever
    its rank. A closer ends the innermost open section whose rows add up to it, else the
    innermost; the section it ends is marked `checked="sum"` when they do."""
    root = Row("", {}, {}, -1.0, True, [])
    stack = [root]
    prev: Row | None = None
    for i, r in enumerate(rows):
        nxt = rows[i + 1] if i + 1 < len(rows) else None
        if closer(r):
            if len(stack) > 1 and r.label.strip():
                while len(stack) > 2 and rank(stack[-1]) >= rank(r) and stack[-1].x > r.x + 1:
                    stack.pop()  # a total at an outer indent closes the sections inside it first
            if len(stack) > 1 and r.x > stack[-1].x + TABLE_INDENT_STEP and not stack[-1].values:
                stack[-1].children.append(
                    r
                )  # a total indented under its section totals a run in it
                prev = r
                continue
            depth = next(
                (d for d in range(len(stack) - 1, 0, -1) if adds_up(addends(stack[d]), r)), None
            )
            if depth is None and adds_up(_root_scope(root), r):
                depth = 0
            summed = depth is not None
            del stack[(len(stack) - 1 if depth is None else depth) + 1 :]
            top = stack[-1]
            if top is root:
                root.children.append(r)
            else:
                top.total = r
                top.checked = "sum" if summed else "layout"
                stack.pop()
            prev = r
            continue
        if prev is not None and stack[-1] is prev:
            pass  # a section holds at least the row right after it
        elif r.section and nxt is not None and nxt.section:
            while len(stack) > 1 and rank(stack[-1]) >= rank(r):
                stack.pop()  # a chain of labels goes back to the outermost of its rank
        else:
            while len(stack) > 1 and rank(stack[-1]) > rank(r):
                stack.pop()
            if len(stack) > 1 and rank(stack[-1]) == rank(r):
                stack.pop()  # a sibling of the innermost section of its rank
        stack[-1].children.append(r)
        opens = r.section or (
            nxt is not None
            and not closer(nxt)
            and nxt.x > r.x + TABLE_INDENT_STEP
            and bool(r.values)
        )
        if opens:
            stack.append(r)
        prev = r
    return root
