"""`tables.nest` and `tables.read`: rows nested into sections, totals checked by their sums, a
table read whole from a printed page, and its innermost sections as keys."""

from __future__ import annotations

from pathlib import Path

import pytest

from cltrplusf.tables import Cell, Row, keys, read_table, read_tables
from cltrplusf.tables.model import Table
from cltrplusf.tables.nest import addends, adds_up, closer, nest, rank
from cltrplusf.testing import Grid, docling, printed_pdf


def _row(label: str, *values: float, x: float = 0.0, bold: bool = False, places: int = 0) -> Row:
    return Row(label, {}, {k + 1: (v, places) for k, v in enumerate(values)}, x, bold, [])


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        pytest.param(_row("Total", 10), True, id="Total"),
        pytest.param(_row("SUB-TOTAL", 10), True, id="a sub-total"),
        pytest.param(_row("(c) Total equity", 10), True, id="numbered"),
        pytest.param(_row("", 10), True, id="values under no label"),
        pytest.param(_row("Revenue", 10), False, id="an ordinary row"),
        pytest.param(_row("Total"), False, id="a label printing no value"),
    ],
)
def test_closer(row: Row, expected: bool) -> None:
    assert closer(row) is expected


def test_rank_puts_a_note_title_above_all_then_indent_bold_and_capitals() -> None:
    assert rank(_row("15. Borrowings", x=40)) < rank(_row("Secured", x=0, bold=True))
    assert rank(_row("Secured", bold=True)) < rank(_row("Secured"))
    assert rank(_row("Term loans")) < rank(_row("Term loans", x=20))
    assert rank(_row("DEBT MUTUAL FUNDS", bold=True)) < rank(_row("Quoted", bold=True))


@pytest.mark.parametrize(
    ("parts", "total", "expected"),
    [
        pytest.param(
            [_row("a", 10, 5), _row("b", 20, 6)], _row("Total", 30, 11), True, id="adding up"
        ),
        pytest.param(
            [_row("a", 10), _row("b", 20)], _row("Total", 33), False, id="off by more than rounding"
        ),
        pytest.param([_row("a", 10), _row("b", 20)], _row("Total", 31), True, id="off by rounding"),
        pytest.param(
            [_row("a", 10), _row("Less: allowance", 3)], _row("Total", 7), True, id="Less subtracts"
        ),
        pytest.param(
            [_row("a", 1.04, places=2), _row("b", 2.04, places=2)],
            _row("Total", 3.09, places=2),
            True,
            id="within rounding",
        ),
        pytest.param(
            [_row("Male", 600, 100), _row("Female", 400, 100)],
            _row("Total", 1000, 100),
            True,
            id="a share column skipped",
        ),
        pytest.param([_row("a", 10)], _row("Total", 10), None, id="one part tests nothing"),
        pytest.param([_row("a"), _row("b")], _row("Total", 10), None, id="no column in common"),
    ],
)
def test_adds_up(parts: list[Row], total: Row, expected: bool | None) -> None:
    assert adds_up(parts, total) is expected


def test_strict_refuses_a_zero_total() -> None:
    assert adds_up([_row("a", 0), _row("b", 0)], _row("", 0), strict=True) is None


def test_addends_fold_an_unlabelled_subtotal_into_the_rows_it_sums() -> None:
    section = _row("Investment income")
    a, b, sub, c = (
        _row("Interest", 3),
        _row("Dividend", 4),
        _row("From financial assets", 7),
        _row("Gain", 5),
    )
    section.children = [a, b, sub, c]
    assert addends(section) == [sub, c]


def _labels(node: Row, depth: int = 0) -> list[str]:
    out: list[str] = []
    for c in node.children:
        out.append("  " * depth + c.label)
        out.extend(_labels(c, depth + 1))
        if c.total is not None:
            out.append("  " * (depth + 1) + f"= {c.total.label}")
    return out


def test_nest_holds_rows_under_sections_and_closes_them_with_their_totals() -> None:
    rows = [
        _row("15. Borrowings"),
        _row("Secured", bold=True),
        _row("Term loans", 100),
        _row("Debentures", 50),
        _row("Total secured", 150),
        _row("Unsecured", bold=True),
        _row("Deposits", 30),
        _row("Total", 180),
    ]
    root = nest(rows)
    assert _labels(root) == [
        "15. Borrowings",
        "  Secured",
        "    Term loans",
        "    Debentures",
        "    = Total secured",
        "  Unsecured",
        "    Deposits",
        "  = Total",
    ], _labels(root)
    assert rows[1].checked == "sum" and rows[0].checked == "sum"


def test_a_label_right_under_a_label_is_its_child_whatever_its_rank() -> None:
    rows = [
        _row("Investments at FVTPL", bold=True),
        _row("Quoted", bold=True),
        _row("Mutual funds", 10),
    ]
    assert _labels(nest(rows)) == ["Investments at FVTPL", "  Quoted", "    Mutual funds"]


def test_a_value_row_with_rows_indented_under_it_opens_a_section() -> None:
    rows = [
        _row("Net working capital", 60),
        _row("i) Cash", 20, x=30),
        _row("ii) Investments", 40, x=30),
    ]
    assert _labels(nest(rows)) == ["Net working capital", "  i) Cash", "  ii) Investments"]


