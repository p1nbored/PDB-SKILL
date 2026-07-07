---
name: pdb-replica-gen
description: Generate a 1:1 replica of a 1970s declassified President's Daily Brief (PDB) as a PDF plus a Markdown rendition, each with a map index, with bilingual English + Chinese articles sourced from multiple authoritative media outlets and grayscale reference maps produced by the cia-map-gen skill. Trigger when the user asks for a "PDB", "President's Daily Brief", "replica PDB", "CIA daily brief", or "每日情报简报".
---

# pdb-replica-gen — President's Daily Brief Replica Generator

## When to use
Trigger on phrases like:
- "make me a PDB for today"
- "generate a President's Daily Brief replica"
- "build a bilingual (EN/CN) CIA daily brief"
- "create a declassified PDB-style report on <topic>"
- "总统每日情报简报"

## Two-step workflow (Claude does step 1, Python does step 2)

### Step 1 — Claude gathers content and writes JSON
Claude must:
1. Use `WebSearch` and `WebFetch` to collect today's top stories from
   at least **six distinct outlets** drawn from at least **four**
   regional "buckets" defined in `source_guidance.md` (A: Western/NATO,
   B: East Asia, C: MENA, D: South Asia, E: Sub-Saharan Africa,
   F: Latin America, G: Russia/Post-Soviet, H: Southeast Asia /
   Oceania / Global South multilaterals). Using only Bucket A
   outlets is **not acceptable** — the brief must intentionally
   include non-NATO framings.
2. Pick 4-6 items of genuine intelligence significance (geopolitics,
   conflict, economy, tech/security, leadership). Avoid soft news.
3. **Multifaceted verification (required).** For every picked item,
   clear the three-gate protocol in `source_guidance.md`:
   - Gate 1 — triangulation across ≥3 independently owned outlets,
     with ≥1 outside Bucket A, and where applicable an outlet from or
     critical of the subject actor's own media environment.
   - Gate 2 — claim-level review: separate reported fact from
     analytic judgment, hedge numbers with cited sources, report
     ranges when outlets disagree, attribute quotes.
   - Gate 3 — bias-and-gap audit: rebalance if any ownership cluster
     dominates, surface counter-framing from the subject country's
     own press, and demote single-source items to NOTES (or drop).
4. For each, write 2-4 tight paragraphs in PDB voice (see
   `source_guidance.md`): lead assertion → supporting evidence →
   implication/forecast.
5. Translate every paragraph to Simplified Chinese — `title_cn`,
   `summary_cn`, `body_cn`, and all `text_cn` strings in NOTES and
   ANNEX — following the CN style rules in `source_guidance.md`
   (intelligence vocabulary, hedging, paragraph-length parity).
6. **Page-density check.** Before emitting JSON, mentally simulate
   layout: articles whose content would leave 1-2 trailing lines on
   an otherwise-blank page must be either tightened or split
   into a main entry plus an ANNEX entry. See the "Page density"
   section below and the matching rule in `source_guidance.md`.
7. Decide on 1-2 accompanying maps and state the `map_prompt` for
   each (same grammar cia-map-gen accepts: "Taiwan Strait",
   "Horn of Africa", "Israel Jordan Lebanon", etc.).
8. Emit a JSON file at
   `~/.claude/skills/pdb-replica-gen/samples/<YYYY-MM-DD>.json`
   matching `content_schema.py`.

### Step 2 — Run the generator

Pick the destination the user asked for (default `~/pdb-output/`).
Either name the PDF explicitly with `--out`, or hand a directory to
`--out-dir` and let the generator auto-name the files:

```bash
# explicit PDF path
python3 ~/.claude/skills/pdb-replica-gen/pdb_gen.py \
    --content ~/.claude/skills/pdb-replica-gen/samples/2026-04-18.json \
    --out ~/pdb-output/PDB_2026-04-18.pdf

# or: directory only — writes PDB_<date>.pdf / PDB_<date>.md there
python3 ~/.claude/skills/pdb-replica-gen/pdb_gen.py \
    --content ~/.claude/skills/pdb-replica-gen/samples/2026-04-18.json \
    --out-dir ~/pdb-output
```

One run writes **both** outputs: the PDF and a Markdown rendition
next to it (same stem, `.md`), each carrying a map index. Map PNGs
land in `maps/` beside the PDF either way.

If neither `--out` nor `--out-dir` is given, the generator falls back
to the default destination chosen at install time (`config.json`;
`~/pdb-output` if none was ever configured).

Optional flags:
- `--out-dir <dir>` destination directory instead of `--out`
- `--set-output-dir <dir>` persist `<dir>` as the default output
  directory (writes `config.json`) and exit
- `--set-primary-format <pdf|markdown>` persist the primary output
  format (writes `config.json`) and exit
- `--primary <pdf|markdown>` override the configured primary format
  for this run (markdown-primary → Obsidian-flavored `.md`)
- `--md-out <path>` write the Markdown somewhere other than
  `<out>.md`
- `--no-pdf` Markdown only (TOC page refs omitted — the PDF layout
  pass is what resolves them)
- `--no-md` skip the Markdown rendition
- `--no-maps` skip cia-map-gen calls (faster dry run)
- `--strict-maps` exit 3 if any map invocation fails
- `--classification "TOP SECRET"` (set via JSON, not flag currently)

## Source diversity and verification

See `source_guidance.md`. Key rules enforced at the content layer:

- **Minimum six outlets across four buckets per brief.** No
  single bucket may provide more than half of the brief's
  citations.
