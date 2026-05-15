# CIA-Style Map Generator — How to Use

Generates Cold War CIA declassified-plate-style reference maps (grayscale,
shaded relief, gridlines, thin black linework) from a natural-language
geographic prompt. Uses cartopy + Natural Earth 10 m data.

## Requirements

- Python 3.10+
- Python packages: `cartopy`, `rasterio`, `matplotlib`, `pillow`, `numpy`

Cartopy ships binary wheels on Linux/macOS/Windows for Python 3.10–3.13, so
a plain `pip install` works without compiling GEOS/PROJ from source.

## Setup (one-time)

```bash
cd cia-map-gen
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

## Run

```bash
.venv/bin/python3 cia_map_gen.py --prompt "Egypt" --topo --out egypt.png
```

First run downloads:

- Natural Earth 10 m vector data (via cartopy, cached to
  `~/.local/share/cartopy/shapefiles/natural_earth/`) — a few MB per layer,
  downloaded on demand.
- Shaded-relief raster `SR_50M.tif` (~11 MB) cached to
  `~/.cache/cia-map-gen/`.

Subsequent runs are fully offline.

## Flags

| Flag | Description |
|------|-------------|
| `--prompt "..."` | **Required.** Geographic description (country, region, or historical name). |
| `--out PATH` | Output PNG path. Default: `./cia_map_<slug>_<timestamp>.png`. |
| `--topo` | Overlay grayscale shaded relief inside focus countries. |
| `--title "..."` | Boxed title rendered top-left of the frame. |
| `--no-header` | Omit the "Declassified in Part…" header/footer strings. |
| `--marker LON,LAT,LABEL[,STYLE]` | Place a custom marker. Style ∈ {star, triangle, diamond, square, dot}. Repeatable. |
| `--download` | Pre-cache Natural Earth data and exit. |

## Examples

```bash
# Egypt with shaded relief
.venv/bin/python3 cia_map_gen.py --prompt "Egypt" --topo --out egypt.png

# Zimbabwe (historical alias: "Rhodesia" also works)
.venv/bin/python3 cia_map_gen.py --prompt "Rhodesia" --topo --out zim.png

# Levant region, boxed title, no declass header
.venv/bin/python3 cia_map_gen.py --prompt "Israel Jordan Lebanon" \
    --title "LEVANT" --no-header --out levant.png

# Named region shortcut
.venv/bin/python3 cia_map_gen.py --prompt "Horn of Africa" --topo \
    --out horn.png

# Custom markers (city of Alexandria with a star, a base with a triangle)
.venv/bin/python3 cia_map_gen.py --prompt "Egypt" --topo \
    --marker "29.918,31.205,Alexandria,star" \
    --marker "32.535,29.974,Suez Base,triangle" \
    --out egypt_annotated.png
```

## Exit codes

- `0` — success; PNG path printed on stdout.
- `2` — prompt could not be resolved; stderr lists closest matches.
- `3` — data fetch failed (no network on first run).

## What you get

- Cartopy `PlateCarree` projection, 8.5×11 in portrait, 200 DPI PNG.
- 10 m Natural Earth vector data: coastlines, country borders (solid for
  international, **dashed for disputed/indefinite boundaries**), rivers,
  lakes, populated places.
- Grayscale shaded relief clipped to the focus country (when `--topo`).
- Fine dotted lat/lon gridlines with coordinate labels on the top & right
  margins (e.g. `30°E`).
- Italic serif marine labels, bold condensed country labels (larger for
  focus country), sans-serif city labels with scalerank-based culling.
- Scale cartouche (miles + kilometers) in the lower-left.
- "CIA-RDP…" declassification header/footer (unless `--no-header`).
- Custom markers with boxed labels.

## Files in this package

```
cia-map-gen/
├── HOW_TO_USE.md       # this file
├── SKILL.md            # original skill manifest
├── README.md           # original short usage notes
├── cia_map_gen.py      # CLI entry point
├── renderer.py         # cartopy drawing pipeline
├── geocoder.py         # prompt → focus countries + bbox
├── data_loader.py      # shaded-relief raster fetch & cache
├── styles.py           # fonts, linewidths, colors, grid style
├── aliases.py          # historical names + named regions
└── requirements.txt    # pip dependencies
```

## Notes & limitations

- **Historical borders** are approximated via modern equivalents. See
  `aliases.py` for substitutions (e.g. Rhodesia → Zimbabwe).
- **No road or railroad network** — Natural Earth does not publish them at
  this scale, and the generator does not fabricate data.
- **Very small dependencies** may be unlabeled to avoid clutter.
- **Shaded relief** uses Natural Earth's 50 m SR plate, which is a global
  grayscale hillshade raster — it is the DEM itself, not a stylized
  hachure synthesis.
