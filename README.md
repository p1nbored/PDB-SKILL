# PDB Skill Pack / 总统每日情报简报 制作技能包

A pair of Claude Code skills that together produce a 1:1 replica of a
1970s declassified **President's Daily Brief (PDB)** as a bilingual
(English + Simplified Chinese) PDF plus a Markdown rendition — each
with a map index — with grayscale CIA-style reference maps embedded
automatically.

> 一套 Claude Code 技能：可联网搜集多家权威媒体的新闻，
> 经多源校核与中文翻译后，生成与解密版《总统每日情报简报》排版一致的双语
> PDF 与 Markdown 双格式输出（均含地图索引），
> 并自动配套 CIA 风格的灰度参考地图。

---

## Repository layout

```
.
├── README.md             # this file
├── .gitignore
├── skills/               # installable skills (one directory per skill)
│   ├── cia-map-gen/      # grayscale CIA-style reference map generator
│   │   ├── SKILL.md      # canonical skill manifest (frontmatter: name, description)
│   │   ├── README.md
│   │   ├── HOW_TO_USE.md
│   │   ├── requirements.txt
│   │   └── *.py
│   └── pdb-replica-gen/  # bilingual PDB PDF generator (depends on cia-map-gen)
│       ├── SKILL.md
│       ├── README.md
│       ├── source_guidance.md
│       ├── requirements.txt
│       ├── samples/      # pre-built bilingual briefs (JSON)
│       └── *.py
└── references/           # development-time reference corpus (NOT required at runtime)
    ├── README.md
    ├── index.json
    ├── *.pdf             # 30 declassified PDB documents
    ├── screenshots/      # per-page PNG renderings
    └── map_sample/       # PDB map plates used as aesthetic anchors
```

Each subdirectory of `skills/` is a self-contained Claude Code skill
following the standard skill convention: a `SKILL.md` with YAML
frontmatter (`name`, `description`) plus the code/assets it needs. The
skills run standalone — `references/` was used **only during
development** to match the typography and map aesthetics of the
declassified originals, and can be deleted or ignored after install.

## Skills

| Skill | What it does |
|-------|--------------|
| [`skills/cia-map-gen`](skills/cia-map-gen/SKILL.md) | Renders grayscale CIA-PDB-style reference map PNGs (legend cartouche, roads/railroads, star capitals, publication number) from a natural-language geographic prompt. |
| [`skills/pdb-replica-gen`](skills/pdb-replica-gen/SKILL.md) | Builds a bilingual EN/CN PDB replica as PDF + Markdown, each with a map index; calls `cia-map-gen` for embedded maps. |

`pdb-replica-gen` invokes `cia-map-gen`, so install both.

## Install

Copy each skill directory into your Claude Code skills directory:

```bash
# user-level install (recommended)
mkdir -p ~/.claude/skills
cp -r skills/cia-map-gen     ~/.claude/skills/
cp -r skills/pdb-replica-gen ~/.claude/skills/

# install Python dependencies
pip install --break-system-packages -r ~/.claude/skills/cia-map-gen/requirements.txt
pip install --break-system-packages -r ~/.claude/skills/pdb-replica-gen/requirements.txt

# choose where generated briefs land + which format is primary (persisted)
python3 ~/.claude/skills/pdb-replica-gen/pdb_gen.py \
    --set-output-dir ~/pdb-output --set-primary-format pdf
```

Or tell your Claude Code agent: *"install the skills in this repo"* — it
will read `SKILL.md` in each subdirectory and place them correctly.
During an agent-driven install, the agent pops up a selectable prompt
asking (1) where briefs should land (`~/pdb-output`,
`~/Documents/PDB-Briefs`, `./pdb-output`, or a custom path typed under
"Other" — e.g. an Obsidian vault folder) and (2) whether **PDF** or
**Markdown** is the primary output format. Both answers persist via
`--set-output-dir` / `--set-primary-format`. Markdown-primary output
is Obsidian-flavored (frontmatter properties, wikilink anchors,
callout lead-ins, `![[map.png]]` embeds) so the brief plus its `maps/`
folder can be dropped straight into a vault.

## Usage

Once installed, trigger the skills in natural language:

- **Map only:** *"make me a CIA-style map of the Horn of Africa"*
- **Full brief:** *"build me a PDB for today"* or *"生成今天的总统每日情报简报"*

See each skill's own `SKILL.md` for the full trigger phrases, flags,
and exit codes.

## References (development-only)

The `references/` directory ships the declassified PDB corpus that was
used **only during development** to design the skills against real
visual targets. It is **not** copied into `~/.claude/skills/` and the
skills do not read from it at runtime. Keep it if you want to study
the originals or extend the skills; delete it freely otherwise. See
[`references/README.md`](references/README.md) for the corpus index.