- **Triangulate or drop.** Any item that cannot be corroborated
  by ≥3 independently-owned outlets is either demoted to NOTES
  (with the `summary_en` marked "single-source reporting") or
  dropped entirely.
- **Surface counter-framings.** For stories whose main facts are
  contested between governments, explicitly note how the subject
  country's own press is framing the story — do not silently
  adopt one side's language.
- **Inclusion ≠ endorsement.** State-aligned outlets (Xinhua,
  TASS, Tehran Times, Anadolu, etc.) are listed in
  `source_guidance.md` because multi-perspective coverage
  requires access to them. Attribute quotes from them
  explicitly (e.g., "Xinhua reported that …", "Tehran Times
  described …") rather than laundering their framing into
  unattributed narrative.

## Install-time setup prompt (interactive)

When installing this skill, ask the user two questions **before**
finishing the install, in a single `AskUserQuestion` call so both
appear as selectable prompts; the UI adds an "Other" option
automatically, which is where users type a custom value.

**Question 1 — output destination:**
1. `~/pdb-output` (Recommended) — default location
2. `~/Documents/PDB-Briefs` — alongside personal documents
3. `./pdb-output` — inside the current project
   (custom path via "Other" — e.g. an Obsidian vault folder)

**Question 2 — primary output format:**
1. `PDF` (Recommended) — print-faithful 1970s replica
2. `Markdown` — Obsidian-ready: YAML frontmatter properties,
   wikilink anchors, callout lead-ins, `![[map.png]]` embeds

Then persist both answers:

```bash
python3 ~/.claude/skills/pdb-replica-gen/pdb_gen.py \
    --set-output-dir "<chosen path>" \
    --set-primary-format <pdf|markdown>
```

This writes `config.json` next to the skill code. Later runs without
`--out`/`--out-dir` land in the chosen directory, and the chosen
primary format is generated/reported first (both formats are still
written unless `--no-md`/`--no-pdf`). When the primary format is
`markdown`, the `.md` is emitted in Obsidian flavor — drop the output
folder (brief + `maps/`) into a vault and everything resolves. Re-run
the `--set-*` flags any time the user wants to change the defaults.

## Page density

The finished PDF must not contain a page that is effectively
blank except for one or two lines of content (a "widow page").

Two layers defend against this:

1. **Content discipline** (Claude's job, step 1 above): size each
   article to 4 full paragraphs; keep the last Chinese paragraph
   at roughly the same visual length as its English counterpart;
   split overlong articles into main body + ANNEX rather than
   spilling onto a new page.
2. **Typesetting discipline** (handled by `pdf_builder.py`): all
   paragraph styles set `allowWidows=0` and `allowOrphans=0`; each
   English paragraph is bound to its Chinese pair with
   `keepWithNext`; the sources line is bound to the preceding
   paragraph. Do not remove these settings without updating this
   guidance.

## Output

Layout follows the dominant 1971-1976 declassified PDB booklet
format (references: DOC_0006466841 of September 9, 1976 and the
1971-73 issues).

**Letter-size PDF:**
- Cover: CIA seal white-on-black square upper left, serif roman
  title "The President's Daily Brief", italic serif date lower
  right, copy number, struck-through italic "Top Secret" with a
  25X1 stamp, empty control-line redaction box lower left
- Inside cover with the E.O. 11652 exemption box
- Typewriter "Table of Contents": underlined region labels,
  hanging-indent summaries, italic "(Page N)" refs, a "Notes:"
  line, a "Maps:" index line ("<title> (follows Page N)"), and
  the "At Annex we discuss ..." sentence
- Articles in the hanging two-column typewriter grid — REGION:
  label plus italic lead-in summary in the narrow left column,
  bilingual EN/CN body paragraphs in the wide right column
- "FOR THE PRESIDENT ONLY" letterspaced italic serif banners top
  and bottom of every text page; declassification release line at
  the extreme page edges; 25X1 stamps in the right margin
- Bare page numbers centered above the bottom banner; annex pages
  numbered A1, A2, ...; cover/TOC/map plates unnumbered
- Unnumbered, banner-free full-page map plates bound after the
  articles that reference them
- NOTES section with run-in underlined country tags; single-column
  ANNEX; blank back cover with italic "Top Secret" bottom left

**Markdown rendition** (same stem, `.md`): mirrors the same
structure — cover block, Table of Contents with anchors and the
same "(Page N)" refs, a **Map Index** table linking each plate PNG
to the article it accompanies, bilingual articles with embedded
map images, NOTES, and ANNEX. Two flavors, keyed off the primary
format: GFM (slug anchors, relative image links) when PDF is
primary; Obsidian (frontmatter properties, `[[#Heading|...]]`
wikilinks, `[!abstract]` callout lead-ins, `![[map.png]]` embeds)
when Markdown is primary.

## Files
```
~/.claude/skills/pdb-replica-gen/
  SKILL.md
  README.md
  requirements.txt
  source_guidance.md      outlet buckets + verification gates + voice
  pdb_gen.py              CLI entry (writes PDF + Markdown)
  config.json             install-time defaults: output dir + primary format
  content_schema.py       dataclasses + JSON loader
  pdf_builder.py          reportlab composition (1971-76 conventions)
  md_builder.py           Markdown rendition + map index
  styles.py               fonts, sizes, margins, CJK registration
  map_integration.py      cia-map-gen invocation helper
  samples/                pre-built bilingual briefs
  out/                    generated briefs
```

## Exit codes
- 0 — PDF (and Markdown unless `--no-md`) written
- 2 — content JSON missing or malformed
- 3 — cia-map-gen invocation failed and `--strict-maps` set
- 4 — CJK fonts not locatable
