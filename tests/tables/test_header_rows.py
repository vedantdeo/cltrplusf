"""`tables.header` and `tables.rows`: where the body begins, and wrapped labels joined."""

from __future__ import annotations

import pytest

from cltrplusf.tables.header import body_line, header_rows, headerish, label_right, one_phrase
from cltrplusf.tables.model import Cell, Piece
from cltrplusf.tables.rows import Line, read_line, rows_of, wrap
from cltrplusf.testing import piece

EDGE = 60.0  # where the label column ends in these tables


@pytest.mark.parametrize(
    ("text", "small_ok", "expected"),
    [
        ("Particulars", True, True),
        ("2025", False, True),
        ("FY 2024-25", False, True),
        ("March 31, 2025", False, True),
        ("31.03.2024", False, True),
        ("234567", False, True),
        ("3", True, True),
        ("1-2", True, True),
        ("3", False, False),
        ("1,234", True, False),
        ("(12.5)", True, False),
    ],
)
def test_headerish(text: str, small_ok: bool, expected: bool) -> None:
    assert headerish(text, small_ok) is expected


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        pytest.param([piece("Revenue", 0, 40), piece("1,234", 80, 100)], True, id="a figure"),
        pytest.param(
            [piece("Provision", 0, 40), piece("85", 80, 90)],
            True,
            id="a small number under a row label",
        ),
        pytest.param(
            [piece("Particulars", 0, 40), piece("1", 80, 85), piece("year", 87, 100)],
            False,
            id="a small number under a column heading",
        ),
        pytest.param(
            [piece("Balance", 0, 40), piece("–", 80, 84), piece("–", 120, 124)],
            True,
            id="a labelled row of dashes",
        ),
        pytest.param([piece("2025", 80, 100), piece("2024", 120, 140)], False, id="years"),
        pytest.param([piece("1", 70, 75), piece("234567", 80, 120)], False, id="column numbers"),
    ],
)
def test_body_line(line: list[Piece], expected: bool) -> None:
    assert body_line(line, EDGE) is expected


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        pytest.param([piece("Trade", 0, 20), piece("payables", 22, 50)], True, id="one phrase"),
        pytest.param(
            [piece("21.", 0, 8), piece("Trade", 30, 50), piece("payables", 52, 80)],
            True,
            id="a hanging number's tab",
        ),
        pytest.param(
            [piece("Particulars", 0, 40), piece("2025", 90, 110)],
            False,
            id="a gap the width of a column",
        ),
        pytest.param([piece("2025", 90, 110)], False, id="starting right of the label column"),
    ],
)
def test_one_phrase(line: list[Piece], expected: bool) -> None:
    assert one_phrase(line, EDGE) is expected


def test_label_right_reaches_the_first_value_column() -> None:
    cells = [Cell("21.", 0, 0, 1, 1, (0, 0, 10, 8)), Cell("x", 1, 0, 2, 1, (0, 9, 12, 17))]
    lines = [[piece("Provision", 15, 50), piece("2,211", 120, 140)]]
    assert label_right(cells, lines, 0.0) == 119.0
    assert label_right([], [[piece("Note", 0, 20)]], 5.0) == 5.0


_TABLE = [
    [piece("(₹ in crore)", 200, 240)],
    [piece("Particulars", 0, 40), piece("2025", 150, 170), piece("2024", 200, 220)],
    [piece("Secured", 0, 30, bold=True)],
    [
        piece("Term", 0, 20),
        piece("loans", 22, 45),
        piece("1,000", 150, 170),
        piece("900", 205, 220),
    ],
]


def test_header_rows_stop_at_the_first_value_line_less_its_section_label() -> None:
    assert header_rows(_TABLE, EDGE) == 2


def test_a_table_printing_no_value_has_no_header_to_find() -> None:
    assert header_rows([[piece("Name", 0, 20)], [piece("Director", 0, 30)]], EDGE) is None


def _line(
    label: str, x: float = 0.0, bold: bool = False, values: bool = False, numbered: bool = False
) -> Line:
    return Line(label + (" 100" if values else ""), label, x, numbered, bold, values)


