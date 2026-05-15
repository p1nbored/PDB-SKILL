"""Resolve a natural-language geographic prompt into focus countries + bbox.

No network calls, no LLMs; purely string matching against Natural Earth's
admin_0 attributes plus a small alias/region table.
"""

from __future__ import annotations

import difflib
import re
import sys
from typing import Iterable

from aliases import COUNTRY_ALIASES, NAMED_REGIONS
from data_loader import load_layer
from styles import BBOX_PAD


def _normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", s.lower()).strip()


_STOPWORDS = {
    "and", "or", "the", "of", "a", "an", "in", "on", "with", "near",
    "around", "between", "show", "map", "area", "region", "country",
    "countries", "surrounding", "plus", "also", "including", "include",
    "state", "states",
}


def _feature_names(feature: dict) -> list[str]:
    """Return matchable names for a country feature.

    ISO codes are intentionally excluded: 3-letter codes like 'AND' (Andorra)
    collide with English stopwords and cause false matches.
    """
    p = feature.get("properties", {})
    names: list[str] = []
    for k in ("NAME", "NAME_LONG", "NAME_EN", "ADMIN", "FORMAL_EN"):
        v = p.get(k)
        if isinstance(v, str) and v and v != "-99":
            names.append(v)
    return names


def _iter_coords(geom: dict) -> Iterable[tuple[float, float]]:
    t = geom.get("type")
    c = geom.get("coordinates")
    if t == "Polygon":
        for ring in c:
            for xy in ring:
                yield xy[0], xy[1]
    elif t == "MultiPolygon":
        for poly in c:
            for ring in poly:
                for xy in ring:
                    yield xy[0], xy[1]


def _bbox_of(features: list[dict]) -> tuple[float, float, float, float]:
    xs: list[float] = []
    ys: list[float] = []
    for feat in features:
        for x, y in _iter_coords(feat["geometry"]):
            xs.append(x)
            ys.append(y)
    if not xs:
        raise ValueError("no coordinates in features")
    return min(xs), min(ys), max(xs), max(ys)


def _pad_bbox(bbox: tuple[float, float, float, float], pad: float = BBOX_PAD):
    x0, y0, x1, y1 = bbox
    dx = (x1 - x0) * pad
    dy = (y1 - y0) * pad
    return (
        max(-180.0, x0 - dx),
        max(-90.0, y0 - dy),
        min(180.0, x1 + dx),
        min(90.0, y1 + dy),
    )


def resolve(prompt: str):
    """Return (focus_features, bbox, matched_names).

    `focus_features` is a list of admin_0 GeoJSON features that the prompt
    refers to. `bbox` is a padded lon/lat box enclosing them. `matched_names`
    is a list of display names actually matched.
    """
    countries = load_layer("countries")["features"]

    text = _normalize(prompt)

    # Apply aliases (longest first so multi-word aliases win)
    for alias in sorted(COUNTRY_ALIASES.keys(), key=len, reverse=True):
        if alias in text:
            text = text.replace(alias, _normalize(COUNTRY_ALIASES[alias]))

    # Named region lookup (exact phrase match)
    for region_name, (focus_list, override_bbox) in NAMED_REGIONS.items():
        if region_name in text:
            focus = [
                f for f in countries
                if any(_normalize(n) == _normalize(c) for n in _feature_names(f) for c in focus_list)
            ]
            if focus:
                bbox = override_bbox if override_bbox else _pad_bbox(_bbox_of(focus))
                return focus, bbox, [f["properties"].get("NAME") for f in focus]

    # Country-name matching
    matched: list[dict] = []
    matched_names: list[str] = []
    seen: set[str] = set()
    # Match longer names first to avoid partial substring collisions.
    name_index: list[tuple[str, dict, str]] = []
    for feat in countries:
        for n in _feature_names(feat):
            name_index.append((_normalize(n), feat, n))
    name_index.sort(key=lambda r: -len(r[0]))

    for norm, feat, display in name_index:
        if len(norm) < 3 or norm in _STOPWORDS:
            continue
        # whole-word match
        pattern = r"\b" + re.escape(norm) + r"\b"
        if re.search(pattern, text):
            props = feat["properties"]
            key = (
                props.get("ISO_A3") if props.get("ISO_A3") not in (None, "-99") else None
            ) or props.get("ADM0_A3") or props.get("NAME")
            if key in seen:
                continue
            seen.add(key)
            matched.append(feat)
            matched_names.append(display)

    if matched:
        bbox = _pad_bbox(_bbox_of(matched))
        return matched, bbox, matched_names

    # Nothing matched — offer fuzzy suggestions.
    all_names = sorted({n for feat in countries for n in _feature_names(feat) if len(n) > 2})
    guess = difflib.get_close_matches(text, [n.lower() for n in all_names], n=5, cutoff=0.5)
    print(
        f"[cia-map-gen] could not resolve prompt: {prompt!r}\n"
        f"  closest matches: {guess}",
        file=sys.stderr,
    )
    raise SystemExit(2)
