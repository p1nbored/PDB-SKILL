"""Emit the PDB replica as a Markdown document.

Mirrors the PDF's 1975-76 structure -- cover block, Table of Contents,
Map Index, lead-in + body articles, NOTES, ANNEX -- with the maps
embedded as images and indexed with links. Page references reuse the
labels resolved during the PDF build so both outputs agree.

Two flavors:
- "gfm" (default): GitHub-style slug anchors and relative image links.
- "obsidian": YAML frontmatter properties, same-note wikilink anchors
  ([[#Heading|Display]], pipe escaped inside tables), callout lead-ins,
  and native ![[image.png]] embeds -- for viewing in an Obsidian vault.
"""
from __future__ import annotations

import json
import posixpath
from os.path import relpath
from pathlib import Path

from content_schema import Annex, Article, Brief, Note
from pdf_pages import classification_label, format_date
from textfmt import redaction_lines

TITLE = "The President’s Daily Brief"


def _anchor(text: str) -> str:
    """GitHub-style heading anchor."""
    keep = [c.lower() if c.isalnum() else ("-" if c in " -" else "")
            for c in text.strip()]
    return "".join(keep)


def _rel(target: Path, md_path: Path) -> str:
    return posixpath.join(*relpath(target, md_path.parent).split("\\"))


def _page_ref(labels: dict[str, str] | None, key: str, prefix: str = "Page") -> str:
    if not labels or key not in labels:
        return ""
    return f" *({prefix} {labels[key]})*"


def _link(heading: str, display: str, flavor: str, in_table: bool = False) -> str:
    """Same-note heading link. Obsidian resolves wikilinks against the
    raw heading text, not GFM slugs; the alias pipe is escaped in tables."""
    if flavor == "obsidian":
        sep = "\\|" if in_table else "|"
        return f"[[#{heading}{sep}{display}]]"
    return f"[{display}](#{_anchor(heading)})"


def _image(path: Path, title: str, out_path: Path, flavor: str) -> str:
    if flavor == "obsidian":
        return f"![[{path.name}]]"
    return f"![{title}]({_rel(path, out_path)})"


def _summary(article: Article) -> str:
    return article.summary_en or article.body_en[0].split(". ")[0].rstrip(".") + "."


def _pairs(body_en: tuple[str, ...], body_cn: tuple[str, ...]) -> list[str]:
    """Bilingual paragraphs; redaction markers become a withheld block."""
    out: list[str] = []
    for en, cn in zip(body_en, body_cn):
        lines = redaction_lines(en)
        if lines is not None:
            out += ["█" * 28 + " `25X1`", ""]
        else:
            out += [en, "", cn, ""]
    return out


def _front_matter(brief: Brief, flavor: str) -> list[str]:
    md: list[str] = []
    if flavor == "obsidian":
        # JSON strings are valid YAML double-quoted scalars, escapes included.
        title = json.dumps(f"{TITLE} -- {format_date(brief.date)}", ensure_ascii=False)
        md += ["---", f"title: {title}", f"date: {brief.date}",
               f"copy: {json.dumps(brief.copy_number, ensure_ascii=False)}",
               "tags:", "  - PDB", "  - daily-brief", "---", ""]
    return md + [
        f"> {brief.declass_header}", "",
        f"# {TITLE}", "",
        f"**{format_date(brief.date)}** -- Copy No. {brief.copy_number}", "",
        f"*FOR THE PRESIDENT ONLY* · ~~{classification_label(brief.classification)}~~ `25X1`",
        "", "---", "",
    ]


def _toc(brief: Brief, labels: dict[str, str] | None, flavor: str) -> list[str]:
    md = ["## Table of Contents", ""]
    for i, art in enumerate(brief.articles):
        link = _link(f"{art.region}: {art.title_en}", art.region, flavor)
        md.append(f"- **{link}:**  {_summary(art)}{_page_ref(labels, f'article:{i}')}")
        if art.summary_cn:
            md.append(f"  {art.summary_cn}")
    if brief.notes:
        topics = "; ".join(n.region for n in brief.notes)
        md.append(f"- **{_link('NOTES', 'Notes', flavor)}:**  {topics}"
                  f"{_page_ref(labels, 'notes:first')}")
    if brief.annex:
        heading = f"Annex: {brief.annex.title_en}"
        md.append(f"- At **{_link(heading, 'Annex', flavor)}** we discuss "
                  f"{brief.annex.title_en.strip()}.")
    return md + [""]


