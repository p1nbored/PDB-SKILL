"""Immutable schema, validation, and loader for PDB content JSON."""
from __future__ import annotations

import dataclasses
import datetime
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ContentError(ValueError):
    """Content JSON is missing, malformed, or fails validation."""


@dataclass(frozen=True)
class Article:
    title_en: str
    title_cn: str
    region: str
    body_en: tuple[str, ...]
    body_cn: tuple[str, ...]
    sources: tuple[str, ...] = ()
    map_prompt: str | None = None
    map_title: str | None = None
    # One-sentence italic lead-in set in the narrow left column; also the
    # Table of Contents entry.
    summary_en: str | None = None
    summary_cn: str | None = None
    # Exemption markers (accepted for older content files; 25X1 is the
    # 1970s marker drawn beside redactions).
    compartments: tuple[str, ...] = ("25X1",)


@dataclass(frozen=True)
class Note:
    """Secondary item in the NOTES section."""
    region: str
    text_en: str
    text_cn: str
    summary_en: str | None = None
    summary_cn: str | None = None


@dataclass(frozen=True)
class Annex:
    title_en: str
    title_cn: str
    body_en: tuple[str, ...]
    body_cn: tuple[str, ...]
    summary_en: str | None = None
    summary_cn: str | None = None
    map_prompt: str | None = None
    map_title: str | None = None


@dataclass(frozen=True)
class Brief:
    date: str
    articles: tuple[Article, ...]
    notes: tuple[Note, ...] = ()
    annex: Annex | None = None
    classification: str = "TOP SECRET"
    copy_number: str = "2"
    volume_marker: str = "CIA/DI"
    declass_header: str = ""


_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_NESTED = frozenset({"articles", "notes", "annex"})


def _default_declass_header(date: str) -> str:
    # Same shape as the originals: CIA-RDP79T00024A000200050001-1.
    y, m, d = date.split("-")
    return ("Declassified in Part - Sanitized Copy Approved for Release "
            f"{y}/{m}/{d} : CIA-RDP{y[2:]}T00024A000{m}{d}00001-1")


def _checked(where: str, name: str, kind: str, value: Any) -> Any:
    """Coerce one field by its annotation; ContentError on a type mismatch."""
    if kind == "tuple[str, ...]":
        if not isinstance(value, (list, tuple)) or not all(
                isinstance(s, str) for s in value):
            raise ContentError(f"{where}.{name}: expected a list of strings")
        return tuple(value)
    if kind == "str" and not isinstance(value, str):
        raise ContentError(f"{where}.{name}: expected a string")
    if kind == "str | None" and value is not None and not isinstance(value, str):
        raise ContentError(f"{where}.{name}: expected a string or null")
    return value


def _fields(cls: type, raw: dict[str, Any], where: str,
            skip: frozenset[str] = frozenset()) -> dict[str, Any]:
    """Validated keyword arguments for *cls* from *raw* (minus *skip*)."""
    fields = {f.name: f for f in dataclasses.fields(cls) if f.name not in skip}
    present = {k: v for k, v in raw.items() if k not in skip}
    unknown = sorted(set(present) - set(fields))
    if unknown:
        raise ContentError(f"{where}: unknown field(s) {', '.join(unknown)}")
    missing = [n for n, f in fields.items()
               if f.default is dataclasses.MISSING and n not in present]
    if missing:
        raise ContentError(f"{where}: missing field(s) {', '.join(missing)}")
    return {k: _checked(where, k, str(fields[k].type), v) for k, v in present.items()}


def _build(cls: type, raw: Any, where: str) -> Any:
    if not isinstance(raw, dict):
        raise ContentError(f"{where}: expected an object")
    obj = cls(**_fields(cls, raw, where))
    if hasattr(obj, "body_en"):
        if not obj.body_en:
            raise ContentError(f"{where}: body_en needs at least one paragraph")
        if len(obj.body_en) != len(obj.body_cn):
            raise ContentError(
                f"{where}: body_en has {len(obj.body_en)} paragraphs but "
                f"body_cn has {len(obj.body_cn)}; they must pair 1:1")
    return obj


def _valid_date(value: Any) -> str:
    if not isinstance(value, str) or not _DATE.match(value):
        raise ContentError("date: expected YYYY-MM-DD")
    try:
        datetime.date.fromisoformat(value)
    except ValueError as exc:
        raise ContentError(f"date: {exc}") from exc
    return value


def brief_from_dict(raw: dict[str, Any]) -> Brief:
    """Validate a parsed content document and return an immutable Brief."""
    if not isinstance(raw, dict):
        raise ContentError("content: expected a JSON object")
    _valid_date(raw.get("date"))
    articles_raw = raw.get("articles")
    if not isinstance(articles_raw, list) or not articles_raw:
        raise ContentError("articles: at least one article is required")
    notes_raw = raw.get("notes") or []
    if not isinstance(notes_raw, list):
        raise ContentError("notes: expected a list")

    articles = tuple(_build(Article, a, f"articles[{i}]")
                     for i, a in enumerate(articles_raw))
    notes = tuple(_build(Note, n, f"notes[{i}]") for i, n in enumerate(notes_raw))
    annex_raw = raw.get("annex")
    annex = _build(Annex, annex_raw, "annex") if annex_raw else None

    scalars = _fields(Brief, raw, "content", skip=_NESTED)
    brief = Brief(articles=articles, notes=notes, annex=annex, **scalars)
    if not brief.declass_header:
        brief = dataclasses.replace(
            brief, declass_header=_default_declass_header(brief.date))
    return brief


def load_brief(path: str | Path) -> Brief:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContentError(f"cannot read content JSON: {exc}") from exc
    return brief_from_dict(raw)
