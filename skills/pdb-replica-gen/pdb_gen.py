#!/usr/bin/env python3
"""CLI entry: render a bilingual PDB replica PDF from a content JSON file."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from content_schema import Brief, load_brief   # noqa: E402
from map_integration import generate_map        # noqa: E402
from pdf_builder import build_pdf               # noqa: E402


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in text).strip("_").lower()[:40]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Generate a PDB replica PDF.")
    p.add_argument("--content", required=True,
                   help="Path to content JSON matching content_schema.Brief")
    p.add_argument("--out", required=True, help="Output PDF path")
    p.add_argument("--no-maps", action="store_true",
                   help="Skip cia-map-gen calls (faster dry run)")
    p.add_argument("--strict-maps", action="store_true",
                   help="Exit 3 if any map invocation fails")
    args = p.parse_args(argv)

    content_path = Path(args.content).expanduser()
    if not content_path.exists():
        print(f"error: content file not found: {content_path}", file=sys.stderr)
        return 2
    try:
        brief: Brief = load_brief(content_path)
    except Exception as e:  # noqa: BLE001
        print(f"error: bad content JSON: {e}", file=sys.stderr)
        return 2

    out_path = Path(args.out).expanduser().resolve()
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

    try:
        build_pdf(brief, out_path, article_maps=article_maps,
                  annex_map=annex_map)
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 4
    print(f"PDF written: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
