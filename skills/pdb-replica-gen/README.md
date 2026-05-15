# pdb-replica-gen

Generate a 1:1 replica of a declassified President's Daily Brief as a PDF.
Articles are bilingual (English + Simplified Chinese). Reference maps are
rendered by the `cia-map-gen` skill and embedded automatically.

## Quick start

```bash
# Install Python deps (one-time)
pip install --break-system-packages -r ~/.claude/skills/pdb-replica-gen/requirements.txt

# Render the included sample brief for 2026-04-18
python3 ~/.claude/skills/pdb-replica-gen/pdb_gen.py \
    --content ~/.claude/skills/pdb-replica-gen/samples/2026-04-18.json \
    --out    ~/pdb-output/PDB_2026-04-18.pdf
```

Outputs the PDF plus any supporting map PNGs under `~/pdb-output/maps/`.
Write the output anywhere outside the skill directory; the skill folder
itself is kept free of generated artifacts.

## Authoring a fresh brief (Claude-assisted)

1. Claude gathers today's stories via `WebSearch` / `WebFetch` from ≥4 of
   Reuters, AP, BBC, NYT, WSJ, FT, Bloomberg, Al Jazeera, Xinhua, SCMP.
2. For each selected story, Claude writes a 2-4 paragraph PDB-voice
   brief and its Chinese translation. Voice rules are in
   `source_guidance.md`.
3. Claude fills a JSON file matching `content_schema.Brief` and places
   it under `samples/YYYY-MM-DD.json`.
4. Run `pdb_gen.py` to render.

## CJK fonts
The PDF uses SimSun/SimHei if the Windows font directory is visible
(`/mnt/c/Windows/Fonts`). Otherwise it falls back to Noto Sans CJK at
`/usr/share/fonts`. Install `fonts-noto-cjk` on Debian/Ubuntu if neither
is present:

```bash
sudo apt install fonts-noto-cjk
```

## Styling anchors
Cover: centered bold block title, binding-hole dashes, declassification
stamp lines, date + struck-through TOP SECRET at bottom-right.
Body: Courier typewriter face for English, SimSun for Chinese, ragged
right, underlined ALL-CAPS titles, compartment markers (`50X1`) beneath.
Footer: "For The President Only — Top Secret" centered on every body
page with a strike-through rule.
