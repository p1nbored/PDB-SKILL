# Sourcing + voice guidance for Claude

## Outlet diversity requirement (hard rule)

A single brief MUST draw on at least **six** distinct outlets across at
least **four** of the regional "buckets" below. No single bucket may
supply more than half of the citations in the brief. The intent is to
break the default Western/NATO-only posture: every article's `sources`
array should contain at least one non-Western-press outlet where the
region or actors concerned have a non-Western viewpoint worth
representing.

> Presence on this list is **not** an endorsement. Several outlets are
> explicitly state-aligned or carry a strong editorial line; they are
> included precisely because a multifaceted brief needs access to how
> the story is being framed from multiple capitals. See the
> "Verification" section below for the cross-check protocol.

### Bucket A — Western / NATO wire + broadsheet
- Reuters — reuters.com
- Associated Press — apnews.com
- Agence France-Presse — afp.com
- BBC — bbc.com/news
- The Guardian — theguardian.com
- New York Times — nytimes.com
- Wall Street Journal — wsj.com
- Washington Post — washingtonpost.com
- Financial Times — ft.com
- Bloomberg — bloomberg.com
- The Economist — economist.com
- Le Monde — lemonde.fr
- Der Spiegel — spiegel.de
- El País — elpais.com
- Politico Europe — politico.eu

### Bucket B — East Asia
- Xinhua — english.news.cn / xinhuanet.com (PRC state)
- People's Daily / Global Times — globaltimes.cn (PRC state-aligned)
- South China Morning Post — scmp.com (Hong Kong)
- Caixin — caixinglobal.com (PRC market-focused)
- Nikkei Asia — asia.nikkei.com (Japan)
- Kyodo News — english.kyodonews.net (Japan)
- Yonhap — en.yna.co.kr (ROK state wire)
- The Korea Herald — koreaherald.com (ROK)
- Focus Taiwan — focustaiwan.tw (CNA, ROC)
- Taipei Times — taipeitimes.com (ROC)
- The Straits Times — straitstimes.com (Singapore)
- Channel News Asia — channelnewsasia.com (Singapore)

### Bucket C — Middle East & North Africa
- Al Jazeera English — aljazeera.com (Qatar)
- Al Arabiya English — english.alarabiya.net (Saudi-owned)
- Arab News — arabnews.com (Saudi Arabia)
- The National — thenationalnews.com (UAE)
- Anadolu Agency — aa.com.tr (Türkiye state wire)
- TRT World — trtworld.com (Türkiye)
- Haaretz — haaretz.com (Israel)
- The Times of Israel — timesofisrael.com (Israel)
- Middle East Eye — middleeasteye.net (London-based, regional)
- Al-Monitor — al-monitor.com
- Ahram Online — english.ahram.org.eg (Egypt)
- Tehran Times — tehrantimes.com (Iran, state-aligned; use with caution)

### Bucket D — South Asia
- The Hindu — thehindu.com (India)
- The Times of India — timesofindia.indiatimes.com
- Hindustan Times — hindustantimes.com
- The Indian Express — indianexpress.com
- ThePrint — theprint.in
- Dawn — dawn.com (Pakistan)
- The Daily Star — thedailystar.net (Bangladesh)
- The Kathmandu Post — kathmandupost.com (Nepal)

### Bucket E — Sub-Saharan Africa
- Daily Maverick — dailymaverick.co.za (South Africa)
- Mail & Guardian — mg.co.za (South Africa)
- The East African — theeastafrican.co.ke (regional)
- Premium Times — premiumtimesng.com (Nigeria)
- The Nation — thenationonlineng.net (Nigeria)
- AllAfrica — allafrica.com (aggregator)
- Ethiopia Insight — ethiopia-insight.com
- Semafor Africa — semafor.com/africa
- ISS Africa — issafrica.org (think-tank, strong open-source value)

### Bucket F — Latin America
- Folha de S.Paulo — folha.uol.com.br (Brazil)
- O Globo — oglobo.globo.com (Brazil)
- Clarín — clarin.com (Argentina)
- La Nación — lanacion.com.ar (Argentina)
- El Universal — eluniversal.com.mx (Mexico)
- Milenio — milenio.com (Mexico)
- El Mercurio — emol.com (Chile)
- La Tercera — latercera.com (Chile)
- El Tiempo — eltiempo.com (Colombia)
- Reforma — reforma.com (Mexico)

### Bucket G — Russia / Post-Soviet space
- TASS — tass.com (Russian state wire)
- RIA Novosti — ria.ru (Russian state)
- Meduza — meduza.io (independent, Russian-language in exile)
- The Moscow Times — themoscowtimes.com (independent, in exile)
- Interfax — interfax.com (Russia/Ukraine bureaus)
- Kyiv Independent — kyivindependent.com (Ukraine)
- Ukrainska Pravda — pravda.com.ua (Ukraine)
- Belsat — belsat.eu (Belarus, in exile)

### Bucket H — Southeast Asia, Oceania, Global South multilaterals
- The Jakarta Post — thejakartapost.com (Indonesia)
- Bangkok Post — bangkokpost.com (Thailand)
- Philippine Daily Inquirer — inquirer.net
- VnExpress International — e.vnexpress.net (Vietnam)
- ABC News (Australia) — abc.net.au/news
- The Australian — theaustralian.com.au
- Stuff — stuff.co.nz (New Zealand)
- IPS News — ipsnews.net (non-aligned wire)

## Multifaceted verification & review protocol (hard rule)

Every article in the brief MUST clear three gates before it ships:

### Gate 1 — Multi-source triangulation
- At least **three** independently owned outlets must report the
  same core fact pattern. "Independently owned" means not sharing
  parent ownership and not reprinting the same wire copy.
