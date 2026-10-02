"""Road/railroad selection for cia-map-gen plates (trunk routes only)."""
from __future__ import annotations

import importlib.util
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_SPEC = importlib.util.spec_from_file_location(
    "cia_linework",
    ROOT / "plugins" / "pdb-skill" / "skills" / "cia-map-gen" / "scripts" / "linework.py")
linework = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(linework)


@dataclass(frozen=True)
class _Geom:
    bounds: tuple[float, float, float, float]


@dataclass(frozen=True)
class _Rec:
    geometry: _Geom | None
    attributes: dict = field(default_factory=dict)


def test_wide_views_keep_only_major_routes():
    road, rail = linework.rank_limits((30.0, 25.0, 46.0, 40.0))
    assert road <= 4 and rail <= 6


def test_close_views_allow_more_detail():
    wide = linework.rank_limits((30.0, 25.0, 46.0, 40.0))
    close = linework.rank_limits((34.0, 31.0, 37.0, 34.0))
    assert close[0] > wide[0] and close[1] >= wide[1]


def test_selection_filters_rank_view_and_ferries():
    view = (0.0, 0.0, 10.0, 10.0)
    recs = [
        _Rec(_Geom((1, 1, 2, 2)), {"scalerank": 3, "featurecla": "Road"}),
        _Rec(_Geom((1, 1, 2, 2)), {"scalerank": 9, "featurecla": "Road"}),
        _Rec(_Geom((20, 20, 21, 21)), {"scalerank": 3, "featurecla": "Road"}),
        _Rec(_Geom((1, 1, 2, 2)), {"scalerank": 3, "featurecla": "Ferry"}),
        _Rec(None, {"scalerank": 3}),
    ]
    picked = linework.select(recs, view, max_rank=4)
    assert picked == [recs[0].geometry]


def test_missing_rank_is_treated_as_minor():
    rec = _Rec(_Geom((1, 1, 2, 2)), {"scalerank": None, "featurecla": "Road"})
    assert linework.select([rec], (0.0, 0.0, 10.0, 10.0), max_rank=4) == []