def test_a_total_closes_the_section_its_rows_add_up_to() -> None:
    rows = [
        _row("Trade payables", bold=True),
        _row("MSME", 10, x=20),
        _row("Others", 20, x=20),
        _row("SUB-TOTAL", 30, x=20),
        _row("Accrued", bold=True, x=20),
        _row("MSME", 1, x=40),
        _row("Others", 2, x=40),
        _row("TOTAL", 33, x=20),
    ]
    root = nest(rows)
    assert rows[0].total is rows[7] and rows[0].checked == "sum", _labels(root)


def test_a_total_that_adds_up_to_nothing_closes_the_innermost_by_layout() -> None:
    rows = [_row("Loans", bold=True), _row("a", 1), _row("b", 2), _row("Total", 99)]
    nest(rows)
    assert rows[0].total is rows[3] and rows[0].checked == "layout"


def _cell(text: str, row: int, col: int, box: tuple[float, float, float, float]) -> Cell:
    return Cell(text, row, col, row + 1, col + 1, box)


_PRINTED = [  # (left, baseline, text) on a 792-point page
    (55, 700, "Particulars"),
    (200, 700, "2025"),
    (260, 700, "2024"),
    (55, 680, "Secured:"),
    (55, 660, "Term loans"),
    (200, 660, "1,000"),
    (260, 660, "900"),
    (55, 640, "Debentures"),
    (200, 640, "500"),
    (260, 640, "400"),
    (55, 620, "Total"),
    (200, 620, "1,500"),
    (260, 620, "1,300"),
]
_CELLS = [
    _cell("Particulars", 0, 0, (55, 85, 90, 95)),
    _cell("Term loans", 2, 0, (55, 125, 90, 135)),
    _cell("1,000", 2, 1, (200, 125, 215, 135)),
    _cell("900", 2, 2, (260, 125, 272, 135)),
    _cell("500", 3, 1, (200, 145, 212, 155)),
    _cell("400", 3, 2, (260, 145, 272, 155)),
]


def _read(tmp_path: Path) -> Table:
    from cltrplusf import filed

    words = filed.read_words(printed_pdf(tmp_path / "p.pdf", _PRINTED), [1])[1]
    bold = [((b[0] + b[2]) / 2, (b[1] + b[3]) / 2, True) for t, b, _ in words if t == "Secured:"]
    table = read_table(1, (50, 80, 300, 180), _CELLS, words, bold)  # "Secured:" set in bold
    assert table is not None
    return table


def test_read_table_reads_header_rows_and_tree_from_the_printed_page(tmp_path: Path) -> None:
    table = _read(tmp_path)
    assert [[p.text for p in line] for line in table.header] == [["Particulars", "2025", "2024"]]
    assert [r.label for r in table.rows] == ["Secured:", "Term loans", "Debentures", "Total"]
    assert table.rows[1].cells == {0: "Term loans", 1: "1,000", 2: "900"}
    secured = table.rows[0]
    assert secured.total is table.rows[3] and secured.checked == "sum"


def test_read_table_keeps_every_printed_number(tmp_path: Path) -> None:
    table = _read(tmp_path)
    printed = sorted(t for _, _, t in _PRINTED if t[0].isdigit())
    held = [t for line in table.header for p in line for t in [p.text] if t[0].isdigit()]
    held += [t for r in table.rows for t in r.cells.values() if t[0].isdigit()]
    assert sorted(held) == printed


def test_read_table_finds_nothing_in_an_empty_box(tmp_path: Path) -> None:
    from cltrplusf import filed

    words = filed.read_words(printed_pdf(tmp_path / "p.pdf", _PRINTED), [1])[1]
    assert read_table(1, (400, 400, 500, 500), _CELLS, words) is None


def test_keys_are_the_innermost_sections_and_a_parents_own_rows(tmp_path: Path) -> None:
    table = _read(tmp_path)
    assert [(path, [r.label for r in rows]) for path, rows in keys(table, "Borrowings")] == [
        (("Borrowings", "Secured:"), ["Term loans", "Debentures", "Total"]),
    ]
    parent = _row("Equity", bold=True)
    inner = _row("Reserves", bold=True)
    inner.children = [_row("General", 1)]
    parent.children = [inner, _row("Share capital", 2)]
    root = _row("")
    root.children = [parent]
    nested = Table(1, (0, 0, 1, 1), [], 0, 0.0, [], root)
    assert [(p, [r.label for r in rs]) for p, rs in keys(nested, "T")] == [
        (("T", "Equity", "Reserves"), ["General"]),
        (("T", "Equity"), ["Share capital"]),
    ]


def test_read_tables_reads_each_of_doclings_tables_from_the_pdf(tmp_path: Path) -> None:
    path = printed_pdf(tmp_path / "p.pdf", _PRINTED)
    grid = Grid(
        rows=(("Particulars", "2025", "2024"), ("Term loans", "1,000", "900")),
        header_rows=1,
        box=(50, 600, 300, 712),
    )
    [table] = read_tables(path, docling([[grid]]))
    assert table.page == 1
    assert "Total" in [r.label for r in table.rows]


def test_a_total_summing_the_top_level_closes_no_section() -> None:
    rows = [
        _row("Cash", 5),
        _row("Investments", bold=True),
        _row("Bonds", 1, x=20),
        _row("Funds", 2, x=20),
        _row("Total", 8),
    ]
    root = nest(rows)
    assert rows[1].total is None and rows[4] in root.children, _labels(root)


def test_a_plain_section_label_holds_at_least_the_row_after_it() -> None:
    rows = [_row("Revenue", 9), _row("Segment"), _row("Retail", 4)]
    assert _labels(nest(rows)) == ["Revenue", "Segment", "  Retail"]
