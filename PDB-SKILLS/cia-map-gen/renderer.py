"""Render a CIA-style black-and-white map PNG using cartopy.

Cold-War CIA declassified plate aesthetic: pure grayscale, clean black
linework on white, 10m Natural Earth borders/coastlines/rivers/lakes,
optional grayscale shaded relief (SR_50M) clipped to the focus country.
No fake hachures, no stylized terrain glyphs — the relief is the DEM.
"""

from __future__ import annotations

import datetime as _dt
import math
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.patheffects as path_effects
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch
from matplotlib.path import Path as MplPath

import cartopy.crs as ccrs
from cartopy.feature import NaturalEarthFeature
from cartopy.io import shapereader

from data_loader import load_layer
import styles as S


# --- GeoJSON -> Matplotlib path helpers -------------------------------------

def _polygon_patch(coords, **kw):
    """coords: list of rings [[lon,lat], ...]. First is outer, rest are holes."""
    verts, codes = [], []
    for ring in coords:
        if len(ring) < 3:
            continue
        verts.append((ring[0][0], ring[0][1]))
        codes.append(MplPath.MOVETO)
        for xy in ring[1:]:
            verts.append((xy[0], xy[1]))
            codes.append(MplPath.LINETO)
        verts.append((ring[0][0], ring[0][1]))
        codes.append(MplPath.CLOSEPOLY)
    if not verts:
        return None
    return PathPatch(MplPath(verts, codes), **kw)


def _add_geometry(ax, geom, **kw):
    t = geom.get("type")
    if t == "Polygon":
        p = _polygon_patch(geom["coordinates"], **kw)
        if p is not None:
            ax.add_patch(p)
    elif t == "MultiPolygon":
        for poly in geom["coordinates"]:
            p = _polygon_patch(poly, **kw)
            if p is not None:
                ax.add_patch(p)
    elif t == "LineString":
        xs = [c[0] for c in geom["coordinates"]]
        ys = [c[1] for c in geom["coordinates"]]
        ax.plot(xs, ys, **kw)
    elif t == "MultiLineString":
        for line in geom["coordinates"]:
            xs = [c[0] for c in line]
            ys = [c[1] for c in line]
            ax.plot(xs, ys, **kw)
    elif t == "Point":
        ax.plot(geom["coordinates"][0], geom["coordinates"][1],
                marker=kw.pop("marker", "o"), **kw)


def _geom_iter_coords(geom):
    t = geom.get("type")
    c = geom.get("coordinates")
    if t == "Polygon":
        for ring in c:
            for xy in ring:
                yield xy
    elif t == "MultiPolygon":
        for poly in c:
            for ring in poly:
                for xy in ring:
                    yield xy
    elif t == "LineString":
        for xy in c:
            yield xy
    elif t == "MultiLineString":
        for line in c:
            for xy in line:
                yield xy
    elif t == "Point":
        yield c


def _centroid_of_polygon(coords):
    """Average-vertex centroid of the first ring — used as a cheap fallback."""
    if not coords or not coords[0]:
        return None
    ring = coords[0]
    xs = [c[0] for c in ring]
    ys = [c[1] for c in ring]
    return (sum(xs) / len(xs), sum(ys) / len(ys))


def _clipped_centroid(geom, view_bbox):
    vx0, vy0, vx1, vy1 = view_bbox
    xs: list[float] = []
    ys: list[float] = []
    for x, y in _geom_iter_coords(geom):
        if vx0 <= x <= vx1 and vy0 <= y <= vy1:
            xs.append(x)
            ys.append(y)
    if not xs:
        return None
    return (sum(xs) / len(xs), sum(ys) / len(ys))


