"""Chinese line breaking with kinsoku rules."""
from __future__ import annotations

from cjkwrap import kinsoku_split

CANNOT_START = "，。；：、）”’？！"
CANNOT_END = "（“‘《"


def _lines(text: str, width: float) -> list[str]:
    return [line for _, line in kinsoku_split(text, [10.0] * len(text), width,
                                              CANNOT_START, CANNOT_END)]


def test_fills_lines_greedily():
    assert _lines("一二三四五六", 30) == ["一二三", "四五六"]


def test_closing_mark_never_opens_a_line():
    assert _lines("一二三，四五", 30) == ["一二", "三，四", "五"]


def test_two_closing_marks_push_back_together():
    lines = _lines("一二”，三四五", 30)
    assert all(not line.startswith(tuple(CANNOT_START)) for line in lines)
    assert "".join(lines) == "一二”，三四五"


def test_opening_mark_never_ends_a_line():
    assert _lines("一二（三四", 30) == ["一二", "（三四"]


def test_latin_word_is_not_cut():
    assert _lines("ab cdef", 50) == ["ab", "cdef"]


def test_reports_unused_width_per_line():
    split = kinsoku_split("一二三，四五", [10.0] * 6, 30, CANNOT_START, CANNOT_END)
    assert [space for space, _ in split] == [10.0, 0.0, 20.0]


def test_accepts_per_line_widths():
    assert _lines("一二三四五", [20, 30]) == ["一二", "三四五"]
