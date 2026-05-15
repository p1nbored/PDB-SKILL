#!/usr/bin/env python3
"""CIA-style map generator CLI.

Usage:
    python3 cia_map_gen.py --prompt "Egypt and the Red Sea" [--out path.png]
                           [--no-header] [--title "EGYPT"]

Exits 2 if the prompt cannot be resolved, 3 if data is unavailable.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path

# Make sibling modules importable when run directly.
HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from data_loader import ensure_all
from geocoder import resolve
from renderer import render


def _slug(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s.strip().lower())
    return s.strip("_")[:60] or "map"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Generate a CIA-style reference map.")
    p.add_argument("--prompt", required=True,
                   help='Geographic prompt, e.g. "Egypt and the Red Sea".')
    p.add_argument("--out", default=None, help="Output PNG path.")
    p.add_argument("--title", default=None,
                   help="Optional map title rendered in a boxed callout.")
    p.add_argument("--no-header", action="store_true",
                   help="Skip the CIA declassification header/footer.")
    p.add_argument("--topo", action="store_true",
                   help="Overlay shaded-relief terrain inside the focus "
                        "countries (matches CIA topographic plates).")
    p.add_argument(
        "--marker", action="append", default=[],
        metavar="LON,LAT,LABEL[,STYLE]",
        help="Place a custom marker. Style is one of: star (default), "
             "triangle, diamond, square, dot. Flag is repeatable.",
    )
    p.add_argument("--download", action="store_true",
                   help="Pre-download Natural Earth data and exit.")
    args = p.parse_args(argv)

    if args.download:
        ensure_all()
        print("natural earth data cached.")
        return 0

    try:
        ensure_all()
    except Exception as e:
        print(f"[cia-map-gen] failed to fetch map data: {e}", file=sys.stderr)
        return 3

    features, bbox, names = resolve(args.prompt)

    markers: list[tuple[float, float, str, str]] = []
    for raw in args.marker:
        parts = [p.strip() for p in raw.split(",")]
        if len(parts) < 3:
            print(f"[cia-map-gen] bad --marker {raw!r}; "
                  f"expected LON,LAT,LABEL[,STYLE]", file=sys.stderr)
            return 2
        try:
            lon = float(parts[0])
            lat = float(parts[1])
        except ValueError:
            print(f"[cia-map-gen] bad --marker {raw!r}; lon/lat must be numeric",
                  file=sys.stderr)
            return 2
        label = parts[2]
        style = parts[3] if len(parts) >= 4 else "star"
        markers.append((lon, lat, label, style))

    out = args.out or f"cia_map_{_slug(args.prompt)}_{int(time.time())}.png"
    out = os.path.abspath(out)

    render(
        focus_features=features,
        bbox=bbox,
        out_path=out,
        declass_header=not args.no_header,
        title=args.title,
        topo=args.topo,
        markers=markers,
    )
    print(out)
    print(f"focus: {', '.join(names)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
