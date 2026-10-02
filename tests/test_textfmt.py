"""Typewriter and CJK text conventions applied before typesetting."""
from __future__ import annotations

import pytest

from textfmt import (MAX_REDACTION_LINES, NBSP, cjk, escape, headline_case,
                     redaction_lines, typewriter, underline_term)


class TestHeadlineCase:
    def test_all_caps_title_gets_minor_words_lowercased(self):
        assert (headline_case("IRAN AFTER KHAMENEI: POLITICAL SUCCESSION AND REGIONAL POSTURE")
                == "Iran after Khamenei: Political Succession and Regional Posture")

    def test_acronyms_survive(self):
        assert headline_case("THE PLA AND THE US") == "The PLA and the US"

    def test_mixed_case_title_is_left_alone(self):
        assert headline_case("China after Mao") == "China after Mao"


class TestEscape:
    def test_escapes_markup_characters(self):
        assert escape("AT&T <b>") == "AT&amp;T &lt;b&gt;"


class TestTypewriter:
    def test_em_dash_becomes_double_hyphen(self):
        assert typewriter("August—the highest") == "August--the highest"

    def test_spaced_em_dash_closes_up(self):
        assert typewriter("rose — sharply") == "rose--sharply"

    def test_en_dash_in_number_range_becomes_hyphen(self):
        assert typewriter("pages 3–5") == "pages 3-5"

    def test_curly_quotes_become_straight(self):
        assert typewriter("“no” and ‘yes’") == "\"no\" and 'yes'"

    def test_two_spaces_after_sentence_end(self):
        assert typewriter("It held. The army") == f"It held.{NBSP} The army"

    def test_two_spaces_after_question_and_quote(self):
        out = typewriter('He asked "why?" Then left.')
        assert out == f'He asked "why?"{NBSP} Then left.'

    @pytest.mark.parametrize("text", [
        "Mr. Smith arrived", "Gen. Ali spoke", "the U.S. Navy",
        "J. Smith said", "e.g. Iran",
    ])
    def test_no_double_space_after_abbreviations(self, text):
        assert NBSP not in typewriter(text)

    def test_output_is_escaped(self):
        assert typewriter("AT&T fell. Then") == f"AT&amp;T fell.{NBSP} Then"


class TestCjk:
    def test_ascii_comma_between_han_becomes_fullwidth(self):
        assert cjk("维持,但") == "维持，但"

    def test_semicolon_and_colon_after_han(self):
        assert cjk("开放;两条") == "开放；两条"
        assert cjk("报道:伊朗") == "报道：伊朗"

    def test_number_grouping_untouched(self):
        assert cjk("约1,000人") == "约1,000人"

    def test_latin_clause_untouched(self):
        assert cjk("IMF, WTO") == "IMF, WTO"

    def test_parentheses_around_han(self):
        assert cjk("真主党(黎巴嫩)") == "真主党（黎巴嫩）"

    def test_output_is_escaped(self):
        assert cjk("A&B公司") == "A&amp;B公司"


class TestRedaction:
    @pytest.mark.parametrize("text,lines", [
        ("[REDACTED]", 4), ("[REDACTED:2]", 2), ("  [redacted: 6] ", 6),
    ])
    def test_parses_marker(self, text, lines):
        assert redaction_lines(text) == lines

    @pytest.mark.parametrize("text", ["Ordinary prose.", "[REDACTED] tail", "[REDACTED:0]"])
    def test_rejects_non_markers(self, text):
        assert redaction_lines(text) is None

    def test_oversized_box_is_capped_to_fit_a_page(self):
        assert redaction_lines("[REDACTED:200]") == MAX_REDACTION_LINES


class TestUnderlineTerm:
    def test_underlines_first_occurrence_case_insensitively(self):
        out = underline_term("Recently appointed Soviet premier.", "soviet")
        assert out == "Recently appointed <u>Soviet</u> premier."

    def test_possessive_form_is_underlined(self):
        out = underline_term("Poland's current troubles", "Poland")
        assert out.startswith("<u>Poland's</u>")

    def test_missing_term_returns_none(self):
        assert underline_term("Nothing here", "Chile") is None
