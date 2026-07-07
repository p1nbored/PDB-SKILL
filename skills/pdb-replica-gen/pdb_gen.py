#!/usr/bin/env python3
"""CLI entry: render a bilingual PDB replica (PDF + Markdown, each with
a map index) from a content JSON file."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from content_schema import Brief, load_brief   # noqa: E402
from map_integration import generate_map        # noqa: E402
from md_builder import build_markdown           # noqa: E402
from pdf_builder import build_pdf               # noqa: E402

# Default output destination chosen at install time (see SKILL.md,
# "Install-time output destination") and persisted next to the code.
CONFIG_PATH = HERE / "config.json"
FALLBACK_OUT_DIR = Path.home() / "pdb-output"


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in text).strip("_").lower()[:40]


def _load_config() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — missing/malformed config -> empty
        return {}


def _save_config(**updates: str) -> None:
    cfg = _load_config()
    cfg.update(updates)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")


def _default_out_dir() -> Path:
    cfg = _load_config()
    if "output_dir" in cfg:
        return Path(cfg["output_dir"]).expanduser()
    return FALLBACK_OUT_DIR


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Generate a PDB replica PDF.")
    p.add_argument("--content",
                   help="Path to content JSON matching content_schema.Brief")
    dest = p.add_mutually_exclusive_group()
    dest.add_argument("--out", help="Output PDF path")
    dest.add_argument("--out-dir",
                      help="Output directory; files are auto-named "
                           "PDB_<date>.pdf / PDB_<date>.md with maps/ beside them")
    p.add_argument("--set-output-dir", metavar="DIR",
                   help="Persist DIR as the default output directory "
                        "(written to config.json) and exit")
    p.add_argument("--set-primary-format", choices=["pdf", "markdown"],
                   help="Persist the primary output format "
                        "(written to config.json) and exit")
    p.add_argument("--primary", choices=["pdf", "markdown"], default=None,
                   help="Override the configured primary format for this run "
                        "(markdown-primary emits Obsidian-flavored Markdown)")
    p.add_argument("--no-pdf", action="store_true",
                   help="Skip the PDF (Markdown only; TOC page refs are "
                        "omitted since the PDF layout resolves them)")
    p.add_argument("--md-out", default=None,
                   help="Output Markdown path (default: PDF path with .md)")
    p.add_argument("--no-md", action="store_true",
                   help="Skip the Markdown rendition")
    p.add_argument("--no-maps", action="store_true",
                   help="Skip cia-map-gen calls (faster dry run)")
    p.add_argument("--strict-maps", action="store_true",
                   help="Exit 3 if any map invocation fails")
    args = p.parse_args(argv)

    if args.set_output_dir or args.set_primary_format:
        updates: dict[str, str] = {}
        if args.set_output_dir:
            updates["output_dir"] = str(Path(args.set_output_dir).expanduser())
        if args.set_primary_format:
            updates["primary_format"] = args.set_primary_format
        _save_config(**updates)
        for key, value in updates.items():
            print(f"{key} set: {value}")
        return 0

    if not args.content:
        p.error("--content is required (unless using --set-output-dir "
                "/ --set-primary-format)")
    if args.no_pdf and args.no_md:
        p.error("--no-pdf and --no-md together leave nothing to generate")

    content_path = Path(args.content).expanduser()
    if not content_path.exists():
        print(f"error: content file not found: {content_path}", file=sys.stderr)
        return 2
    try:
        brief: Brief = load_brief(content_path)
    except Exception as e:  # noqa: BLE001
        print(f"error: bad content JSON: {e}", file=sys.stderr)
        return 2

    if args.out:
        out_path = Path(args.out).expanduser().resolve()
    else:
        if args.out_dir:
            base = Path(args.out_dir).expanduser()
        else:
            base = _default_out_dir()
            print(f"[out] using default output directory: {base}")
        out_path = base.resolve() / f"PDB_{brief.date}.pdf"
    maps_dir = out_path.parent / "maps"

    article_maps: dict[int, Path] = {}
    annex_map: Path | None = None
    if not args.no_maps:
        for i, article in enumerate(brief.articles):
            if not article.map_prompt:
                continue
            map_out = maps_dir / f"{brief.date}_{i:02d}_{_slug(article.map_prompt)}.png"
            got = generate_map(article.map_prompt, map_out,
                               title=article.map_title)
            if got:
                article_maps[i] = got
                print(f"[map] generated {got.name}")
            else:
                print(f"[map] FAILED: {article.map_prompt}")
                if args.strict_maps:
                    return 3
        if brief.annex and brief.annex.map_prompt:
            map_out = maps_dir / f"{brief.date}_annex_{_slug(brief.annex.map_prompt)}.png"
            annex_map = generate_map(
                brief.annex.map_prompt, map_out,
                title=brief.annex.map_title,
            )
            if annex_map:
                print(f"[map] generated {annex_map.name}")
            elif args.strict_maps:
                return 3

    primary = args.primary or _load_config().get("primary_format", "pdf")

    labels: dict[str, str] | None = None
    if not args.no_pdf:
        try:
            labels = build_pdf(brief, out_path, article_maps=article_maps,
                               annex_map=annex_map)
        except RuntimeError as e:
            print(f"error: {e}", file=sys.stderr)
            return 4

    md_path: Path | None = None
    if not args.no_md:
        md_path = (Path(args.md_out).expanduser().resolve()
                   if args.md_out else out_path.with_suffix(".md"))
        build_markdown(brief, md_path, article_maps=article_maps,
                       annex_map=annex_map, labels=labels,
                       flavor="obsidian" if primary == "markdown" else "gfm")

    # Report the primary output first.
    pdf_line = f"PDF written: {out_path}" if labels is not None else None
    md_line = f"Markdown written: {md_path}" if md_path else None
    if primary == "markdown":
        lines = [md_line and md_line.replace("written:", "written (primary):"),
                 pdf_line]
    else:
        lines = [pdf_line and pdf_line.replace("written:", "written (primary):"),
                 md_line]
    for line in lines:
        if line:
            print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
