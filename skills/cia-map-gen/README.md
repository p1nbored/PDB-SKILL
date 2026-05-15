# cia-map-gen

Generates CIA PDB-style declassified reference map PNGs from a natural-language
geographic prompt. Pure matplotlib + public-domain Natural Earth vectors; no
paid APIs, no `cartopy` dependency.

## Quick start
```bash
python3 cia_map_gen.py --prompt "Egypt and the Red Sea" --out egypt.png
```

The first run downloads five Natural Earth 1:50m GeoJSON layers (~7 MB total)
into `~/.cache/cia-map-gen/natural_earth/`. All subsequent runs are offline.

## Architecture
| File | Role |
|------|------|
| `cia_map_gen.py` | argparse CLI entry |
| `geocoder.py`    | prompt → list of admin_0 features + padded bbox |
| `data_loader.py` | download + cache Natural Earth GeoJSON |
| `renderer.py`    | matplotlib rendering pipeline |
| `styles.py`      | fonts, line widths, colors, thresholds |
| `aliases.py`     | historical names & named-region presets |

## Styling notes
Reference samples are pure black-on-white with:
- bold country labels
- italic water body labels
- thin dotted city markers
- paired MILES / KILOMETERS scale bars
- a thick black frame
- a declassification header/footer strip

`styles.py` exposes all of these for tuning.

## Extending
- **Add a historical alias** → edit `COUNTRY_ALIASES` in `aliases.py`.
- **Add a named region** → append to `NAMED_REGIONS` in `aliases.py`.
- **Change aesthetic** → edit `styles.py` (safe: no logic there).
- **Higher resolution data** → swap the `BASE_URL` and file names in
  `data_loader.py` to the 1:10m Natural Earth layers.
