---
name: cia-map-gen
description: Generate CIA-style declassified reference map PNGs from a natural-language geographic prompt. Use when the user asks for a "CIA map", "declassified map", "reference map image", or "make a map of <place>". The output is a grayscale matplotlib PNG matching the 1970s CIA PDB map plates - country labels, city dots and star capitals, road/railroad linework, italic sea labels, a legend cartouche with Road/Railroad samples and miles+km scale bars, a boundary disclaimer, a publication number under the frame, and an optional declassification header/footer.
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
   roads and railroads, italic marine labels, city dots with star
   capitals, a legend cartouche (optional bold title, Road/Railroad
   line samples, miles + km scale bars), the "BOUNDARY REPRESENTATION
   IS NOT NECESSARILY AUTHORITATIVE" disclaimer, a CIA-style
   publication number below the frame (e.g. "620402 9-76"), a black
   frame with bare graticule numerals, and an optional CIA-RDP
   declassification header/footer.
4. **Output.** PNG at 200 DPI, portrait, ~8.5×11 in.

## Exit codes
- `0` — success, image written.
- `2` — prompt could not be resolved (stderr lists closest matches).
- `3` — Natural Earth data could not be fetched or loaded.

## Flags
- `--prompt` (required) free-form geographic description.
- `--out` output PNG path. Default: `./cia_map_<slug>_<ts>.png`.
- `--title` optional bold title inside the legend cartouche (boxed,
  as on the Egypt reference plate).
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
- Roads/railroads come from Natural Earth 10m (cartopy fetches and
  caches them on first use); coverage is modern, not period.
- Historical borders are approximated via modern equivalents; see
  `aliases.py` for the substitutions applied (Rhodesia→Zimbabwe, etc.).
- Very small countries/dependencies may be unlabeled to avoid clutter.
