"""Score `cltrplusf.tables` on the filed PDFs: numbers kept, and the hand labels for header rows,
wrapped labels and nesting, tuned and held out apart; with `--all`, every table of every
born-digital PDF for numbers kept and totals that add up. Free: no model, no API.

    uv run python scripts/table_eval.py            # the labelled tables
    uv run python scripts/table_eval.py --all      # every born-digital table too

Reads Docling's cached readings only, and refuses a PDF without one rather than parse it.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from collections.abc import Iterator
from pathlib import Path

from docling_core.types.doc.document import DoclingDocument

from cltrplusf import corpus, filed
from cltrplusf.tables import Cell, Row, Table, read_table
from cltrplusf.tables.lines import read_glyphs
from cltrplusf.tables.nest import addends, adds_up, closer
from cltrplusf.tables.rows import Line, read_line, wrap

REFERENCE = Path(__file__).resolve().parents[1] / "evals" / "reference" / "tables"
VERIFY = corpus.CORPUS_DIR / "verify"
_SEP = re.compile(r"(?<=\d),(?=\d{2,3}(?!\d))")


def doc_id_of(name: str) -> str:
    """A filed PDF's name in the parse cache, as aigent names it: `verify-annual-ITC-FY25`."""
    path = Path(name)
    return f"verify-{path.parent.name}-{path.stem}"


def reading(name: str) -> DoclingDocument | None:
    """Docling's cached reading of a filed PDF; None when it has none, rather than parse it."""
    kept = corpus.parse_file(VERIFY / name, doc_id_of(name))
    return DoclingDocument.load_from_json(kept) if kept.exists() else None


def tables_on(name: str, pages: set[int] | None = None) -> Iterator[tuple[int, int, Table | None]]:
    """Each Docling table of a PDF (on `pages`, when given) read from its words: page, its index
    among that page's tables, and the table."""
    parsed = reading(name)
    if parsed is None:
        raise LookupError(f"{name} has no cached Docling reading; parse it in aigent first")
    items = [
        i for i in filed._docling_tables(parsed) if pages is None or i.prov[0].page_no in pages
    ]
    wanted = sorted({i.prov[0].page_no for i in items})
    words = filed.read_words(VERIFY / name, wanted)
    glyphs = read_glyphs(VERIFY / name, wanted)
    seen: Counter[int] = Counter()
    for item in items:
        page = item.prov[0].page_no
        k = seen[page]
        seen[page] += 1
        height = parsed.pages[page].size.height
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
        box = item.prov[0].bbox.to_top_left_origin(height).as_tuple()
        yield page, k, read_table(page, box, cells, words.get(page, []), glyphs.get(page, []))


def runs(text: str) -> list[str]:
    return re.findall(r"\d+", _SEP.sub("", text))


def kept(table: Table) -> tuple[int, int]:
    """Digit runs the table's printed lines hold, and how many its header and cells lost."""
    printed = Counter(r for line in table.lines for p in line for r in runs(p.text))
    held = Counter(r for line in table.header for p in line for r in runs(p.text))
    for row in table.rows:
        for t in row.cells.values():
            held.update(runs(t))
    return sum(printed.values()), sum((printed - held).values())


def parents(table: Table) -> list[int]:
    at = {id(r): i for i, r in enumerate(table.rows)}
    out = [-1] * len(table.rows)

    def walk(node: Row, pid: int) -> None:
        for c in node.children:
            out[at[id(c)]] = pid
            if c.children:
                walk(c, at[id(c)])
                if c.total is not None:
                    out[at[id(c.total)]] = at[id(c)]

    walk(table.root, -1)
    return out


def totals(table: Table) -> tuple[int, int]:
    """Totals the tree can test, and how many of them add up."""
    tested = ok = 0

    def walk(node: Row) -> None:
        nonlocal tested, ok
        kids = node.children
        for i, c in enumerate(kids):
            if c.children:
                if c.total is not None:
                    got = adds_up(addends(c), c.total)
                    if got is not None:
                        tested, ok = tested + 1, ok + got
                walk(c)
            elif closer(c):
                last = max([j for j in range(i) if closer(kids[j])], default=-1)
                scope = Row("", {}, {}, 0.0, False, [], children=kids[last + 1 : i])
                got = adds_up(addends(scope), c)
                if got is not None:
                    tested, ok = tested + 1, ok + got

    walk(table.root)
    return tested, ok


