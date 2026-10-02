"""Markdown rendition: structure, map index, and Obsidian flavor."""
from __future__ import annotations

import pytest
from PIL import Image

from content_schema import brief_from_dict
from md_builder import build_markdown


@pytest.fixture
def plate(tmp_path):
    path = tmp_path / "maps" / "plate.png"
    path.parent.mkdir()
    Image.new("L", (10, 10), 255).save(path)
    return path


def _render(tmp_path, brief_dict, plate, flavor):
    brief = brief_from_dict(brief_dict)
    labels = {"article:0": "1", "article_end:0": "2", "notes:first": "6",
              "annex:last": "A3"}
    out = tmp_path / "PDB.md"
    build_markdown(brief, out, article_maps={0: plate}, annex_map=plate,
                   labels=labels, flavor=flavor)
    return out.read_text(encoding="utf-8")


def test_gfm_structure(tmp_path, brief_dict, plate):
    md = _render(tmp_path, brief_dict, plate, "gfm")
    assert "# The President’s Daily Brief" in md
    assert "## Table of Contents" in md
    assert "*(Page 1)*" in md
    assert "## Map Index" in md
    assert "](maps/plate.png)" in md
    assert "## NOTES" in md
    assert "## Annex: Iran after the ceasefire" in md


def test_redaction_rendered_as_withheld_block(tmp_path, brief_dict, plate):
    md = _render(tmp_path, brief_dict, plate, "gfm")
    assert "[REDACTED" not in md
    assert "`25X1`" in md


def test_note_and_annex_summaries_present(tmp_path, brief_dict, plate):
    md = _render(tmp_path, brief_dict, plate, "gfm")
    assert "Poland's coalition talks have stalled." in md
    assert "The ceasefire has bought time but not a settlement." in md


def test_obsidian_flavor(tmp_path, brief_dict, plate):
    md = _render(tmp_path, brief_dict, plate, "obsidian")
    assert md.startswith("---\n")
    assert "![[plate.png]]" in md
    assert "[[#Middle East: MIDDLE EAST: TALKS CONTINUE|Middle East]]" in md
    assert "> [!abstract]" in md