def _map_index(brief: Brief, article_maps: dict[int, Path], annex_map: Path | None,
               labels: dict[str, str] | None, out_path: Path, flavor: str) -> list[str]:
    rows: list[tuple[str, str, Path, str]] = []
    for i, art in enumerate(brief.articles):
        if article_maps.get(i):
            rows.append((art.map_title or art.region, f"{art.region}: {art.title_en}",
                         article_maps[i],
                         _page_ref(labels, f"article_end:{i}", "follows Page")))
    if annex_map and brief.annex:
        rows.append((brief.annex.map_title or brief.annex.title_en,
                     f"Annex: {brief.annex.title_en}", annex_map,
                     _page_ref(labels, "annex:last", "follows Page")))
    if not rows:
        return []
    md = ["## Map Index", "", "| Map | Accompanies | Plate |", "|-----|-------------|-------|"]
    for title, follows, path, ref in rows:
        plate = (f"[[{path.name}]]" if flavor == "obsidian"
                 else f"[{path.name}]({_rel(path, out_path)})")
        md.append(f"| {title}{ref} | {_link(follows, follows, flavor, True)} | {plate} |")
    return md + [""]


def _article(art: Article, plate: Path | None, out_path: Path, flavor: str) -> list[str]:
    md = [f"## {art.region}: {art.title_en}", "", f"### {art.title_cn}", ""]
    if flavor == "obsidian":
        md += [f"> [!abstract] {art.region.upper()}", f"> *{_summary(art)}*"]
        md += [f"> {art.summary_cn}"] if art.summary_cn else []
    else:
        md.append(f"> **{art.region.upper()}:**  *{_summary(art)}*")
        md += [">", f"> {art.summary_cn}"] if art.summary_cn else []
    md += [""] + _pairs(art.body_en, art.body_cn)
    if art.sources:
        md += [f"*(Sources: {'; '.join(art.sources)})*", ""]
    if plate:
        md += [_image(plate, art.map_title or art.region, out_path, flavor), ""]
    return md + ["---", ""]


def _note(note: Note) -> list[str]:
    md = [f"**{note.region}:**  *{note.summary_en}*" if note.summary_en
          else f"**{note.region}:**", ""]
    if note.summary_cn:
        md += [f"*{note.summary_cn}*", ""]
    return md + _pairs((note.text_en,), (note.text_cn,))


def _annex(annex: Annex, plate: Path | None, out_path: Path, flavor: str) -> list[str]:
    md = [f"## Annex: {annex.title_en}", "", f"### {annex.title_cn}", ""]
    if annex.summary_en:
        md += [f"*{annex.summary_en}*", ""]
        md += [f"*{annex.summary_cn}*", ""] if annex.summary_cn else []
    md += _pairs(annex.body_en, annex.body_cn)
    if plate:
        md += [_image(plate, annex.map_title or annex.title_en, out_path, flavor), ""]
    return md


def build_markdown(brief: Brief, out_path: Path,
                   article_maps: dict[int, Path] | None = None,
                   annex_map: Path | None = None,
                   labels: dict[str, str] | None = None,
                   flavor: str = "gfm") -> Path:
    maps = dict(article_maps or {})
    out_path.parent.mkdir(parents=True, exist_ok=True)
    md = (_front_matter(brief, flavor) + _toc(brief, labels, flavor)
          + _map_index(brief, maps, annex_map, labels, out_path, flavor)
          + ["---", ""])
    for i, art in enumerate(brief.articles):
        md += _article(art, maps.get(i), out_path, flavor)
    if brief.notes:
        md += ["## NOTES", ""]
        for note in brief.notes:
            md += _note(note)
        md += ["---", ""]
    if brief.annex:
        md += _annex(brief.annex, annex_map, out_path, flavor)
    md += [f"*FOR THE PRESIDENT ONLY -- {classification_label(brief.classification)}*", ""]
    out_path.write_text("\n".join(md), encoding="utf-8")
    return out_path
