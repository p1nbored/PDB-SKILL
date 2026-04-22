"""Schema + loader for PDB content JSON."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Article:
    title_en: str
    title_cn: str
    region: str
    body_en: list[str]
    body_cn: list[str]
    sources: list[str] = field(default_factory=list)
    compartments: list[str] = field(default_factory=lambda: ["50X1"])
    map_prompt: str | None = None
    map_title: str | None = None
    # One-sentence pull-quote summary rendered in the narrow left column.
    summary_en: str | None = None
    summary_cn: str | None = None


@dataclass
class Note:
    """Short secondary-item paragraph inside the NOTES section."""
    region: str
    text_en: str
    text_cn: str


@dataclass
class Annex:
    title_en: str
    title_cn: str
    body_en: list[str]
    body_cn: list[str]
    map_prompt: str | None = None
    map_title: str | None = None


@dataclass
class Brief:
    date: str
    articles: list[Article]
    volume_marker: str = "CIA/DI"
    classification: str = "TOP SECRET"
    declass_header: str = (
        "Declassified in Part - Sanitized Copy Approved for Release 2026/04/18 "
        ": CIA-RDP99T00000A000200010001-0"
    )
    notes: list[Note] = field(default_factory=list)
    annex: Annex | None = None


def load_brief(path: str | Path) -> Brief:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    articles = [Article(**a) for a in raw.pop("articles", [])]
    notes = [Note(**n) for n in raw.pop("notes", [])]
    annex_raw = raw.pop("annex", None)
    annex = Annex(**annex_raw) if annex_raw else None
    return Brief(articles=articles, notes=notes, annex=annex, **raw)