@pytest.mark.parametrize(
    ("lines", "i", "expected"),
    [
        pytest.param(
            [_line("Other Financial Assets at Amortised", values=True), _line("cost")],
            1,
            "up",
            id="a lowercase second line",
        ),
        pytest.param(
            [_line("Total outstanding dues of", values=True), _line("Micro enterprises")],
            1,
            "up",
            id="the line above ends on a connective",
        ),
        pytest.param(
            [_line("Bonds (cumulative", values=True), _line("Redeemable)")],
            1,
            "up",
            id="the line above leaves a bracket open",
        ),
        pytest.param(
            [_line("National Bank for Agriculture and"), _line("Rural Development")],
            0,
            "down",
            id="ending on a connective",
        ),
        pytest.param(
            [_line("Investment in deposits"), _line("", values=True), _line("(original maturity)")],
            0,
            "down",
            id="wrapped around its own values",
        ),
        pytest.param(
            [_line("Commercial vehicle"), _line("Undertaking", values=True)],
            0,
            "down",
            id="a plain label over a row at its indent",
        ),
        pytest.param(
            [_line("Secured", bold=True), _line("Term loans", values=True)],
            0,
            "none",
            id="a bold section label",
        ),
        pytest.param(
            [_line("Secured:"), _line("Term loans", values=True)],
            0,
            "none",
            id="a label ending in a colon",
        ),
        pytest.param(
            [_line("Investments"), _line("Mutual funds", x=20, values=True)],
            0,
            "none",
            id="a row indented under it",
        ),
        pytest.param(
            [_line("Revenue", values=True), _line("(a) Others", numbered=True)],
            1,
            "none",
            id="a numbered line starts its own row",
        ),
    ],
)
def test_wrap(lines: list[Line], i: int, expected: str) -> None:
    assert wrap(lines, i) == expected


def test_read_line_splits_label_from_values() -> None:
    line = read_line(
        [
            piece("(a)", 0, 10),
            piece("Loans", 20, 40),
            piece("1,234", 150, 170),
            piece("–", 200, 204),
        ],
        EDGE,
    )
    assert (line.label, line.text_x, line.numbered, line.values) == ("(a) Loans", 20, True, True)


def test_rows_of_joins_wrapped_labels_and_keeps_every_cell() -> None:
    body = [
        [
            piece("Other", 0, 20),
            piece("Financial", 22, 50),
            piece("Assets", 52, 59),
            piece("741", 150, 165),
            piece("1,149", 200, 220),
        ],
        [piece("cost", 0, 20)],
        [piece("Others", 0, 30), piece("420", 150, 165), piece("399", 205, 220)],
    ]
    columns = [[0, 0, 0, 1, 2], [0], [0, 1, 2]]
    rows = rows_of(body, columns, EDGE, first=3)
    assert [(r.label, r.lines) for r in rows] == [
        ("Other Financial Assets cost", [3, 4]),
        ("Others", [5]),
    ]
    assert rows[0].cells == {0: "Other Financial Assets cost", 1: "741", 2: "1,149"}
    assert rows[0].values == {1: (741.0, 0), 2: (1149.0, 0)}


def test_rows_of_carries_a_label_down_into_its_row() -> None:
    body = [
        [piece("Commercial", 0, 40), piece("vehicle", 42, 59)],
        [piece("undertaking", 0, 50), piece("690", 150, 165)],
    ]
    [row] = rows_of(body, [[0, 0], [0, 1]], EDGE)
    assert (row.label, row.values, row.lines) == (
        "Commercial vehicle undertaking",
        {1: (690.0, 0)},
        [0, 1],
    )


def test_a_label_carried_down_takes_the_lowercase_line_below_not_the_row_above() -> None:
    body = [
        [piece("Revenue", 0, 30), piece("100", 150, 165)],
        [piece("National", 0, 30), piece("Bank", 32, 45), piece("and", 47, 58)],
        [piece("rural", 0, 20), piece("development", 22, 58)],
        [piece("Others", 0, 30), piece("5", 150, 155)],
    ]
    rows = rows_of(body, [[0, 1], [0, 0, 0], [0, 0], [0, 1]], EDGE)
    assert [r.label for r in rows] == ["Revenue", "National Bank and rural development", "Others"]
