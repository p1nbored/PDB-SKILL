"""Emit the PDB replica as a Markdown document.

Mirrors the PDF's 1971-76 structure — cover block, Table of Contents,
Map Index, hanging lead-in + body articles, NOTES, ANNEX — with the
maps embedded as images and indexed with links. Page references reuse
the labels resolved during the PDF build so both outputs agree.

Two flavors:
- "gfm" (default): GitHub-style slug anchors and relative image links.
- "obsidian": YAML frontmatter properties, same-note wikilink anchors
  ([[#Heading|Display]], pipe escaped inside tables), callout lead-ins,
  and native ![[image.png]] embeds — for viewing in an Obsidian vault.
"""
from __future__ import annotations

import posixpath
from os.path import relpath
from pathlib import Path

from content_schema import Brief

_MONTHS = ["January", "February", "March", "April", "May", "June",
           "July", "August", "September", "October", "November", "December"]


def _format_date(iso: str) -> str:
    try:
        y, m, d = iso.split("-")
        return f"{_MONTHS[int(m) - 1]} {int(d)}, {y}"
    except Exception:  # noqa: BLE001
        return iso


def _anchor(text: str) -> str:
    """GitHub-style heading anchor."""
    keep = [c.lower() if c.isalnum() else ("-" if c in " -" else "")
            for c in text.strip()]
    return "".join(keep).replace(" ", "-")


def _rel(target: Path, md_path: Path) -> str:
    return posixpath.join(*relpath(target, md_path.parent).split("\\"))


def _page_ref(labels: dict[str, str] | None, key: str,
              prefix: str = "Page") -> str:
    if not labels or key not in labels:
        return ""
    return f" *({prefix} {labels[key]})*"


def _link(heading: str, display: str, flavor: str,
          in_table: bool = False) -> str:
    """Same-note heading link. Obsidian resolves wikilinks against the
    raw heading text, not GFM slugs; the alias pipe must be escaped
    inside tables."""
    if flavor == "obsidian":
        sep = "\\|" if in_table else "|"
        return f"[[#{heading}{sep}{display}]]"
    return f"[{display}](#{_anchor(heading)})"


def _image(path: Path, title: str, out_path: Path, flavor: str) -> str:
    if flavor == "obsidian":
        return f"![[{path.name}]]"
    return f"![{title}]({_rel(path, out_path)})"


