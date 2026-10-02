"""Choose which Natural Earth roads and railroads a plate shows.

The 1976 plates (Rhodesia 620402 9-76, Egypt 620375 8-76) carry only
trunk routes -- a few dozen lines per sheet -- not the full 10m network.
Natural Earth ranks every segment (scalerank: lower is more important),
so the cut-off tightens as the view widens.
"""
from __future__ import annotations

from typing import Any, Iterable

# (minimum view span in degrees, max road scalerank, max railroad scalerank)
RANK_BY_SPAN = (
    (12.0, 3, 4),
    (6.0, 4, 6),
    (0.0, 6, 7),
)


def rank_limits(view_bbox: tuple[float, float, float, float]) -> tuple[int, int]:
    """(road, railroad) scalerank cut-offs for a lon/lat view box."""
    x0, y0, x1, y1 = view_bbox
    span = max(x1 - x0, y1 - y0)
    for min_span, road, rail in RANK_BY_SPAN:
        if span >= min_span:
            return road, rail
    return RANK_BY_SPAN[-1][1], RANK_BY_SPAN[-1][2]


def select(records: Iterable[Any], view_bbox: tuple[float, float, float, float],
           max_rank: int) -> list[Any]:
    """Geometries of ranked, in-view, non-ferry records."""
    vx0, vy0, vx1, vy1 = view_bbox
    picked = []
    for rec in records:
        geom = rec.geometry
        attrs = rec.attributes
        if geom is None or attrs.get("featurecla") == "Ferry":
            continue
        rank = attrs.get("scalerank")
        if not isinstance(rank, (int, float)) or rank > max_rank:
            continue                      # unranked segments count as minor
        gx0, gy0, gx1, gy1 = geom.bounds
        if gx1 < vx0 or gx0 > vx1 or gy1 < vy0 or gy0 > vy1:
            continue
        picked.append(geom)
    return picked