def _point_in_ring(x, y, ring):
    """Even-odd ray casting."""
    inside = False
    n = len(ring)
    if n < 3:
        return False
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)):
            xt = (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi
            if x < xt:
                inside = not inside
        j = i
    return inside


def _point_in_polygon(x, y, polygon):
    if not polygon or not _point_in_ring(x, y, polygon[0]):
        return False
    for hole in polygon[1:]:
        if _point_in_ring(x, y, hole):
            return False
    return True


def _point_in_geom(x, y, geom):
    t = geom.get("type")
    if t == "Polygon":
        return _point_in_polygon(x, y, geom["coordinates"])
    if t == "MultiPolygon":
        return any(_point_in_polygon(x, y, p) for p in geom["coordinates"])
    return False


def _pole_of_inaccessibility(geom, view_bbox, grid: int = 18):
    """Interior point of the visible part of `geom`, maximally far from
    the visible-polygon bbox edges. Approximation of pole of inaccessibility."""
    gb = _geom_bbox(geom)
    vx0, vy0, vx1, vy1 = view_bbox
    x0 = max(gb[0], vx0)
    y0 = max(gb[1], vy0)
    x1 = min(gb[2], vx1)
    y1 = min(gb[3], vy1)
    if x1 <= x0 or y1 <= y0:
        return None
    best = None
    best_score = -1.0
    for i in range(1, grid):
        for j in range(1, grid):
            x = x0 + (x1 - x0) * i / grid
            y = y0 + (y1 - y0) * j / grid
            if not _point_in_geom(x, y, geom):
                continue
            dx = min(x - x0, x1 - x)
            dy = min(y - y0, y1 - y)
            dvx = min(x - vx0, vx1 - x)
            dvy = min(y - vy0, vy1 - y)
            score = min(dx, dy) + 0.25 * min(dvx, dvy)
            if score > best_score:
                best_score = score
                best = (x, y)
    if best is None:
        return _clipped_centroid(geom, view_bbox)
    return best


# Back-compat alias (some callers may reference the old name).
_label_position = _pole_of_inaccessibility


def _visible_area(geom, view_bbox) -> float:
    """Cheap visible-area proxy: clipped-bbox area. Good enough for ranking."""
    gb = _geom_bbox(geom)
    vx0, vy0, vx1, vy1 = view_bbox
    w = max(0.0, min(gb[2], vx1) - max(gb[0], vx0))
    h = max(0.0, min(gb[3], vy1) - max(gb[1], vy0))
    return w * h


class _LabelSpace:
    """Track placed label bboxes (in axes-fraction coords) to avoid overlap."""

    def __init__(self, fig_w_in: float, fig_h_in: float,
                 ax_frac_w: float, ax_frac_h: float,
                 view_bbox: tuple[float, float, float, float]) -> None:
        self.ax_w_in = fig_w_in * ax_frac_w
        self.ax_h_in = fig_h_in * ax_frac_h
        self.vx0, self.vy0, self.vx1, self.vy1 = view_bbox
        self.vw = self.vx1 - self.vx0
        self.vh = self.vy1 - self.vy0
        self.placed: list[tuple[float, float, float, float]] = []

    def _bbox(self, x: float, y: float, text: str, fontsize: float,
              ha: str = "center", va: str = "center",
              pad_x: float = 0.25, pad_y: float = 0.2) -> tuple[float, float, float, float]:
        fx = (x - self.vx0) / self.vw
        fy = (y - self.vy0) / self.vh
        w = len(text) * 0.55 * fontsize / 72.0 / self.ax_w_in
        h = fontsize * 1.15 / 72.0 / self.ax_h_in
        w *= 1 + pad_x
        h *= 1 + pad_y
        if ha == "center":
            x0, x1 = fx - w / 2, fx + w / 2
        elif ha == "left":
            x0, x1 = fx, fx + w
        else:
            x0, x1 = fx - w, fx
        if va == "center":
            y0, y1 = fy - h / 2, fy + h / 2
        elif va == "top":
            y0, y1 = fy - h, fy
        else:
            y0, y1 = fy, fy + h
        return (x0, y0, x1, y1)

    def try_place(self, x: float, y: float, text: str, fontsize: float,
                  ha: str = "center", va: str = "center",
                  pad_x: float = 0.25, pad_y: float = 0.2) -> bool:
        bb = self._bbox(x, y, text, fontsize, ha, va, pad_x, pad_y)
        # Out-of-frame rejection.
        if bb[0] < 0 or bb[1] < 0 or bb[2] > 1 or bb[3] > 1:
            return False
        for pb in self.placed:
            if not (bb[2] < pb[0] or bb[0] > pb[2]
                    or bb[3] < pb[1] or bb[1] > pb[3]):
                return False
        self.placed.append(bb)
        return True


def _bbox_intersects(bbox, pt_bbox):
    return not (pt_bbox[2] < bbox[0] or pt_bbox[0] > bbox[2]
                or pt_bbox[3] < bbox[1] or pt_bbox[1] > bbox[3])


def _geom_bbox(geom):
    xs, ys = [], []
    for xy in _geom_iter_coords(geom):
        xs.append(xy[0])
        ys.append(xy[1])
    if not xs:
        return (0, 0, 0, 0)
    return (min(xs), min(ys), max(xs), max(ys))


# --- Focus-geometry matplotlib path (for DEM clip) --------------------------

def _focus_path(focus_features) -> MplPath | None:
    verts: list[tuple[float, float]] = []
    codes: list[int] = []
    for feat in focus_features:
        geom = feat["geometry"]
        if geom["type"] == "Polygon":
            polys = [geom["coordinates"]]
        elif geom["type"] == "MultiPolygon":
            polys = geom["coordinates"]
        else:
            continue
        for poly in polys:
            for ring in poly:
                if len(ring) < 3:
                    continue
                verts.append((ring[0][0], ring[0][1]))
                codes.append(MplPath.MOVETO)
                for xy in ring[1:]:
                    verts.append((xy[0], xy[1]))
                    codes.append(MplPath.LINETO)
                verts.append((ring[0][0], ring[0][1]))
                codes.append(MplPath.CLOSEPOLY)
    if not verts:
        return None
    return MplPath(verts, codes)


# --- Declass header / footer strip ------------------------------------------

def _draw_declass_header(fig) -> None:
    today = _dt.date.today().strftime("%Y/%m/%d")
    declass_text = (
        f"Declassified in Part - Sanitized Copy Approved for Release "
        f"{today} : CIA-RDP00T00000A000000000000-1"
    )
    fig.text(0.5, 0.965, declass_text,
             ha="center", va="center", color=S.DECLASS_TEXT,
             **S.FONT_DECLASS)
    fig.text(0.5, 0.035, declass_text,
             ha="center", va="center", color=S.DECLASS_TEXT,
             **S.FONT_DECLASS)


# --- Shaded-relief terrain ---------------------------------------------------

# Boundary feature classes that we render dashed because the frontier is
# unsettled / disputed / a claim line rather than an internationally agreed
# border. Natural Earth 10m uses the FEATURECLA column for this.
_DASHED_BOUNDARY_CLASSES = {
    "Disputed (please verify)",
    "Indefinite (please verify)",
    "Claim boundary",
    "Line of control (please verify)",
    "Breakaway",
    "Unrecognized",
}


def _apply_focus_clip(ax, img_artist, focus_features) -> None:
    """Clip a matplotlib AxesImage to the focus country polygons."""
    path = _focus_path(focus_features)
    if path is None:
        return
    patch = PathPatch(path, transform=ax.transData,
                      facecolor="none", edgecolor="none")
    ax.add_patch(patch)
    img_artist.set_clip_path(patch)


def _draw_topo_relief(ax, focus_features, view_bbox) -> None:
    """Draw grayscale shaded relief from the cached SR_50M.tif, clipped to
    the focus-country polygons. Pure CIA vintage plate aesthetic — the relief
    IS the DEM. No hachures, no vector glyphs, no stylization.
    """
    try:
        import rasterio
    except Exception as e:
        print(f"[cia-map-gen] --topo requires rasterio; skipping ({e})",
              file=sys.stderr)
        return
    from data_loader import ensure_relief
    try:
        tif = ensure_relief()
    except Exception as e:
        print(f"[cia-map-gen] could not fetch relief raster: {e}",
              file=sys.stderr)
        return

    vx0, vy0, vx1, vy1 = view_bbox
    with rasterio.open(tif) as src:
        # Read the whole grayscale band (plate-carrée global). It's a modest
        # ~11 MB; pulling it all is fine and keeps indexing simple.
        arr = src.read(1)
        bounds = src.bounds

    img = ax.imshow(
        arr,
        extent=[bounds.left, bounds.right, bounds.bottom, bounds.top],
        transform=ccrs.PlateCarree(),
        cmap="gray",
        origin="upper",
        zorder=2,
        alpha=0.85,
        interpolation="bilinear",
    )
    _apply_focus_clip(ax, img, focus_features)


# --- Borders, rivers, lakes, coastline --------------------------------------

def _draw_boundary_lines(ax, view_bbox) -> None:
    """Draw NE 10m admin_0_boundary_lines_land with dashed style for disputed /
    indefinite / claim lines and solid for recognized international borders.
    """
    try:
        path = shapereader.natural_earth(
            resolution="10m", category="cultural",
            name="admin_0_boundary_lines_land",
        )
    except Exception as e:
        print(f"[cia-map-gen] boundary_lines_land unavailable ({e})",
              file=sys.stderr)
        return

    vx0, vy0, vx1, vy1 = view_bbox
    reader = shapereader.Reader(path)
    for rec in reader.records():
        geom = rec.geometry
        if geom is None:
            continue
        try:
            gx0, gy0, gx1, gy1 = geom.bounds
        except Exception:
            continue
        if gx1 < vx0 or gx0 > vx1 or gy1 < vy0 or gy0 > vy1:
            continue
        fc = (rec.attributes.get("FEATURECLA")
              or rec.attributes.get("FEATURECL") or "")
        disputed = fc in _DASHED_BOUNDARY_CLASSES
        ls = (0, (4, 2)) if disputed else "-"
        ax.add_geometries(
            [geom], crs=ccrs.PlateCarree(),
            edgecolor="black", facecolor="none",
            linewidth=0.6, linestyle=ls, zorder=5,
        )


# --- Main render ------------------------------------------------------------

def render(
    focus_features: list[dict],
    bbox: tuple[float, float, float, float],
    out_path: str,
    declass_header: bool = True,
    title: str | None = None,
    topo: bool = False,
    markers: list[tuple[float, float, str, str]] | None = None,
) -> str:
    min_lon, min_lat, max_lon, max_lat = bbox

    # We still use data_loader for cities and marine polys (labels). Borders,
    # rivers, lakes, coastline all come from cartopy's 10m Natural Earth.
    try:
        marine = load_layer("marine")["features"]
    except Exception:
        marine = []
    try:
        cities = load_layer("cities")["features"]
    except Exception:
        cities = []
    # Countries only used to pick neighbor labels — cartopy draws the polygons.
    try:
        countries = load_layer("countries")["features"]
    except Exception:
        countries = []

    focus_ids = {
        f["properties"].get("ISO_A3") or f["properties"].get("NAME")
        for f in focus_features
    }

    fig = plt.figure(figsize=(S.FIG_WIDTH_IN, S.FIG_HEIGHT_IN),
                     dpi=S.DPI, facecolor=S.BG)

    if declass_header:
        _draw_declass_header(fig)

    # Map axes with cartopy PlateCarree projection.
    ax_rect = [0.08, 0.22, 0.84, 0.60]
    ax = fig.add_axes(ax_rect, projection=ccrs.PlateCarree())
    ax.set_extent([min_lon, max_lon, min_lat, max_lat], crs=ccrs.PlateCarree())
    ax.set_facecolor(S.SEA)
    for spine in ax.spines.values():
        spine.set_linewidth(S.LW_FRAME)
        spine.set_edgecolor(S.FRAME)

    view_bbox = (min_lon, min_lat, max_lon, max_lat)

    # --- Focus country white fill (below everything) ---
    # Add focus polygons as a white fill that other layers can sit on top of.
    for feat in focus_features:
        _add_geometry(ax, feat["geometry"],
                      facecolor="white",
                      edgecolor="none",
                      linewidth=0,
                      zorder=1)

    # --- Shaded relief (clipped to focus) ---
    if topo:
        _draw_topo_relief(ax, focus_features, view_bbox)

    # --- Natural Earth 10m features via cartopy ---
    # Countries: filled white with a thin black edge. We use this as the
    # *background* land polygon. Zorder above relief (so borders still show
    # as crisp lines even over gray hillshade that bleeds slightly).
    countries_feat = NaturalEarthFeature(
        category="cultural", name="admin_0_countries", scale="10m",
        facecolor="none", edgecolor="black",
    )
    ax.add_feature(countries_feat, linewidth=0.0, zorder=3)

    # Coastline (physical).
    coast_feat = NaturalEarthFeature(
        category="physical", name="coastline", scale="10m",
        facecolor="none", edgecolor="black",
    )
    ax.add_feature(coast_feat, linewidth=S.LW_COASTLINE, zorder=4)

    # Lakes (physical) — white fill, thin black outline.
    lakes_feat = NaturalEarthFeature(
        category="physical", name="lakes", scale="10m",
        facecolor="white", edgecolor="black",
    )
    ax.add_feature(lakes_feat, linewidth=0.4, zorder=4)

    # Rivers (physical) — CIA clean style: uniform 0.35 black.
    rivers_feat = NaturalEarthFeature(
        category="physical", name="rivers_lake_centerlines", scale="10m",
        facecolor="none", edgecolor="black",
    )
    ax.add_feature(rivers_feat, linewidth=0.35, zorder=4)

    # Borders with dashed-for-disputed handling.
    _draw_boundary_lines(ax, view_bbox)

    # Focus-country outline on top (heavier edge).
    for feat in focus_features:
        _add_geometry(ax, feat["geometry"],
                      facecolor="none",
                      edgecolor=S.LAND_FOCUS_EDGE,
                      linewidth=S.LW_COUNTRY_FOCUS,
                      zorder=6)

    # --- Gridlines (CIA plate style: fine dotted, top+right labels only) ---
    gl = ax.gridlines(
        draw_labels=True, dms=False, x_inline=False, y_inline=False,
        linewidth=S.LW_GRID, color=S.GRID_COLOR,
        linestyle=(0, (1, 3)), alpha=0.45,
    )
    gl.top_labels = True
    gl.right_labels = True
    gl.bottom_labels = False
    gl.left_labels = False
    gl.xlabel_style = {"size": 6, "color": "black"}
    gl.ylabel_style = {"size": 6, "color": "black"}

    # --- Label placement with dedupe + collision avoidance ---
    space = _LabelSpace(S.FIG_WIDTH_IN, S.FIG_HEIGHT_IN,
                        ax_rect[2], ax_rect[3], view_bbox)

    def _country_key(feat: dict) -> str:
        p = feat["properties"]
        return (p.get("ADMIN") or p.get("NAME") or p.get("NAME_LONG") or "").strip().lower()

    focus_labels: list[tuple[dict, float]] = []
    other_labels: list[tuple[dict, float]] = []
    seen_keys: set[str] = set()
    for feat in countries:
        gb = _geom_bbox(feat["geometry"])
        if not _bbox_intersects(view_bbox, gb):
            continue
        key = _country_key(feat)
        if not key or key in seen_keys:
            continue
        seen_keys.add(key)
        area = _visible_area(feat["geometry"], view_bbox)
        if area <= 0:
            continue
        iso = feat["properties"].get("ISO_A3") or feat["properties"].get("NAME")
        if iso in focus_ids:
            focus_labels.append((feat, area))
        else:
            other_labels.append((feat, area))
    focus_labels.sort(key=lambda t: -t[1])
    other_labels.sort(key=lambda t: -t[1])

    halo = ([path_effects.withStroke(linewidth=2.4, foreground="white")]
            if topo else None)

    # 1) Focus countries.
    for feat, _area in focus_labels:
        pos = _pole_of_inaccessibility(feat["geometry"], view_bbox)
        if pos is None:
            continue
        name = feat["properties"].get("NAME") or feat["properties"].get("ADMIN") or ""
        if space.try_place(pos[0], pos[1], name, S.FONT_COUNTRY_FOCUS["size"]):
            t = ax.text(pos[0], pos[1], name,
                        ha="center", va="center", color="black",
                        transform=ccrs.PlateCarree(),
                        zorder=10, **S.FONT_COUNTRY_FOCUS)
            if halo:
                t.set_path_effects(halo)

    # 2) Neighbor countries.
    for feat, area in other_labels:
        view_area = (max_lon - min_lon) * (max_lat - min_lat)
        if area / view_area < 0.004:
            continue
        pos = _pole_of_inaccessibility(feat["geometry"], view_bbox)
        if pos is None:
            continue
        name = feat["properties"].get("NAME") or feat["properties"].get("ADMIN") or ""
        if space.try_place(pos[0], pos[1], name, S.FONT_COUNTRY["size"]):
            t = ax.text(pos[0], pos[1], name,
                        ha="center", va="center", color="black",
                        transform=ccrs.PlateCarree(),
                        zorder=10, **S.FONT_COUNTRY)
            if halo:
                t.set_path_effects(halo)

    # 3) Marine labels.
    marine_sorted = sorted(
        (
            (feat, _visible_area(feat["geometry"], view_bbox))
            for feat in marine
            if _bbox_intersects(view_bbox, _geom_bbox(feat["geometry"]))
        ),
        key=lambda t: -t[1],
    )
    seen_marine: set[str] = set()
    for feat, _area in marine_sorted:
        name = (feat["properties"].get("name") or feat["properties"].get("NAME") or "").strip()
        if not name:
            continue
        nk = name.lower()
        if nk in seen_marine:
            continue
        pos = _pole_of_inaccessibility(feat["geometry"], view_bbox)
        if pos is None:
            pos = _clipped_centroid(feat["geometry"], view_bbox)
        if pos is None:
            continue
        if space.try_place(pos[0], pos[1], name, S.FONT_SEA["size"]):
            ax.text(pos[0], pos[1], name, ha="center", va="center",
                    color="#222222", transform=ccrs.PlateCarree(),
                    zorder=10, **S.FONT_SEA)
            seen_marine.add(nk)

    # 4) Custom markers (before cities so POI get priority).
    if markers:
        _draw_markers(ax, markers, view_bbox, space, halo)

    # 5) Cities.
    focus_iso2 = {f["properties"].get("ISO_A2") for f in focus_features}
    focus_adm0 = {f["properties"].get("ADMIN") for f in focus_features}

    def _city_rank(props: dict) -> tuple[int, int]:
        featurecla = props.get("featurecla") or ""
        is_cap = 0 if featurecla in S.CAPITAL_FEATURECLASS else 1
        return (is_cap, props.get("scalerank", 10))

    candidate_cities: list[dict] = []
    for feat in cities:
        coords = feat["geometry"]["coordinates"]
        cx, cy = coords[0], coords[1]
        if not (min_lon < cx < max_lon and min_lat < cy < max_lat):
            continue
        props = feat["properties"]
        scalerank = props.get("scalerank", 10)
        featurecla = (props.get("featurecla") or "")
        is_capital = featurecla in S.CAPITAL_FEATURECLASS
        city_iso2 = props.get("iso_a2") or props.get("adm0_a3")
        city_admin = props.get("adm0name") or props.get("sov0name")
        in_focus = (city_iso2 in focus_iso2) or (city_admin in focus_adm0)
        if not in_focus and not is_capital:
            continue
        if in_focus and scalerank > S.CITY_MAX_SCALERANK and not is_capital:
            continue
        candidate_cities.append(feat)
    candidate_cities.sort(key=lambda f: _city_rank(f["properties"]))
    MAX_CITIES = 14

    rendered = 0
    for feat in candidate_cities:
        if rendered >= MAX_CITIES:
            break
        coords = feat["geometry"]["coordinates"]
        cx, cy = coords[0], coords[1]
        props = feat["properties"]
        featurecla = (props.get("featurecla") or "")
        is_capital = featurecla in S.CAPITAL_FEATURECLASS
        city_iso2 = props.get("iso_a2") or props.get("adm0_a3")
        city_admin = props.get("adm0name") or props.get("sov0name")
        in_focus = (city_iso2 in focus_iso2) or (city_admin in focus_adm0)
        if is_capital and not in_focus:
            is_capital = False
        name = props.get("name") or props.get("NAME") or ""
        label_fontsize = (S.FONT_CAPITAL if is_capital else S.FONT_CITY)["size"]
        placed = False
        dx_small = (max_lon - min_lon) * 0.008
        dy_small = (max_lat - min_lat) * 0.012
        candidates = [
            (cx + dx_small, cy, "left", "center"),
            (cx - dx_small, cy, "right", "center"),
            (cx, cy - dy_small, "center", "top"),
            (cx, cy + dy_small, "center", "bottom"),
        ]
        for lx, ly, ha, va in candidates:
            if space.try_place(lx, ly, name, label_fontsize, ha=ha, va=va):
                if is_capital:
                    ax.plot(cx, cy, marker="s", markersize=5,
                            markerfacecolor="white", markeredgecolor="black",
                            markeredgewidth=0.9,
                            transform=ccrs.PlateCarree(), zorder=11)
                    t = ax.text(lx, ly, name, ha=ha, va=va, color="black",
                                transform=ccrs.PlateCarree(),
                                zorder=11, **S.FONT_CAPITAL)
                else:
                    ax.plot(cx, cy, marker="o", markersize=2.2,
                            markerfacecolor="black", markeredgecolor="black",
                            transform=ccrs.PlateCarree(), zorder=11)
                    t = ax.text(lx, ly, name, ha=ha, va=va, color="black",
                                transform=ccrs.PlateCarree(),
                                zorder=11, **S.FONT_CITY)
                if halo:
                    t.set_path_effects(halo)
                rendered += 1
                placed = True
                break
        if not placed and is_capital:
            ax.plot(cx, cy, marker="s", markersize=5,
                    markerfacecolor="white", markeredgecolor="black",
                    markeredgewidth=0.9,
                    transform=ccrs.PlateCarree(), zorder=11)

    # --- Title callout ---
    if title:
        ax.text(0.02, 0.965, title, transform=ax.transAxes,
                ha="left", va="top", fontsize=14, fontweight="bold",
                family="DejaVu Sans",
                bbox=dict(facecolor="white", edgecolor="black",
                          linewidth=0.8, boxstyle="square,pad=0.3"),
                zorder=12)

    # --- Scale bar cartouche ---
    _draw_scale_bar(ax, bbox)

    fig.savefig(out_path, dpi=S.DPI, facecolor=S.BG)
    plt.close(fig)
    return out_path


# --- Markers ----------------------------------------------------------------

def _draw_markers(ax, markers, view_bbox, space: "_LabelSpace",
                  halo=None) -> None:
    """Render user-supplied markers: (lon, lat, label, style) tuples."""
    style_map = {
        "star": dict(marker="*", markersize=11,
                     markerfacecolor="black", markeredgecolor="black"),
        "triangle": dict(marker="^", markersize=7,
                         markerfacecolor="black", markeredgecolor="black"),
        "diamond": dict(marker="D", markersize=5,
                        markerfacecolor="white", markeredgecolor="black",
                        markeredgewidth=1.0),
        "square": dict(marker="s", markersize=5,
                       markerfacecolor="white", markeredgecolor="black",
                       markeredgewidth=1.0),
        "dot": dict(marker="o", markersize=4,
                    markerfacecolor="black", markeredgecolor="black"),
    }
    vx0, vy0, vx1, vy1 = view_bbox
    for lon, lat, label, style in markers:
        if not (vx0 <= lon <= vx1 and vy0 <= lat <= vy1):
            print(f"[cia-map-gen] marker ({lon},{lat}) '{label}' is outside "
                  f"the view bbox — skipping.", file=sys.stderr)
            continue
        props = style_map.get(style.lower(), style_map["star"])
        ax.plot(lon, lat, transform=ccrs.PlateCarree(),
                zorder=12, **props)
        if not label:
            continue
        dx = (vx1 - vx0) * 0.018
        dy = (vy1 - vy0) * 0.022
        dxs = (vx1 - vx0) * 0.012
        dys = (vy1 - vy0) * 0.015
        candidates = [
            (lon + dx, lat, "left", "center"),
            (lon - dx, lat, "right", "center"),
            (lon, lat + dy, "center", "bottom"),
            (lon, lat - dy, "center", "top"),
            (lon + dxs, lat + dys, "left", "bottom"),
            (lon - dxs, lat + dys, "right", "bottom"),
            (lon + dxs, lat - dys, "left", "top"),
            (lon - dxs, lat - dys, "right", "top"),
        ]
        fontsize = S.FONT_MARKER["size"]
        for lx, ly, ha, va in candidates:
            if space.try_place(lx, ly, label, fontsize, ha=ha, va=va,
                               pad_x=0.45, pad_y=0.35):
                t = ax.text(lx, ly, label, ha=ha, va=va, color="black",
                            transform=ccrs.PlateCarree(),
                            zorder=13,
                            **S.FONT_MARKER,
                            bbox=dict(facecolor="white", edgecolor="black",
                                      linewidth=0.4,
                                      alpha=0.92, pad=1.2,
                                      boxstyle="round,pad=0.2"))
                if halo:
                    t.set_path_effects(halo)
                break


# --- Scale bar --------------------------------------------------------------

def _nice_distance(max_miles: float) -> int:
    """Pick a clean 1/2/5 x 10^k value under max_miles."""
    if max_miles <= 0:
        return 1
    exp = math.floor(math.log10(max_miles))
    base = 10 ** exp
    for mult in (5, 2, 1):
        cand = mult * base
        if cand <= max_miles:
            return int(cand)
    return int(base)


def _draw_scale_bar(ax, bbox):
    """Scale cartouche: bordered white box lower-left, miles + km bars."""
    min_lon, min_lat, max_lon, max_lat = bbox
    mean_lat = (min_lat + max_lat) / 2.0
    miles_per_deg_lon = 69.172 * max(0.1, math.cos(math.radians(mean_lat)))
    map_width_miles = (max_lon - min_lon) * miles_per_deg_lon
    target_miles = _nice_distance(map_width_miles * 0.22)
    target_km = _nice_distance(target_miles * 1.60934)

    miles_deg = target_miles / miles_per_deg_lon
    km_deg = (target_km / 1.60934) / miles_per_deg_lon

    dlon = max_lon - min_lon
    dlat = max_lat - min_lat

    inner_x0 = min_lon + dlon * S.SCALE_ANCHOR[0]
    inner_y0 = min_lat + dlat * S.SCALE_ANCHOR[1]
    bar_h = dlat * 0.006
    gap = dlat * 0.020

    bar_width = max(miles_deg, km_deg)
    cart_pad_x = dlon * 0.020
    cart_pad_y = dlat * 0.014
    cart_x0 = inner_x0 - cart_pad_x
    cart_y0 = inner_y0 - bar_h - dlat * 0.012 - cart_pad_y
    cart_x1 = inner_x0 + bar_width + cart_pad_x + dlon * 0.09
    cart_y1 = inner_y0 + gap + bar_h + dlat * 0.012 + cart_pad_y
    from matplotlib.patches import Rectangle
    ax.add_patch(Rectangle(
        (cart_x0, cart_y0), cart_x1 - cart_x0, cart_y1 - cart_y0,
        facecolor="white", edgecolor="black", linewidth=0.7,
        transform=ccrs.PlateCarree(),
        zorder=14,
    ))

    scale_zorder = 15

    # Miles bar (top)
    ax.plot([inner_x0, inner_x0 + miles_deg],
            [inner_y0 + gap, inner_y0 + gap],
            color="black", linewidth=S.LW_SCALE, solid_capstyle="butt",
            transform=ccrs.PlateCarree(), zorder=scale_zorder)
    ax.plot([inner_x0, inner_x0],
            [inner_y0 + gap - bar_h, inner_y0 + gap + bar_h],
            color="black", linewidth=S.LW_SCALE,
            transform=ccrs.PlateCarree(), zorder=scale_zorder)
    ax.plot([inner_x0 + miles_deg, inner_x0 + miles_deg],
            [inner_y0 + gap - bar_h, inner_y0 + gap + bar_h],
            color="black", linewidth=S.LW_SCALE,
            transform=ccrs.PlateCarree(), zorder=scale_zorder)
    ax.text(inner_x0 + miles_deg + dlon * 0.008, inner_y0 + gap,
            f"{target_miles} MILES", ha="left", va="center",
            color="black", transform=ccrs.PlateCarree(),
            zorder=scale_zorder, **S.FONT_SCALE)

    # Km bar (bottom)
    ax.plot([inner_x0, inner_x0 + km_deg], [inner_y0, inner_y0],
            color="black", linewidth=S.LW_SCALE, solid_capstyle="butt",
            transform=ccrs.PlateCarree(), zorder=scale_zorder)
    ax.plot([inner_x0, inner_x0],
            [inner_y0 - bar_h, inner_y0 + bar_h],
            color="black", linewidth=S.LW_SCALE,
            transform=ccrs.PlateCarree(), zorder=scale_zorder)
    ax.plot([inner_x0 + km_deg, inner_x0 + km_deg],
            [inner_y0 - bar_h, inner_y0 + bar_h],
            color="black", linewidth=S.LW_SCALE,
            transform=ccrs.PlateCarree(), zorder=scale_zorder)
    ax.text(inner_x0 + km_deg + dlon * 0.008, inner_y0,
            f"{target_km} KILOMETERS", ha="left", va="center",
            color="black", transform=ccrs.PlateCarree(),
            zorder=scale_zorder, **S.FONT_SCALE)