- At least **one** of those sources must be outside Bucket A.
- If the story concerns a specific country or non-state actor, at
  least one source should be from, or critical of, that actor's
  own media environment (e.g., an Israel story benefits from both
  Haaretz and an Arab-press outlet; a PRC story benefits from
  Xinhua/Caixin *and* a Japanese/Taiwanese outlet).

### Gate 2 — Claim-level review
- Every `body_en` paragraph is classified as either
  **reported fact** (attributable to open sources; hedge with
  "reporting indicates", "the foreign ministry announced") or
  **analytic judgment** (must be hedged "we assess", "likely",
  "probable", with an explicit confidence level low/moderate/high).
- Numerical claims (casualty counts, vessel tallies, percentages)
  require a named source in `sources` or must be removed. If two
  reputable outlets give different numbers, report the range and
  cite both.
- Any quote must be attributed to the outlet that carried it.
- Political or cultural framing that originates in a single
  state-aligned outlet is flagged and either balanced with a
  counter-framing paragraph or demoted to the NOTES section.

### Gate 3 — Bias-and-gap audit
- After drafting, Claude explicitly asks: "Does this article rely
  disproportionately on a single ownership cluster?" If yes,
  substitute at least one citation from another bucket before
  emitting JSON.
- For any country that is the subject of an article, check whether
  that country's own press offers a materially different account.
  If so, surface that framing — even briefly — within the article
  rather than leaving it to the reader.
- Flag any item where verification gate 1 cannot be cleared; such
  items are either dropped or marked "single-source reporting"
  inside `summary_en` and demoted to the NOTES section.

## PDB voice conventions (post-1970s)
- Third-person, declarative, present tense where possible.
- Lead paragraph states the most important fact.
- Supporting paragraphs introduce evidence, attribution ("press reporting
  indicates", "open-source imagery suggests"), and context.
- Final paragraph offers implication or near-term forecast.
- Use "we" (the community) sparingly, never first-person singular.
- Prefer hedged language: "likely", "probably", "we assess that".
- Keep paragraphs tight: 2-5 sentences each.
- Title is a punchy noun phrase in ALL CAPS, e.g.
  "TAIWAN STRAIT: PLA NAVY MOVEMENT ESCALATES".

## Chinese translation rules
- Simplified Chinese.
- **Model requirement:** All `title_cn`, `summary_cn`, `body_cn`,
  and `text_cn` strings MUST be produced using the `claude-opus-4-7`
  model. If Claude is currently running on a smaller model, it MUST
  either (a) escalate by delegating the translation step to an
  `executor` agent with `model=opus`, or (b) spawn a
  `Task(subagent_type="oh-my-claudecode:executor", model="opus", ...)`
  whose sole job is bilingual translation of the already-drafted
  English content. Do not degrade to Sonnet or Haiku for CN output.
- Match paragraph boundaries 1:1 with the English — for every English
  paragraph there is exactly one Chinese paragraph.
- Preserve paragraph *lengths* in rough proportion. A 4-sentence
  English paragraph should not translate into a single short Chinese
  sentence; expand with additional hedging vocabulary
  (情报界评估 / 据公开报道 / 我们判断) rather than compressing.
- Title: descriptive noun phrase; preserve place names in official
  Mandarin form (台湾, 首尔, 华盛顿, 德黑兰, 基辅).
- Use 情报界 for "intelligence community", 评估 for "assess",
  很可能 / 较有可能 / 概率较低 for likelihood hedges, 短期内 / 近期
  for near-term, 中期 for mid-term.

## Page-density and layout discipline (hard rule)

The finished PDF must not contain any page whose only content is one
or two short lines of prose (a classic "widow" page). Avoid this at
the content layer by:
- Sizing each article to 4 body paragraphs whenever possible; do not
  emit a 5-paragraph body unless the final paragraph is itself a
  substantive (3+ sentence) implication/forecast section.
- Ensuring the Chinese paragraph for the last body item is never
  dramatically shorter than its English counterpart — pad with the
  "我们判断 / 情报界评估" analytic frame if needed.
- Splitting an over-long article into a main entry plus an ANNEX
  entry rather than letting the body spill a handful of lines onto
  an otherwise-blank page.
- The typesetting layer (`pdf_builder.py`) additionally enforces
  widow/orphan prevention and keeps English/Chinese pairs together;
  do not remove those settings.

## WebSearch prompt templates
Run at least two of these per story, from different buckets, and
cross-reference:
```
site:reuters.com OR site:apnews.com OR site:bbc.com "<region or actor>" <YYYY-MM-DD>
site:aljazeera.com OR site:arabnews.com OR site:thenationalnews.com "<region or actor>" <YYYY-MM-DD>
site:xinhuanet.com OR site:scmp.com OR site:asia.nikkei.com "<region or actor>" <YYYY-MM-DD>
site:thehindu.com OR site:dawn.com OR site:theprint.in "<region or actor>" <YYYY-MM-DD>
site:folha.uol.com.br OR site:clarin.com OR site:eluniversal.com.mx "<region or actor>" <YYYY-MM-DD>
site:tass.com OR site:meduza.io OR site:kyivindependent.com "<region or actor>" <YYYY-MM-DD>
site:dailymaverick.co.za OR site:theeastafrican.co.ke "<region or actor>" <YYYY-MM-DD>
```
Retrieve 3-5 hits per story, cross-reference at least two outlets
from different buckets, and cite each outlet in the article's
`sources` array.

## Map prompts (feed to cia-map-gen)
Use concise geographic noun phrases it already handles:
- "Taiwan Strait"
- "Korean Peninsula"
- "Red Sea"
- "Eastern Europe Ukraine"
- "Horn of Africa"
- "Israel Jordan Lebanon"
- "South China Sea"
- "Sahel"
- "Caucasus"
- "Andean Ridge"
