"""Download + cache Natural Earth GeoJSON layers.

All data is public domain (Natural Earth). Files are fetched once from
GitHub's raw CDN and cached in `~/.cache/cia-map-gen/natural_earth/`.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
import zipfile
from pathlib import Path

CACHE_DIR = Path(
    os.environ.get("CIA_MAP_CACHE", Path.home() / ".cache" / "cia-map-gen" / "natural_earth")
)

BASE_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson"
)

LAYERS = {
    "countries": "ne_50m_admin_0_countries.geojson",
    "cities": "ne_50m_populated_places_simple.geojson",
    "rivers": "ne_10m_rivers_lake_centerlines.geojson",
    "lakes": "ne_50m_lakes.geojson",
    "marine": "ne_50m_geography_marine_polys.geojson",
}


def _download(name: str, dest: Path) -> None:
    url = f"{BASE_URL}/{name}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "cia-map-gen/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp, open(tmp, "wb") as out:
        while True:
            chunk = resp.read(65536)
            if not chunk:
                break
            out.write(chunk)
    tmp.rename(dest)


def ensure_layer(key: str) -> Path:
    if key not in LAYERS:
        raise KeyError(f"unknown layer {key!r}")
    path = CACHE_DIR / LAYERS[key]
    if not path.exists():
        print(f"[cia-map-gen] downloading {LAYERS[key]} ...", file=sys.stderr)
        _download(LAYERS[key], path)
    return path


def load_layer(key: str) -> dict:
    path = ensure_layer(key)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


REQUIRED_LAYERS = {"countries"}

# Shaded-relief raster — used only by --topo. Natural Earth 50m, grayscale.
RELIEF_URL = "https://naciscdn.org/naturalearth/50m/raster/SR_50M.zip"
RELIEF_ZIP = CACHE_DIR.parent / "SR_50M.zip"
RELIEF_TIF = CACHE_DIR.parent / "SR_50M.tif"


def ensure_relief() -> Path:
    """Download + extract the 50m shaded-relief GeoTIFF (covers whole globe,
    plate-carrée, grayscale). Cached at ~/.cache/cia-map-gen/SR_50M.tif."""
    if RELIEF_TIF.exists():
        return RELIEF_TIF
    RELIEF_TIF.parent.mkdir(parents=True, exist_ok=True)
    if not RELIEF_ZIP.exists():
        print(f"[cia-map-gen] downloading shaded relief (~11 MB) ...", file=sys.stderr)
        tmp = RELIEF_ZIP.with_suffix(".zip.part")
        req = urllib.request.Request(RELIEF_URL, headers={"User-Agent": "cia-map-gen/1.0"})
        with urllib.request.urlopen(req, timeout=120) as resp, open(tmp, "wb") as out:
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                out.write(chunk)
        tmp.rename(RELIEF_ZIP)
    with zipfile.ZipFile(RELIEF_ZIP) as zf:
        zf.extractall(RELIEF_TIF.parent)
    if not RELIEF_TIF.exists():
        raise FileNotFoundError(f"SR_50M.tif missing after extract at {RELIEF_TIF}")
    return RELIEF_TIF


def ensure_all() -> None:
    """Fetch all layers. Hard-fails only when a REQUIRED layer is unavailable;
    optional layers warn-and-continue so a partial cache still yields a map.
    """
    for k in LAYERS:
        try:
            ensure_layer(k)
        except Exception as e:
            if k in REQUIRED_LAYERS:
                raise
            print(f"[cia-map-gen] warning: optional layer {k!r} unavailable "
                  f"({e}); continuing without it.", file=__import__("sys").stderr)