def labelled() -> dict[str, Counter[str]]:
    headers = json.loads((REFERENCE / "headers.json").read_text())["tables"]
    wraps = json.loads((REFERENCE / "wraps.json").read_text())["lines"]
    nesting = json.loads((REFERENCE / "nesting.json").read_text())["tables"]
    pages: dict[str, set[int]] = {}
    for r in [*headers, *wraps, *nesting]:
        pages.setdefault(r["name"], set()).add(r["page"])
    read: dict[tuple[str, int, int], Table | None] = {}
    for name, ps in sorted(pages.items()):
        for page, k, table in tables_on(name, ps):
            read[(name, page, k)] = table
    score: dict[str, Counter[str]] = {}
    for r in headers:
        t = read.get((r["name"], r["page"], r["table"]))
        c = score.setdefault(f"header {r['split']}", Counter())
        c["n"] += 1
        c["ok"] += t is not None and len(t.header) == r["header"]
    for r in wraps:
        t = read.get((r["name"], r["page"], r["table"]))
        c = score.setdefault(f"wrap {r['split']}", Counter())
        if t is None or r["line"] < len(t.header):
            c["unreachable"] += 1
            continue
        body = _body_lines(t)
        i = r["line"] - len(t.header)
        if i >= len(body) or body[i].values or not body[i].label:
            c["unreachable"] += 1
            continue
        c["n"] += 1
        c["ok"] += wrap(body, i) == r["wrap"]
    for r in nesting:
        t = read.get((r["name"], r["page"], r["table"]))
        c = score.setdefault(f"nesting {r['split']}", Counter())
        if t is None or [x.label for x in t.rows[: len(r["rows"])]] != r["rows"]:
            c["rows differ"] += 1
            continue
        got = parents(t)[: len(r["parents"])]
        c["n"] += len(r["parents"])
        c["ok"] += sum(a == b for a, b in zip(got, r["parents"], strict=True))
    return score


def _body_lines(table: Table) -> list[Line]:
    return [read_line(line, table.label_right) for line in table.lines[table.header_lines :]]


def main() -> None:
    parser = argparse.ArgumentParser(description="Score cltrplusf.tables on the filed PDFs. Free.")
    parser.add_argument("--all", action="store_true", help="every born-digital table as well")
    args = parser.parse_args()
    for what, c in sorted(labelled().items()):
        extra = ", ".join(f"{k} {v}" for k, v in c.items() if k not in ("n", "ok"))
        share = c["ok"] / max(c["n"], 1)
        print(f"{what:18} {c['ok']}/{c['n']} ({share:.1%})" + (f"  {extra}" if extra else ""))
    if args.all:
        manifest = json.loads((VERIFY / "manifest.json").read_text())
        tally: Counter[str] = Counter()
        for name, entry in sorted(manifest.items()):
            if entry.get("format") != "pdf" or entry.get("ocr_pages"):
                continue
            if reading(name) is None:
                tally["unread PDFs"] += 1
                continue
            for _, _, t in tables_on(name):
                if t is None:
                    continue
                printed, lost = kept(t)
                tested, ok = totals(t)
                tally.update(
                    {"tables": 1, "printed": printed, "lost": lost, "tested": tested, "ok": ok}
                )
            print(name, flush=True)
        share = tally["ok"] / max(tally["tested"], 1)
        lost = f"{tally['lost']} of {tally['printed']} numbers lost"
        print(f"born-digital: {tally['tables']} tables; {lost}; {tally['unread PDFs']} PDFs unread")
        print(f"totals that add up: {tally['ok']}/{tally['tested']} ({share:.1%})")


if __name__ == "__main__":
    main()
