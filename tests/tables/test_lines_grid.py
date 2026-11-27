"""`tables.lines` and `tables.grid`: pieces from words, dates made whole, bold read, and every
piece placed in a column."""

from __future__ import annotations

import pytest

from cltrplusf.line_rows import Word
from cltrplusf.tables.grid import bands, docling_columns, placed
from cltrplusf.tables.lines import bold, dates_joined, lines_in
from cltrplusf.tables.model import Box, Cell
from cltrplusf.testing import piece


def _box(left: float, right: float, top: float = 0.0) -> Box:
    return (left, top, right, top + 8.0)


@pytest.mark.parametrize(
    ("texts", "joined"),
    [
        pytest.param(["March", "31,", "2025"], ["March 31, 2025"], id="month day year"),
        pytest.param(["31st", "March,", "2026"], ["31st March, 2026"], id="day month year"),
        pytest.param(["31", "March"], ["31 March"], id="day and month"),
        pytest.param(["2025", "March"], ["2025", "March"], id="a year before a month stays apart"),
        pytest.param(["31,", "2025"], ["31,", "2025"], id="no month, no date"),
        pytest.param(
            ["Revenue", "March", "2025", "1,234"],
            ["Revenue", "March 2025", "1,234"],
            id="a date among other pieces",
        ),
    ],
)
def test_dates_joined(texts: list[str], joined: list[str]) -> None:
    pieces = [(t, _box(i * 40, i * 40 + 30)) for i, t in enumerate(texts)]
    assert [t for t, _ in dates_joined(pieces)] == joined


def test_a_joined_date_is_boxed_by_its_parts() -> None:
    [(_, box)] = dates_joined([("March", _box(0, 20)), ("2025", _box(25, 45, top=1))])
    assert box == (0, 0, 45, 9)


@pytest.mark.parametrize(
    ("glyphs", "expected"),
    [
        pytest.param([(5.0, 4.0, True), (6.0, 4.0, True), (7.0, 4.0, False)], True, id="most bold"),
        pytest.param(
            [(5.0, 4.0, True), (6.0, 4.0, False), (7.0, 4.0, False)], False, id="most plain"
        ),
        pytest.param([(50.0, 4.0, True)], False, id="no character inside"),
    ],
)
def test_bold(glyphs: list[tuple[float, float, bool]], expected: bool) -> None:
    assert bold(_box(0, 10), glyphs) is expected


def _word(text: str, left: float, top: float, spaced: bool = True) -> Word:
    return (text, (left, top, left + 6.0 * len(text), top + 8.0), spaced)


def test_lines_in_reads_the_words_inside_the_box_line_by_line() -> None:
    words = [
        _word("Revenue", 10, 20),
        _word("100", 100, 20),
        _word("Other", 10, 40),
        _word("5", 100, 41),
        _word("Outside", 10, 200),
    ]
    lines = lines_in((0, 0, 200, 100), words, [(12.0, 24.0, True)])
    assert [[p.text for p in line] for line in lines] == [["Revenue", "100"], ["Other", "5"]]
    assert lines[0][0].bold and not lines[1][0].bold


def test_lines_in_an_empty_box_reads_nothing() -> None:
    assert lines_in((0, 0, 50, 50), [_word("Far", 300, 300)]) == []


def _cell(col: int, left: float, right: float, text: str = "x", span: int = 1) -> Cell:
    return Cell(text, 0, col, 1, col + span, _box(left, right))


def test_docling_columns_are_the_median_edges_of_one_column_cells() -> None:
    cells = [
        _cell(0, 10, 90),
        _cell(0, 12, 80),
        _cell(0, 11, 85),
        _cell(1, 100, 140),
        _cell(1, 0, 400, span=2),  # spanning: no column's edge
        _cell(1, 300, 400, text=" "),  # empty: no column's edge
    ]
    assert docling_columns(cells) == {0: (11, 85), 1: (100, 140)}


def test_bands_group_figure_edges_and_keep_those_printed_twice() -> None:
    lines = [
        [piece("Revenue", 0, 40), piece("1,000", 80, 100), piece("900", 150, 170)],
        [piece("Cost", 0, 30), piece("50", 88, 102), piece("40", 160, 171)],
        [piece("Other", 0, 30), piece("7", 250, 255)],
    ]
    assert bands(lines) == [101.0, 170.5]


def test_placed_puts_each_piece_in_the_column_it_overlaps_or_the_nearest() -> None:
    cells = [_cell(0, 0, 60), _cell(1, 70, 110), _cell(2, 120, 160)]
    lines = [[piece("Revenue", 0, 40), piece("100", 90, 108), piece("90", 140, 158)]]
    lines += [[piece("Note", 0, 20), piece("5", 112, 117)]]  # between two columns: the nearer
    assert placed(lines, cells) == [[0, 1, 2], [0, 1]]


def test_placed_splits_a_column_holding_two_printed_figure_columns() -> None:
    cells = [_cell(0, 0, 60), _cell(1, 70, 200)]  # Docling merged two figure columns into one
    lines = [
        [piece("Revenue", 0, 40), piece("100", 90, 110), piece("90", 170, 190)],
        [piece("Cost", 0, 30), piece("40", 98, 110), piece("30", 180, 190)],
    ]
    assert placed(lines, cells) == [[0, 1, 2], [0, 1, 2]]


def test_placed_with_no_docling_columns_puts_everything_in_one() -> None:
    assert placed([[piece("A", 0, 5), piece("1", 20, 25)]], []) == [[0, 0]]


def test_a_piece_overlapping_no_column_goes_to_the_nearest_by_middle() -> None:
    cells = [_cell(0, 0, 100), _cell(1, 105, 115)]
    assert placed([[piece("Label", 10, 40), piece("7", 101, 103)]], cells) == [[0, 1]]
