"""Content JSON loading and validation."""
from __future__ import annotations

import copy
import dataclasses
import json

import pytest

from content_schema import ContentError, brief_from_dict, load_brief


def test_loads_bundled_sample(sample_path):
    brief = load_brief(sample_path)
    assert brief.date == "2026-04-18"
    assert len(brief.articles) == 5
    assert brief.annex is not None


def test_models_are_immutable(brief_dict):
    brief = brief_from_dict(brief_dict)
    with pytest.raises(dataclasses.FrozenInstanceError):
        brief.date = "2027-01-01"  # type: ignore[misc]
    assert isinstance(brief.articles, tuple)
    assert isinstance(brief.articles[0].body_en, tuple)


def test_input_dict_is_not_mutated(brief_dict):
    snapshot = copy.deepcopy(brief_dict)
    brief_from_dict(brief_dict)
    assert brief_dict == snapshot


def test_optional_note_and_annex_summaries(brief_dict):
    brief = brief_from_dict(brief_dict)
    assert brief.notes[0].summary_en == "Poland's coalition talks have stalled."
    assert brief.notes[1].summary_en is None
    assert brief.annex.summary_cn.startswith("停火")


def test_mismatched_paragraph_counts_rejected(brief_dict):
    brief_dict["articles"][0]["body_cn"] = brief_dict["articles"][0]["body_cn"][:-1]
    with pytest.raises(ContentError, match="articles\\[0\\]"):
        brief_from_dict(brief_dict)


def test_bad_date_rejected(brief_dict):
    brief_dict["date"] = "18 April 2026"
    with pytest.raises(ContentError, match="date"):
        brief_from_dict(brief_dict)


def test_unknown_field_rejected(brief_dict):
    brief_dict["articles"][0]["headline"] = "x"
    with pytest.raises(ContentError, match="headline"):
        brief_from_dict(brief_dict)


def test_missing_required_field_rejected(brief_dict):
    del brief_dict["articles"][0]["region"]
    with pytest.raises(ContentError, match="region"):
        brief_from_dict(brief_dict)


def test_empty_articles_rejected(brief_dict):
    brief_dict["articles"] = []
    with pytest.raises(ContentError, match="articles"):
        brief_from_dict(brief_dict)


def test_default_declass_header_derived_from_date(brief_dict):
    brief = brief_from_dict(brief_dict)
    assert "CIA-RDP" in brief.declass_header
    assert brief.classification == "TOP SECRET"


@pytest.mark.parametrize("value", ["a whole paragraph as a string", 5, None, ["ok", 3]])
def test_body_must_be_a_list_of_strings(brief_dict, value):
    brief_dict["articles"][0]["body_en"] = value
    with pytest.raises(ContentError, match="body_en"):
        brief_from_dict(brief_dict)


def test_empty_body_rejected(brief_dict):
    brief_dict["articles"][0]["body_en"] = []
    brief_dict["articles"][0]["body_cn"] = []
    with pytest.raises(ContentError, match="at least one paragraph"):
        brief_from_dict(brief_dict)


@pytest.mark.parametrize("where,key", [
    (("articles", 0), "region"), (("articles", 0), "title_en"),
    (("notes", 0), "text_en"), ((), "classification"), ((), "copy_number"),
])
def test_string_fields_must_be_strings(brief_dict, where, key):
    target = brief_dict
    for step in where:
        target = target[step]
    target[key] = None
    with pytest.raises(ContentError, match=key):
        brief_from_dict(brief_dict)


def test_impossible_calendar_date_rejected(brief_dict):
    brief_dict["date"] = "2026-13-99"
    with pytest.raises(ContentError, match="date"):
        brief_from_dict(brief_dict)


def test_load_brief_rejects_invalid_json(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(ContentError):
        load_brief(bad)


def test_load_brief_roundtrip(tmp_path, brief_dict):
    path = tmp_path / "b.json"
    path.write_text(json.dumps(brief_dict, ensure_ascii=False), encoding="utf-8")
    assert load_brief(path) == brief_from_dict(brief_dict)
