#!/usr/bin/env python3
"""Render a bilingual PDB replica (PDF + Markdown, each with a map
index) from a content JSON file.

Defaults for the destination and primary format come from the plugin's
user configuration, which SKILL.md passes as --out-dir/--primary. When
the skill runs outside a plugin those placeholders arrive unexpanded
("${user_config.output_dir}") and are treated as unset.

Exit codes: 0 ok, 2 bad or missing content, 3 map failure with
--strict-maps, 4 fonts unavailable, 5 output could not be written.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from reportlab.platypus.doctemplate import LayoutError        # noqa: E402

from content_schema import Brief, ContentError, load_brief   # noqa: E402
from map_integration import generate_map                      # noqa: E402
from md_builder import build_markdown                         # noqa: E402
from pdf_builder import build_pdf                             # noqa: E402

# Failures while laying out or writing a file: a flowable too large for
# a page, a PDF held open by a viewer, a path on another drive.
_OUTPUT_ERRORS = (LayoutError, OSError, ValueError)

DEFAULT_OUT_DIR = Path.home() / "pdb-output"
FORMATS = ("pdf", "markdown")
_PLACEHOLDER = re.compile(r"^\$\{[^}]*\}$")


def _configured(value: str | None) -> str | None:
    """None for empty values and unexpanded ${...} placeholders."""
    if value is None or not value.strip() or _PLACEHOLDER.match(value.strip()):
        return None
    return value.strip()


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in text).strip("_").lower()[:40]


def _parse(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate a PDB replica (PDF + Markdown).")
    p.add_argument("--content", required=True,
                   help="content JSON matching content_schema.Brief")
    dest = p.add_mutually_exclusive_group()
    dest.add_argument("--out", help="output PDF path")
    dest.add_argument("--out-dir", help="output directory; files are named "
                      "PDB_<date>.pdf / .md with maps/ beside them")
    p.add_argument("--primary", default=None,
                   help="primary format: pdf (default) or markdown "
                        "(markdown-primary emits Obsidian-flavored Markdown)")
    p.add_argument("--md-out", help="Markdown path (default: PDF path with .md)")
    p.add_argument("--no-pdf", action="store_true",
                   help="Markdown only (TOC page references are omitted)")
    p.add_argument("--no-md", action="store_true", help="skip the Markdown rendition")
    p.add_argument("--no-maps", action="store_true", help="skip cia-map-gen calls")
    p.add_argument("--strict-maps", action="store_true",
                   help="exit 3 if any map fails to render")
    args = p.parse_args(argv)
    if args.no_pdf and args.no_md:
        p.error("--no-pdf and --no-md together leave nothing to generate")
    primary = _configured(args.primary)
    if primary is not None and primary not in FORMATS:
        p.error(f"--primary must be one of {', '.join(FORMATS)}")
    args.primary = primary or "pdf"
    return args


def _render_maps(brief: Brief, maps_dir: Path,
                 strict: bool) -> tuple[dict[int, Path], Path | None] | None:
    """Render article and annex plates; None signals a strict failure."""
    article_maps: dict[int, Path] = {}
    for i, art in enumerate(brief.articles):
        if not art.map_prompt:
            continue
        out = maps_dir / f"{brief.date}_{i:02d}_{_slug(art.map_prompt)}.png"
        got = generate_map(art.map_prompt, out, title=art.map_title)
        print(f"[map] {'generated ' + got.name if got else 'FAILED: ' + art.map_prompt}")
        if got:
            article_maps = {**article_maps, i: got}
        elif strict:
            return None
    annex_map = None
    if brief.annex and brief.annex.map_prompt:
        out = maps_dir / f"{brief.date}_annex_{_slug(brief.annex.map_prompt)}.png"
        annex_map = generate_map(brief.annex.map_prompt, out, title=brief.annex.map_title)
        print(f"[map] {'generated ' + annex_map.name if annex_map else 'FAILED: annex'}")
        if annex_map is None and strict:
            return None
    return article_maps, annex_map


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        # Chinese map prompts must not crash a cp1252/cp936 console.
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    args = _parse(argv)
    try:
        brief = load_brief(Path(args.content).expanduser())
    except ContentError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.out:
        out_path = Path(args.out).expanduser().resolve()
    else:
        out_dir = _configured(args.out_dir)
        base = Path(out_dir).expanduser() if out_dir else DEFAULT_OUT_DIR
        out_path = base.resolve() / f"PDB_{brief.date}.pdf"

    maps: tuple[dict[int, Path], Path | None] | None = ({}, None)
    if not args.no_maps:
        maps = _render_maps(brief, out_path.parent / "maps", args.strict_maps)
        if maps is None:
            return 3
    article_maps, annex_map = maps

    labels: dict[str, str] | None = None
    if not args.no_pdf:
        try:
            labels = build_pdf(brief, out_path, article_maps, annex_map)
        except RuntimeError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 4
        except _OUTPUT_ERRORS as exc:
            print(f"error: could not write {out_path}: {exc}", file=sys.stderr)
            return 5

    md_path: Path | None = None
    if not args.no_md:
        md_path = (Path(args.md_out).expanduser().resolve() if args.md_out
                   else out_path.with_suffix(".md"))
        flavor = "obsidian" if args.primary == "markdown" else "gfm"
        try:
            build_markdown(brief, md_path, article_maps, annex_map, labels, flavor)
        except _OUTPUT_ERRORS as exc:
            print(f"error: could not write {md_path}: {exc}", file=sys.stderr)
            return 5

    written = {"pdf": out_path if labels is not None else None, "markdown": md_path}
    order = [args.primary] + [f for f in FORMATS if f != args.primary]
    for rank, fmt in enumerate(order):
        if written[fmt] is not None:
            tag = " (primary)" if rank == 0 else ""
            print(f"{'PDF' if fmt == 'pdf' else 'Markdown'} written{tag}: {written[fmt]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
