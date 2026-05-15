---
name: pdb-replica-gen
description: Generate a 1:1 replica of a post-1970s declassified President's Daily Brief (PDB) as a PDF, with bilingual English + Chinese articles sourced from multiple authoritative media outlets and grayscale reference maps produced by the cia-map-gen skill. Trigger when the user asks for a "PDB", "President's Daily Brief", "replica PDB", "CIA daily brief", or "每日情报简报".
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
5. **Translate every paragraph to Simplified Mandarin using the
   `claude-opus-4-7` model.** This is non-negotiable and applies
   to `title_cn`, `summary_cn`, `body_cn`, and all `text_cn`
   strings in NOTES and ANNEX. If the currently-running Claude
   session is not Opus 4.7, delegate the translation pass via
   `Task(subagent_type="oh-my-claudecode:executor", model="opus",
   prompt="...translate the following PDB content to Simplified
   Mandarin following source_guidance.md CN rules...")` rather than
   falling back to Sonnet/Haiku.
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
```bash
python3 ~/.claude/skills/pdb-replica-gen/pdb_gen.py \
    --content ~/.claude/skills/pdb-replica-gen/samples/2026-04-18.json \
    --out ~/pdb-output/PDB_2026-04-18.pdf
```

Optional flags:
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

## Chinese translation model requirement

All Chinese output (titles, summaries, body paragraphs, NOTES,
ANNEX) MUST be produced by `claude-opus-4-7`. Never downgrade to
Sonnet or Haiku for the translation pass. If the current session
is not Opus 4.7, spawn an `executor` subagent with `model="opus"`
solely for translation. The translator must follow the CN style
rules in `source_guidance.md` (intelligence vocabulary, hedging,
paragraph-length parity).

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
A letter-size PDF with:
- Cover page (binding dashes, declassification stamp, block-bold
  title, date, struck-through TOP SECRET)
- Per-article spreads in Courier typewriter face, underlined
  ALL-CAPS title, Chinese title beneath in SimHei, bilingual
  paragraph pairs, compartment markers (`50X1`, `NOFORN`) in right
  margin
- Map pages inserted after articles that reference them
- Running footer "For The President Only — Top Secret" and a
  declassification stamp top and bottom

## Files
```
~/.claude/skills/pdb-replica-gen/
  SKILL.md
  README.md
  requirements.txt
  source_guidance.md      outlet buckets + verification gates + voice
  pdb_gen.py              CLI entry
  content_schema.py       dataclasses + JSON loader
  pdf_builder.py          reportlab composition (widow/orphan control)
  styles.py               fonts, sizes, margins, CJK registration
  map_integration.py      cia-map-gen invocation helper
  samples/                pre-built bilingual briefs
  out/                    generated PDFs
```

## Exit codes
- 0 — PDF written
- 2 — content JSON missing or malformed
- 3 — cia-map-gen invocation failed and `--strict-maps` set
- 4 — CJK fonts not locatable
