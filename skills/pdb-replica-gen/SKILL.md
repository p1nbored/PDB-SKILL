---
name: pdb-replica-gen
description: Builds a replica of a 1975-76 declassified President's Daily Brief from current news - four to six intelligence items verified across at least six outlets in four world regions, written in PDB voice with Simplified Chinese translations, and typeset as a typewritten booklet PDF plus a Markdown twin, both with a map index and CIA-style map plates. Use when the user asks for a PDB, a President's Daily Brief, a CIA-style daily intelligence brief, a declassified-style briefing on today's events, or 总统每日情报简报 / 每日情报简报.
argument-hint: "[date or focus, e.g. 2026-04-18 or 'Middle East']"
---

# PDB Replica Generator

Produces a brief laid out like the declassified 1975-76 booklets: a
cover with the CIA seal, a typewritten Table of Contents, articles in
the two-column lead-in grid, NOTES, an optional annex on A-numbered
pages, and map plates bound in after the pages that cite them. Every
article is bilingual (English, then Simplified Chinese).

You do the reporting and writing; `scripts/pdb_gen.py` does all
typesetting. Settings from the plugin configuration:

- Output folder: `${user_config.output_dir}`
- Primary format: `${user_config.primary_format}`

If either value above still reads as a `${user_config...}` placeholder,
the skill is running outside the plugin: use `~/pdb-output` and `pdf`.
Resolve `~` to the user's home directory before writing any file there.

On Windows, run the commands below with `python` (or `py -3`) instead
of `python3`, which often resolves to the Microsoft Store stub.

## Workflow

0. **Dependencies.** If
   `python3 -c "import reportlab, pyphen, cartopy"` fails, install them
   (see [First run](#first-run)) before going further; the map
   libraries can take a few minutes to install.
1. **Scope.** Use the date in `$ARGUMENTS` if given, otherwise today.
   A focus (region or topic) narrows selection but the brief still
   needs four or more items.
2. **Research.** Follow [references/sourcing.md](references/sourcing.md):
   at least six outlets from four regional buckets, every item through
   the three verification gates. Use WebSearch and WebFetch; read the
   articles, do not write from headlines.
3. **Select.** Four to six items of real intelligence weight
   (conflict, leadership, diplomacy, energy and economics, security
   technology), two to four NOTES, and an annex only when one story
   deserves extended analysis. Single-source items go to NOTES or are
   dropped.
4. **Write.** Follow [references/style-guide.md](references/style-guide.md):
   one-sentence lead-in per item, short hedged paragraphs, attributed
   evidence, no printed headlines, and a `sources` list per article.
   Translate every paragraph 1:1 into Simplified Chinese.
5. **Save the content JSON** as `PDB_<YYYY-MM-DD>.json` in the output
   folder, using an absolute path (create the folder if needed). The
   schema is at the end of the style guide; a full example is
   `${CLAUDE_SKILL_DIR}/assets/samples/2026-04-18.json`. Never write
   into the skill directory.
6. **Render:**

   ```bash
   python3 "${CLAUDE_SKILL_DIR}/scripts/pdb_gen.py" \
       --content "<output folder>/PDB_<date>.json" \
       --out-dir "${user_config.output_dir}" \
       --primary "${user_config.primary_format}"
   ```

   Maps take about five seconds each; `--no-maps` skips them for a
   quick check.
7. **Check and report.** Exit code 2 means the JSON failed validation:
   the message names the field, so fix it and re-run. Report the
   written paths (the primary format first), any map that failed, and
   the outlets the brief relied on.

## First run

Install the Python dependencies once (both skills ship in this plugin):

```bash
python3 -m pip install -r "${CLAUDE_SKILL_DIR}/requirements.txt" \
    -r "${CLAUDE_SKILL_DIR}/../cia-map-gen/requirements.txt"
```

Latin fonts (IBM Plex Mono, Courier Prime, EB Garamond; SIL OFL) are
bundled in `assets/fonts/`. Chinese text needs a TrueType CJK font:
SimSun on Windows, Songti on macOS, or `fonts-arphic-uming` /
`fonts-wqy-microhei` on Linux; set `PDB_CJK_FONT` to a `.ttf`/`.ttc`
path to choose one explicitly.

## Options

| Flag | Effect |
|------|--------|
| `--out <file.pdf>` | Exact PDF path instead of `--out-dir` |
| `--md-out <file.md>` | Markdown somewhere other than beside the PDF |
| `--primary pdf\|markdown` | Markdown-primary emits Obsidian Markdown (frontmatter, wikilinks, callouts, `![[map.png]]`) |
| `--no-pdf` / `--no-md` | Write only one format (page refs need the PDF) |
| `--no-maps` | Skip cia-map-gen |
| `--strict-maps` | Exit 3 if any map fails |

Exit codes: 0 written, 2 content missing or invalid, 3 map failure with
`--strict-maps`, 4 fonts unavailable, 5 output could not be written
(file open in a viewer, unwritable folder, or a page element too large).

## Output

`PDB_<date>.pdf`, `PDB_<date>.md`, and `maps/` in the output folder.
The Markdown mirrors the PDF (cover block, Table of Contents with the
same page numbers, a Map Index table, articles, NOTES, annex) in GitHub
flavor, or Obsidian flavor when Markdown is primary.
