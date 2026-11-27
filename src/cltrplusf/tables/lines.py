"""A table's printed lines: its words grouped into lines, joined into pieces, split at figures,
dates made whole, and each piece marked bold or not from its characters."""

from __future__ import annotations

import ctypes
import re
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c

from cltrplusf import line_rows
from cltrplusf.config import TABLE_LINE_GAP
from cltrplusf.filed import _opened
from cltrplusf.tables.model import Box, Piece

Glyph = tuple[float, float, bool]  # a character's middle on the page as displayed, and whether bold

_DAY = re.compile(r"^\d{1,2}(?:st|nd|rd|th)?,?$", re.I)
_MONTH = re.compile(r"^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?,?$", re.I)
_YEAR = re.compile(r"^(?:19|20)\d{2}[,.]?$")
_BOLD_NAMES = ("bold", "black", "heavy", "semibold", "demi")


def _font_name(text: pdfium.PdfTextPage, i: int) -> str:
    buf = ctypes.create_string_buffer(256)
    flags = ctypes.c_int(0)
    n = pdfium_c.FPDFText_GetFontInfo(text.raw, i, buf, 256, ctypes.byref(flags))
    return buf.value.decode("latin-1", "replace") if n else ""


def read_glyphs(path: Path, pages: Sequence[int]) -> dict[int, list[Glyph]]:
    """Every printed character of these 1-based pages: where it sits and whether its font is bold
    (by weight, or by a bold name when the weight is unset)."""
    pdf = _opened(path)
    out: dict[int, list[Glyph]] = {}
    try:
        for p in pages:
            page = pdf[p - 1]
            left, bottom, right, top = line_rows.crop_box(page)
            text = page.get_textpage()
            try:
                glyphs: list[Glyph] = []
                for i in range(text.count_chars()):
                    if chr(pdfium_c.FPDFText_GetUnicode(text.raw, i)).isspace():
                        continue
                    x1, y1, x2, y2 = text.get_charbox(i)
                    a, b, c, d = line_rows.displayed(
                        (x1 - left, y1 - bottom, x2 - left, y2 - bottom),
                        page.get_rotation(),
                        right - left,
                        top - bottom,
                    )
                    name = _font_name(text, i).lower()
                    weight = pdfium_c.FPDFText_GetFontWeight(text.raw, i)
                    bold = weight >= 600 or any(k in name for k in _BOLD_NAMES)
                    glyphs.append(((a + c) / 2, (b + d) / 2, bold))
                out[p] = glyphs
            finally:
                text.close()
    finally:
        pdf.close()
    return out


def bold(box: Box, glyphs: Sequence[Glyph]) -> bool:
    """Whether most characters inside the box are bold."""
    inside = Counter(
        g
        for x, y, g in glyphs
        if box[0] - 0.5 <= x <= box[2] + 0.5 and box[1] - 0.5 <= y <= box[3] + 0.5
    )
    return inside.most_common(1)[0][0] if inside else False


def dates_joined(pieces: Sequence[tuple[str, Box]]) -> list[tuple[str, Box]]:
    """Month, day and year pieces printed side by side made one piece ("March 31, 2025")."""
    out: list[tuple[str, Box]] = []
    i = 0
    while i < len(pieces):
        j = i
        kinds: list[str] = []
        while j < len(pieces) and len(kinds) < 3:
            t = pieces[j][0].strip()
            k = "m" if _MONTH.match(t) else "d" if _DAY.match(t) else "y" if _YEAR.match(t) else ""
            if not k or k in kinds:
                break
            kinds.append(k)
            j += 1
        if len(kinds) >= 2 and "m" in kinds and kinds != ["y", "m"]:
            group = pieces[i:j]
            box = (
                min(g[1][0] for g in group),
                min(g[1][1] for g in group),
                max(g[1][2] for g in group),
                max(g[1][3] for g in group),
            )
            out.append((" ".join(g[0] for g in group), box))
            i = j
        else:
            out.append(pieces[i])
            i += 1
    return out


def lines_in(
    box: Box, words: Sequence[line_rows.Word], glyphs: Sequence[Glyph] = ()
) -> list[list[Piece]]:
    """The printed lines whose words' middles fall inside the box, top to bottom, as pieces left
    to right; empty when no word does."""
    within = [
        w
        for w in words
        if box[0] - 1 <= (w[1][0] + w[1][2]) / 2 <= box[2] + 1
        and box[1] - 1 <= (w[1][1] + w[1][3]) / 2 <= box[3] + 1
    ]
    if not within:
        return []
    found, height = line_rows._lines(within, TABLE_LINE_GAP)
    out: list[list[Piece]] = []
    for line in found:
        ordered = sorted(line, key=lambda w: w[1][0])
        pieces = dates_joined(line_rows.split_figures(line_rows.joined(ordered, height)))
        out.append([Piece(t, b, bold(b, glyphs)) for t, b in pieces])
    return out
