# PDB Skill

A Claude Code plugin that turns today's news into a replica of a
1975-76 declassified **President's Daily Brief**: four to six items
verified across outlets from at least four world regions, written in
PDB voice, translated into Simplified Chinese, and typeset as a single
typewritten booklet PDF with grayscale CIA-style map plates bound in.
Markdown output is available on request.

> 一个 Claude Code 插件：联网搜集多地区权威媒体的新闻，经多源校核与中文翻译后，
> 生成与 1975-76 年解密版《总统每日情报简报》版式一致的双语 PDF，
> CIA 风格的灰度参考地图直接嵌入其中（可按需输出 Markdown）。

## Install

In Claude Code:

```
/plugin marketplace add p1nbored/PDB-SKILL
/plugin install pdb-skill@pdb-skill
```

The install dialog asks for an **output folder** (default `~/pdb-output`)
and an **output format**: `pdf` (default, one PDF per brief with the maps
embedded), `markdown` (Obsidian Markdown plus the `maps/` folder it links
to), or `both`. Change them later with `/plugin configure pdb-skill@pdb-skill`.
Map images are saved as separate files only when you ask for them.

The skills run Python 3.10+. On first use Claude checks for the Python
dependencies and installs them from the plugin's `requirements.txt`
files; from a clone you can do it yourself:

```bash
pip install -r plugins/pdb-skill/skills/pdb-replica-gen/requirements.txt \
            -r plugins/pdb-skill/skills/cia-map-gen/requirements.txt
```

Chinese text needs a TrueType CJK font: SimSun (Windows), Songti
(macOS), or `fonts-arphic-uming` / `fonts-wqy-microhei` (Linux).

## Use

Ask in plain language:

- *"Build me a PDB for today"* / *"生成今天的总统每日情报简报"*
- *"A PDB focused on the Middle East"*
- *"Make a CIA-style map of the Horn of Africa"*

or invoke a skill directly: `/pdb-skill:pdb-replica-gen 2026-04-18`,
`/pdb-skill:cia-map-gen Taiwan Strait`.

To render the bundled sample without Claude:

```bash
python plugins/pdb-skill/skills/pdb-replica-gen/scripts/pdb_gen.py \
    --content plugins/pdb-skill/skills/pdb-replica-gen/assets/samples/2026-04-18.json \
    --out-dir ./out
```

## What the replica reproduces

Measured from the scans of September 9, 1976, July 28, 1976, and April
30, 1975:

- Cover with the CIA seal on a black square, Garamond title, italic
  date, copy number, struck-through "Top Secret" with a 25X1 stamp, and
  the empty control-line box; the E.O. 11652 box on the inside cover.
- Typewritten Table of Contents with underlined region labels, hanging
  indents, and italic "(Page N)" references.
- Articles in the hanging two-column grid: `REGION:` and an italic
  lead-in two lines above a 34-character body column, Letter
  Gothic-style typewriter face, hyphenated ragged-right lines, double
  spaces after sentences, `*  *  *` between items, and `--continued`
  at the foot of each page.
- NOTES with underlined country words in the lead-ins; an annex with an
  italic abstract, A-numbered pages, and the ANNEX edge tab.
- "FOR THE PRESIDENT ONLY" banners, release lines, sanitized passages
  as ruled boxes stamped 25X1, and map plates bound in after the page
  that cites them.

## Repository layout

```
.claude-plugin/marketplace.json   marketplace listing this repo's plugin
plugins/pdb-skill/                the plugin (all that an install copies)
  .claude-plugin/plugin.json      manifest and install-time settings
  skills/pdb-replica-gen/         the brief: SKILL.md, references/ (sourcing,
                                  style guide), scripts/, assets/ (fonts, samples)
  skills/cia-map-gen/             the map plates: SKILL.md, scripts/
tests/                            pytest suite for the brief renderer
references/                       development corpus: 30 declassified PDBs
                                  (1961-76) with per-page scans
```

## Development

```bash
pip install -r requirements-dev.txt
python -m pytest tests --cov=plugins/pdb-skill/skills/pdb-replica-gen/scripts
claude plugin validate --strict .
claude plugin validate --strict plugins/pdb-skill
```

The `references/` corpus is public-domain material from the CIA
electronic reading room (CIA-RDP series; file names keep the original
document IDs). It is what the layout was measured against. It stays
outside the plugin folder, so installing the plugin copies about 1 MB;
only the one-time marketplace clone (about 170 MB) includes it.

## Licenses and provenance

- Bundled fonts: IBM Plex Mono, Courier Prime, and EB Garamond (subset
  to Latin), all under the SIL Open Font License 1.1; license texts are
  in `plugins/pdb-skill/skills/pdb-replica-gen/assets/fonts/`.
- Map data: Natural Earth (public domain), downloaded on first use.
- Output is a stylistic replica built from public news reporting. The
  PDF metadata marks it as a replica, not a government document.
