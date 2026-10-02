---
name: cia-map-gen
description: Renders a grayscale reference map in the style of the 1970s CIA President's Daily Brief map plates from a plain-language place description - framed sheet with bold country names, star capitals, trunk roads and railroads, italic sea names, a legend box with Road/Railroad samples and miles/kilometers scales, the boundary disclaimer, and a publication number. Use when the user asks for a CIA-style, declassified-style, or PDB-style map, or a black-and-white reference map of a country or region. Also called by pdb-replica-gen for its map plates.
argument-hint: "<place, e.g. 'Horn of Africa' or 'Israel Jordan Lebanon'>"
---

# CIA-Style Map Generator

Turns a geographic prompt into a letter-size, 200 dpi PNG that matches
the map plates bound into the 1975-76 briefs (Rhodesia 620402 9-76,
Egypt 620375 8-76): black linework on white, a heavy frame with bare
graticule numerals, and a legend box in the lower left.

## Run

If `python3 -c "import cartopy, matplotlib"` fails, do the
[first-run install](#first-run) first. On Windows use `python` (or
`py -3`) in place of `python3`.

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/cia_map_gen.py" \
    --prompt "<place>" --out "<file.png>" [--title "<legend title>"]
```

Pick the output path from the user's request; otherwise write to the
current directory. Report the path printed on stdout.

| Flag | Effect |
|------|--------|
| `--prompt` | Required. Countries ("Israel Jordan Lebanon"), a named region, or a historical name ("Rhodesia", "Burma", "Persia") |
| `--out` | PNG path (default `./cia_map_<slug>_<timestamp>.png`) |
| `--title` | Bold title in the legend box, e.g. "LEBANON -- Ceasefire Line" |
| `--topo` | Grayscale shaded relief inside the focus countries |
| `--marker LON,LAT,LABEL[,STYLE]` | Extra marker; style is star, triangle, diamond, square, or dot; repeatable |
| `--no-header` | Omit the release line printed above and below the sheet |
| `--download` | Fetch and cache the map data, then exit |

Named regions: Middle East, Horn of Africa, Southeast Asia, Central
America, Scandinavia, Balkans, Southern Africa, Maghreb, Caucasus,
Indochina, Korean Peninsula, Red Sea, Persian Gulf, Taiwan Strait,
South China Sea, Sahel, Andean Ridge, Eastern Europe.

Exit codes: 0 written, 2 prompt not resolved (stderr lists the closest
matches; retry with a country name), 3 map data unavailable.

## First run

```bash
python3 -m pip install -r "${CLAUDE_SKILL_DIR}/requirements.txt"
```

The first map downloads Natural Earth public-domain data (a few MB per
layer, cached under `~/.local/share/cartopy` and `~/.cache/cia-map-gen`);
later runs are offline.

## Limits

- Borders, roads, and railroads are modern Natural Earth data, not the
  period network; historical names map to their modern successors
  (`scripts/aliases.py`).
- Road and rail density is cut to trunk routes, tighter for wider
  views (`scripts/linework.py`).
- Very small states may go unlabeled to avoid clutter.
