# Writing a 1975-76 PDB

How the Ford-era briefs read and how the content JSON maps onto the
printed page. Ground truth is the declassified corpus in the
repository's `references/` folder, especially the issues of
September 9, 1976, July 28, 1976, and April 30, 1975.

## What the reader sees

- **Table of Contents** -- one entry per article: the underlined region
  label, a one-sentence summary, and "(Page N)". Then a `Notes:` line
  listing the note countries, a `Maps:` line, and "At Annex we discuss
  ...". The summary is `summary_en`.
- **Articles** -- no headline is printed. The narrow left column carries
  `REGION:` in capitals followed by the italic lead-in (`summary_en`),
  starting two lines above the body. The body runs down the right
  column, about 34 typewriter characters wide, ragged right, with a
  blank line between paragraphs. Items follow one another on the same
  page, separated by `*  *  *`; pages end with `--continued`.
- **NOTES** -- short items in the same two-column form. The italic
  lead-in is a full sentence with the country word underlined
  ("*Poland's current troubles have led to speculation about party
  chief Gierek's future.*").
- **Annex** -- one longer analytic piece on its own A-numbered pages:
  capitalized title, an italic abstract, then a single column of
  paragraphs.

The renderer handles typography: typewriter double spaces after
sentences, `--` for dashes, straight quotes, hyphenation, and Chinese
punctuation. Write normal prose and leave those to it.

## Voice

- Lead with the fact the President needs, in plain declarative
  sentences. "The five presidents probably held off making any firm
  decisions on ways to strengthen the military effort against Rhodesia
  until they assess the results of Secretary Kissinger's meeting."
- Attribute evidence the way the originals do: "press reports
  indicate", "according to our embassy in Warsaw", "photography of
  September 5 seems to indicate", "Pravda yesterday charged".
- Hedge judgments: "probably", "apparently", "we believe", "we have no
  evidence that", "the Soviets almost certainly". Use "we" for the
  Agency; never "I".
- End with the implication or what to watch, not a summary.
- Keep it short. Paragraphs are one to three sentences, usually under
  70 words; articles are two to five paragraphs. A brief has four to
  six articles, two to four notes, and at most one annex.
- Region labels follow the originals: a country or a hyphenated pair
  or trio ("Egypt-Libya", "USSR - US - South Africa", "OPEC").

### Lead-ins (`summary_en`)

One sentence, 15-35 words, italic in print and repeated in the Table
of Contents. It states the news, not the topic: "*Reliable reports
confirm that no progress was made toward uniting the fragmented
Rhodesian nationalist movement at the two-day summit conference.*"

### Notes

`region` is the country (or pair) that will be underlined;
`summary_en` should contain that word so it can be underlined in place.
`text_en` is a single paragraph of two to four sentences.

### Annex

`title_en` is a short capitalized title ("CHINA AFTER MAO").
`summary_en` is a two- or three-sentence italic abstract. The body is
four to eight paragraphs of analysis, ending with indicators to watch.

### Sanitized passages

Real copies are full of reviewer redactions: empty ruled boxes stamped
`25X1` in the margin. A body paragraph written exactly as
`"[REDACTED]"` (or `"[REDACTED:n]"` for an n-line box) prints one, with
the matching `body_cn` entry set to the same marker. Use at most one or
two per brief, between paragraphs, and never in place of a substantive
fact -- they are texture, not content.

## Chinese translation

- Simplified Chinese, one Chinese paragraph for every English one, in
  the same order (`body_cn[i]` translates `body_en[i]`).
- Keep the length roughly in proportion; do not compress a four-
  sentence paragraph into one line.
- Use intelligence vocabulary: 情报界 (intelligence community), 评估 /
  我们判断 (we assess), 很可能 / 较有可能 / 概率较低 (likelihood),
  短期内 / 近期 (near term), 中期 (medium term), 据公开报道 (according to
  press reports).
- Use the standard Mandarin forms of place names (台湾, 首尔, 华盛顿,
  德黑兰, 基辅).
- Full-width punctuation (，。；：) is preferred; ASCII punctuation next
  to Chinese characters is converted automatically.

## Maps

Give an article a `map_prompt` when geography carries the story, one or
two per brief plus an optional annex map. Prompts are geographic noun
phrases that cia-map-gen resolves: a country list ("Israel Jordan
Lebanon") or a named region ("Taiwan Strait", "Korean Peninsula", "Red
Sea", "Persian Gulf", "Horn of Africa", "South China Sea", "Sahel",
"Caucasus", "Eastern Europe", "Balkans", "Southern Africa"). `map_title`
goes in the plate's legend box, e.g. "LEBANON -- Ceasefire Line". Each
plate is bound in after the page on which its article ends.

## Content JSON

```jsonc
{
  "date": "2026-04-18",                 // YYYY-MM-DD, required
  "classification": "TOP SECRET",       // optional
  "copy_number": "2",                   // optional
  "volume_marker": "CIA/DI",            // optional, not printed
  "declass_header": "...",              // optional; derived from date if omitted
  "articles": [{                        // required, 4-6 items
    "region": "Middle East",
    "title_en": "MIDDLE EAST: CEASEFIRE HOLDS",   // Markdown heading only
    "title_cn": "中东：停火维持",
    "summary_en": "One-sentence lead-in.",
    "summary_cn": "一句话导语。",
    "body_en": ["Paragraph.", "[REDACTED:3]", "Paragraph."],
    "body_cn": ["段落。", "[REDACTED:3]", "段落。"],
    "sources": ["Reuters 2026-04-17", "Al Jazeera 2026-04-17", "Haaretz 2026-04-17"],
    "map_prompt": "Israel Lebanon Syria",          // optional
    "map_title": "LEBANON -- Ceasefire Line",       // optional
    "compartments": ["25X1"]                        // optional, legacy
  }],
  "notes": [{                           // optional, 2-4 items
    "region": "Poland",
    "summary_en": "Poland's coalition talks have stalled.",
    "summary_cn": "波兰联合政府谈判陷入停滞。",
    "text_en": "One paragraph.",
    "text_cn": "一段。"
  }],
  "annex": {                            // optional
    "title_en": "IRAN AFTER THE WAR", "title_cn": "战后的伊朗",
    "summary_en": "Italic abstract.", "summary_cn": "摘要。",
    "body_en": ["..."], "body_cn": ["..."],
    "map_prompt": "Iran", "map_title": "IRAN"
  }
}
```

Unknown fields and mismatched `body_en`/`body_cn` lengths are rejected
with exit code 2. A complete example lives in
`assets/samples/2026-04-18.json`.