def build_markdown(brief: Brief, out_path: Path,
                   article_maps: dict[int, Path] | None = None,
                   annex_map: Path | None = None,
                   labels: dict[str, str] | None = None,
                   flavor: str = "gfm") -> Path:
    article_maps = article_maps or {}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    md: list[str] = []

    # --- Frontmatter properties (Obsidian) ---------------------------------
    if flavor == "obsidian":
        md += [
            "---",
            f"title: \"The President's Daily Brief — {_format_date(brief.date)}\"",
            f"date: {brief.date}",
            f"copy: \"{brief.copy_number}\"",
            "tags:",
            "  - PDB",
            "  - daily-brief",
            "---",
            "",
        ]

    # --- Cover block -------------------------------------------------------
    md.append(f"> {brief.declass_header}")
    md.append("")
    md.append("# The President's Daily Brief")
    md.append("")
    md.append(f"**{_format_date(brief.date)}** — Copy No. {brief.copy_number}")
    md.append("")
    md.append(f"*FOR THE PRESIDENT ONLY* · ~~{brief.classification.title()}~~ `25X1`")
    md.append("")
    md.append("---")
    md.append("")

    # --- Table of Contents -------------------------------------------------
    md.append("## Table of Contents")
    md.append("")
    for i, art in enumerate(brief.articles):
        summary = art.summary_en or (art.body_en[0].split(". ")[0] + ".")
        heading = f"{art.region}: {art.title_en}"
        ref = _page_ref(labels, f"article:{i}")
        link = _link(heading, art.region, flavor)
        md.append(f"- **{link}:**  {summary}{ref}")
        if art.summary_cn:
            md.append(f"  {art.summary_cn}")
    if brief.notes:
        topics = "; ".join(n.region for n in brief.notes)
        md.append(f"- **{_link('NOTES', 'Notes', flavor)}:**  {topics}"
                  f"{_page_ref(labels, 'notes:first')}")
    if brief.annex:
        annex_heading = f"Annex: {brief.annex.title_en}"
        md.append(f"- At **{_link(annex_heading, 'Annex', flavor)}** we discuss "
                  f"{brief.annex.title_en.strip()}.")
    md.append("")

    # --- Map Index ---------------------------------------------------------
    map_rows: list[tuple[str, str, Path, str]] = []
    for i, art in enumerate(brief.articles):
        m = article_maps.get(i)
        if m:
            title = art.map_title or art.region
            follows = f"{art.region}: {art.title_en}"
            map_rows.append((title, follows, m,
                             _page_ref(labels, f"article_end:{i}",
                                       prefix="follows Page")))
    if annex_map and brief.annex:
        title = brief.annex.map_title or brief.annex.title_en
        map_rows.append((title, f"Annex: {brief.annex.title_en}", annex_map,
                         _page_ref(labels, "annex:last",
                                   prefix="follows Page")))
    if map_rows:
        md.append("## Map Index")
        md.append("")
        md.append("| Map | Accompanies | Plate |")
        md.append("|-----|-------------|-------|")
        for title, follows, path, ref in map_rows:
            follows_link = _link(follows, follows, flavor, in_table=True)
            if flavor == "obsidian":
                plate_link = f"[[{path.name}]]"
            else:
                plate_link = f"[{path.name}]({_rel(path, out_path)})"
            md.append(f"| {title}{ref} | {follows_link} | {plate_link} |")
        md.append("")

    md.append("---")
    md.append("")

    # --- Articles ----------------------------------------------------------
    for i, art in enumerate(brief.articles):
        heading = f"{art.region}: {art.title_en}"
        md.append(f"## {heading}")
        md.append("")
        md.append(f"### {art.title_cn}")
        md.append("")
        summary = art.summary_en or (art.body_en[0].split(". ")[0] + ".")
        if flavor == "obsidian":
            md.append(f"> [!abstract] {art.region.upper()}")
            md.append(f"> *{summary}*")
            if art.summary_cn:
                md.append(f"> {art.summary_cn}")
        else:
            md.append(f"> **{art.region.upper()}:**  *{summary}*")
            if art.summary_cn:
                md.append(">")
                md.append(f"> {art.summary_cn}")
        md.append("")
        for en, cn in zip(art.body_en, art.body_cn):
            md.append(en)
            md.append("")
            md.append(cn)
            md.append("")
        if art.sources:
            md.append(f"*(Sources: {'; '.join(art.sources)})*")
            md.append("")
        m = article_maps.get(i)
        if m:
            title = art.map_title or art.region
            md.append(_image(m, title, out_path, flavor))
            md.append("")
        md.append("---")
        md.append("")

    # --- NOTES --------------------------------------------------------------
    if brief.notes:
        md.append("## NOTES")
        md.append("")
        for n in brief.notes:
            md.append(f"**{n.region}:**  {n.text_en}")
            md.append("")
            md.append(n.text_cn)
            md.append("")
        md.append("---")
        md.append("")

    # --- ANNEX ---------------------------------------------------------------
    if brief.annex:
        md.append(f"## Annex: {brief.annex.title_en}")
        md.append("")
        md.append(f"### {brief.annex.title_cn}")
        md.append("")
        for en, cn in zip(brief.annex.body_en, brief.annex.body_cn):
            md.append(en)
            md.append("")
            md.append(cn)
            md.append("")
        if annex_map:
            title = brief.annex.map_title or brief.annex.title_en
            md.append(_image(annex_map, title, out_path, flavor))
            md.append("")

    md.append(f"*FOR THE PRESIDENT ONLY — {brief.classification.title()}*")
    md.append("")

    out_path.write_text("\n".join(md), encoding="utf-8")
    return out_path
