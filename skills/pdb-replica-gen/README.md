# pdb-replica-gen

Generate a 1:1 replica of a 1970s declassified President's Daily Brief
as a PDF **and** a Markdown rendition, each with a map index. Articles
are bilingual (English + Simplified Chinese). Reference maps are
rendered by the `cia-map-gen` skill and embedded automatically.

## Quick start

```bash
# Install Python deps (one-time)
pip install --break-system-packages -r ~/.claude/skills/pdb-replica-gen/requirements.txt

# Render the included sample brief for 2026-04-18
python3 ~/.claude/skills/pdb-replica-gen/pdb_gen.py \
    --content ~/.claude/skills/pdb-replica-gen/samples/2026-04-18.json \
    --out    ~/pdb-output/PDB_2026-04-18.pdf

# Same, but just pick a destination directory (files auto-named)
python3 ~/.claude/skills/pdb-replica-gen/pdb_gen.py \
    --content ~/.claude/skills/pdb-replica-gen/samples/2026-04-18.json \
    --out-dir ~/pdb-output
```

Outputs the PDF, a Markdown twin (`PDB_2026-04-18.md`, with a Map
Index table linking each plate), and the supporting map PNGs under
`~/pdb-output/maps/`. Write the output anywhere outside the skill
directory; the skill folder itself is kept free of generated
artifacts (except `config.json`, the persisted destination choice).

## Default output destination and primary format

At install time the installing agent prompts for a destination and a
primary output format (selectable presets or a custom value) and
persists both:

```bash
python3 ~/.claude/skills/pdb-replica-gen/pdb_gen.py \
    --set-output-dir ~/pdb-output --set-primary-format markdown
```

Runs without `--out`/`--out-dir` write to that directory (fallback
`~/pdb-output`), and the primary format is generated/reported first.
When Markdown is primary, the `.md` is Obsidian-flavored — YAML
frontmatter properties, `[[#Heading|...]]` wikilink anchors,
`[!abstract]` callout lead-ins, and `![[map.png]]` embeds — so the
brief and its `maps/` folder can be dropped into an Obsidian vault
as-is. Per-run override: `--primary <pdf|markdown>`; `--no-pdf` for a
Markdown-only run.

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
The PDF uses SimSun/SimHei from `C:\Windows\Fonts` (native Windows) or
`/mnt/c/Windows/Fonts` (WSL). Otherwise it falls back to Noto Sans CJK
at `/usr/share/fonts`. Install `fonts-noto-cjk` on Debian/Ubuntu if
neither is present:

```bash
sudo apt install fonts-noto-cjk
```

## Styling anchors (1971-76 originals)
Cover: CIA seal white-on-black square, serif roman "The President's
Daily Brief", italic serif date + copy number, struck-through italic
"Top Secret" with 25X1 stamp, empty control-line box bottom-left.
TOC: all typewriter — centered date, underlined "Table of Contents",
underlined region labels, italic "(Page N)" refs, "Notes:" and "Maps:"
index lines, "At Annex we discuss ..." sentence.
Body: hanging two-column typewriter grid (REGION: label + italic
lead-in left, bilingual paragraphs right), Courier for English, SimSun
for Chinese, bare centered page numbers, right-margin 25X1 stamps.
Banners: "FOR THE PRESIDENT ONLY" in letterspaced italic serif caps,
top and bottom of every text page; map plates carry no banner.
