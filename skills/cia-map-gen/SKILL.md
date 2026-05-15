---
name: cia-map-gen
description: Generate CIA-style declassified reference map PNGs from a natural-language geographic prompt. Use when the user asks for a "CIA map", "declassified map", "reference map image", or "make a map of <place>". The output is a grayscale matplotlib PNG with country labels, city dots, italic sea labels, a scale bar, and an optional declassification header/footer matching the style of CIA PDB-era map plates.
---

# CIA-Style Map Generator

## When to use this skill
Trigger on phrases like:
- "make me a CIA-style map of ..."
- "generate a declassified map of ..."
- "draw a black-and-white reference map of ..."
- "CIA map of <region/country>"
- "PDB-style map ..."

## Command
```bash
python3 ~/.claude/skills/cia-map-gen/cia_map_gen.py \
    --prompt "<geographic prompt>" \
    [--out <output.png>] \
    [--title "<title text>"] \
    [--no-header]
```

First run will download ~7 MB of Natural Earth public-domain GeoJSON into
`~/.cache/cia-map-gen/`. Subsequent runs are offline.

## Examples
```bash
# Egypt and the Red Sea (matches page_011.png aesthetic)
python3 ~/.claude/skills/cia-map-gen/cia_map_gen.py \
    --prompt "Egypt and the Red Sea" --out /tmp/egypt.png

# Israel / Jordan / Lebanon (matches page_006.png)
python3 ~/.claude/skills/cia-map-gen/cia_map_gen.py \
    --prompt "Israel Jordan Lebanon" --out /tmp/levant.png

# Historical name aliasing (Rhodesia -> Zimbabwe region, page_005.png)
python3 ~/.claude/skills/cia-map-gen/cia_map_gen.py \
    --prompt "Rhodesia and surrounding states" --out /tmp/rhodesia.png

# Named region shortcut
python3 ~/.claude/skills/cia-map-gen/cia_map_gen.py \
    --prompt "Horn of Africa" --out /tmp/horn.png
```

## How it works
1. **Geocode.** `geocoder.py` matches prompt tokens against Natural Earth
   admin_0 country attributes (NAME, NAME_LONG, ADMIN, ISO_A2/A3) and a
   small historical-alias + named-region dictionary.
2. **Compute bbox.** Union of matched country geometries, padded 15%.
3. **Render.** `renderer.py` draws grayscale countries, lakes, rivers,
   italic marine labels, city dots, scale bar (miles + km), black frame,
   and optional CIA-RDP declassification header/footer.
4. **Output.** PNG at 200 DPI, portrait, ~8.5×11 in.

## Exit codes
- `0` — success, image written.
- `2` — prompt could not be resolved (stderr lists closest matches).
- `3` — Natural Earth data could not be fetched or loaded.

## Flags
- `--prompt` (required) free-form geographic description.
- `--out` output PNG path. Default: `./cia_map_<slug>_<ts>.png`.
- `--title` optional boxed title rendered top-left of the frame.
- `--no-header` omit the declassification header/footer strings.
- `--download` pre-cache Natural Earth data and exit.

## Files
```
~/.claude/skills/cia-map-gen/
├── SKILL.md              # this file
├── cia_map_gen.py        # CLI entry
├── renderer.py           # matplotlib drawing
├── geocoder.py           # prompt → countries + bbox
├── data_loader.py        # NE geojson fetch + cache
├── styles.py             # fonts, line widths, colors
├── aliases.py            # historical names, named regions
├── README.md             # usage + tech notes
└── requirements.txt      # matplotlib (pre-installed on most systems)
```

## Limitations
- No road/railroad network data (Natural Earth does not include them at
  1:50m detail); the legend in the CIA originals is therefore omitted
  rather than fabricated.
- Historical borders are approximated via modern equivalents; see
  `aliases.py` for the substitutions applied (Rhodesia→Zimbabwe, etc.).
- Very small countries/dependencies may be unlabeled to avoid clutter.
