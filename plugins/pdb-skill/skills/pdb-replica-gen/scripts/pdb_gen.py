#!/usr/bin/env python3
"""Render a bilingual PDB replica from a content JSON file.

By default the only output is the PDF: map plates are rendered to a
scratch folder, embedded, and discarded. Map images are kept only when
asked for (--maps-dir), or when Markdown is written, since the Markdown
links to them.

The destination and format defaults come from the plugin's user
configuration, which SKILL.md passes as --out-dir/--format. Outside a
plugin those placeholders arrive unexpanded ("${user_config.output_dir}")
and are treated as unset.

Exit codes: 0 ok, 2 bad or missing content, 3 map failure with
--strict-maps, 4 fonts unavailable, 5 output could not be written.
"""
from __future__ import annotations

import argparse
import re
import sys
import tempfile
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
FORMATS = ("pdf", "markdown", "both")
MD_FLAVORS = ("obsidian", "gfm")
_PLACEHOLDER = re.compile(r"^\$\{[^}]*\}$")

MapSet = tuple[dict[int, Path], Path | None]


def _configured(value: str | None) -> str | None:
    """None for empty values and unexpanded ${...} placeholders."""
    if value is None or not value.strip() or _PLACEHOLDER.match(value.strip()):
        return None
    return value.strip()


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in text).strip("_").lower()[:40]


def _parse(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate a PDB replica.")
    p.add_argument("--content", required=True,
                   help="content JSON matching content_schema.Brief")
    dest = p.add_mutually_exclusive_group()
    dest.add_argument("--out", help="output PDF path")
    dest.add_argument("--out-dir", help="output directory; files are named "
                      "PDB_<date>.pdf (and .md)")
    p.add_argument("--format", default=None,
                   help="pdf (default; maps embedded), markdown (Markdown plus "
                        "a maps/ folder), or both")
    p.add_argument("--md-flavor", choices=MD_FLAVORS, default="obsidian",
                   help="Markdown style when Markdown is written (default obsidian)")
    p.add_argument("--md-out", help="Markdown path (default: PDF path with .md)")
    p.add_argument("--maps-dir", help="also keep the map PNGs in this folder")
    p.add_argument("--no-maps", action="store_true", help="skip cia-map-gen calls")
    p.add_argument("--strict-maps", action="store_true",
                   help="exit 3 if any map fails to render")
    args = p.parse_args(argv)
    fmt = _configured(args.format) or "pdf"
    if fmt not in FORMATS:
        p.error(f"--format must be one of {', '.join(FORMATS)}")
    return argparse.Namespace(**{**vars(args), "format": fmt})


def _render_maps(brief: Brief, maps_dir: Path, strict: bool) -> MapSet | None:
    """Render article and annex plates; None signals a strict failure."""
    article_maps: dict[int, Path] = {}
    for i, art in enumerate(brief.articles):
        if not art.map_prompt:
            continue
        out = maps_dir / f"{brief.date}_{i:02d}_{_slug(art.map_prompt)}.png"
        got = generate_map(art.map_prompt, out, title=art.map_title)
        print(f"[map] {'rendered ' + art.map_prompt if got else 'FAILED: ' + art.map_prompt}")
        if got:
            article_maps = {**article_maps, i: got}
        elif strict:
            return None
    annex_map = None
    if brief.annex and brief.annex.map_prompt:
        out = maps_dir / f"{brief.date}_annex_{_slug(brief.annex.map_prompt)}.png"
        annex_map = generate_map(brief.annex.map_prompt, out, title=brief.annex.map_title)
        print(f"[map] {'rendered annex map' if annex_map else 'FAILED: annex map'}")
        if annex_map is None and strict:
            return None
    return article_maps, annex_map


def _out_path(args: argparse.Namespace, brief: Brief) -> Path:
    if args.out:
        return Path(args.out).expanduser().resolve()
    out_dir = _configured(args.out_dir)
    base = Path(out_dir).expanduser() if out_dir else DEFAULT_OUT_DIR
    return base.resolve() / f"PDB_{brief.date}.pdf"


def _maps_home(args: argparse.Namespace, out_path: Path, scratch: Path) -> tuple[Path, bool]:
    """Where plates are rendered, and whether they are kept afterwards."""
    if args.maps_dir:
        return Path(args.maps_dir).expanduser().resolve(), True
    if args.format != "pdf":
        return out_path.parent / "maps", True     # the Markdown links to them
    return scratch, False


def _write(args: argparse.Namespace, brief: Brief, out_path: Path,
           maps: MapSet) -> list[str] | int:
    """Write the requested files; a list of report lines, or an exit code."""
    article_maps, annex_map = maps
    report: list[str] = []
    labels: dict[str, str] | None = None
    if args.format in ("pdf", "both"):
        try:
            labels = build_pdf(brief, out_path, article_maps, annex_map)
        except RuntimeError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 4
        except _OUTPUT_ERRORS as exc:
            print(f"error: could not write {out_path}: {exc}", file=sys.stderr)
            return 5
        report.append(f"PDF written: {out_path}")
    if args.format in ("markdown", "both"):
        md_path = (Path(args.md_out).expanduser().resolve() if args.md_out
                   else out_path.with_suffix(".md"))
        try:
            build_markdown(brief, md_path, article_maps, annex_map, labels,
                           args.md_flavor)
        except _OUTPUT_ERRORS as exc:
            print(f"error: could not write {md_path}: {exc}", file=sys.stderr)
            return 5
        report.append(f"Markdown written: {md_path}")
    return report


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
    out_path = _out_path(args, brief)

    with tempfile.TemporaryDirectory(prefix="pdb-maps-") as scratch:
        maps_dir, keep_maps = _maps_home(args, out_path, Path(scratch))
        maps: MapSet | None = ({}, None)
        if not args.no_maps:
            maps = _render_maps(brief, maps_dir, args.strict_maps)
            if maps is None:
                return 3
        result = _write(args, brief, out_path, maps)
    if isinstance(result, int):
        return result
    if keep_maps and (maps[0] or maps[1]):
        result.append(f"Map images kept in: {maps_dir}")
    print("\n".join(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
