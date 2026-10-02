# Sourcing and verification

Read this before researching. Every brief draws on at least **six
outlets from at least four regional buckets**, and no bucket supplies
more than half of the citations. The aim is to break a Western-only
framing: where the actors in a story have their own press, cite it.

Listing an outlet is not an endorsement. Several are state-owned or
carry a strong editorial line; they are here because a multi-capital
brief needs to know how each capital frames the story. Attribute their
claims explicitly ("Xinhua reported...", "Tehran Times described...")
rather than folding their framing into unattributed narrative.

## Outlet buckets

**A -- Western / NATO wire and broadsheet:** Reuters (reuters.com),
Associated Press (apnews.com), AFP (afp.com), BBC (bbc.com/news), The
Guardian, New York Times, Wall Street Journal, Washington Post,
Financial Times, Bloomberg, The Economist, Le Monde, Der Spiegel,
El Pais, Politico Europe.

**B -- East Asia:** Xinhua (english.news.cn, PRC state), Global Times
(globaltimes.cn, PRC state-aligned), South China Morning Post (scmp.com),
Caixin (caixinglobal.com), Nikkei Asia (asia.nikkei.com), Kyodo
(english.kyodonews.net), Yonhap (en.yna.co.kr), Korea Herald, Focus
Taiwan (focustaiwan.tw), Taipei Times, The Straits Times, CNA
(channelnewsasia.com).

**C -- Middle East and North Africa:** Al Jazeera English, Al Arabiya
English, Arab News, The National (UAE), Anadolu Agency (aa.com.tr),
TRT World, Haaretz, The Times of Israel, Middle East Eye, Al-Monitor,
Ahram Online, Tehran Times (state-aligned; use with care).

**D -- South Asia:** The Hindu, The Times of India, Hindustan Times, The
Indian Express, ThePrint, Dawn (Pakistan), The Daily Star (Bangladesh),
The Kathmandu Post.

**E -- Sub-Saharan Africa:** Daily Maverick, Mail & Guardian, The East
African, Premium Times (Nigeria), The Nation (Nigeria), AllAfrica,
Ethiopia Insight, Semafor Africa, ISS Africa (issafrica.org).

**F -- Latin America:** Folha de S.Paulo, O Globo, Clarin, La Nacion
(Argentina), El Universal (Mexico), Milenio, Reforma, El Mercurio
(emol.com), La Tercera, El Tiempo (Colombia).

**G -- Russia and the post-Soviet space:** TASS (state), RIA Novosti
(state), Meduza (independent, in exile), The Moscow Times (independent,
in exile), Interfax, Kyiv Independent, Ukrainska Pravda, Belsat.

**H -- Southeast Asia, Oceania, multilateral:** The Jakarta Post, Bangkok
Post, Philippine Daily Inquirer, VnExpress International, ABC News
(Australia), The Australian, Stuff (New Zealand), IPS News.

## Verification gates

Every article clears all three gates before it goes into the JSON.

**Gate 1 -- triangulation.** At least three independently owned outlets
(no shared parent, not the same wire copy) report the core facts; at
least one is outside Bucket A. When a story concerns a particular
country or movement, include a source from, or critical of, that
actor's own media environment (an Israel story wants Haaretz and an
Arab outlet; a PRC story wants Xinhua or Caixin and a Japanese or
Taiwanese outlet).

**Gate 2 -- claim review.** Treat each paragraph as either reported fact
("press reports indicate", "the foreign ministry announced") or analytic
judgment ("we believe", "probably", "we assess with moderate
confidence"). Every number needs a named source in `sources`; when
reputable outlets disagree, give the range and cite both. Attribute
every quotation to the outlet that carried it. Framing that appears in
only one state-aligned outlet is either balanced in the same article or
moved to NOTES.

**Gate 3 -- bias and gap audit.** Ask whether the article leans on one
ownership cluster; if so, swap in a source from another bucket. Check
whether the subject country's own press tells a materially different
story and, if it does, say so in the article. An item that cannot clear
Gate 1 is dropped, or moved to NOTES with "single-source reporting" in
its text.

## Search patterns

Run at least two queries per story from different buckets and read 3-5
hits before writing:

```
site:reuters.com OR site:apnews.com OR site:bbc.com "<actor or place>" <YYYY-MM-DD>
site:aljazeera.com OR site:arabnews.com OR site:thenationalnews.com "<actor or place>"
site:english.news.cn OR site:scmp.com OR site:asia.nikkei.com "<actor or place>"
site:thehindu.com OR site:dawn.com OR site:theprint.in "<actor or place>"
site:folha.uol.com.br OR site:clarin.com OR site:eluniversal.com.mx "<actor or place>"
site:tass.com OR site:meduza.io OR site:kyivindependent.com "<actor or place>"
site:dailymaverick.co.za OR site:theeastafrican.co.ke "<actor or place>"
```

Cite each outlet you relied on in the article's `sources` array as
`"<Outlet> <YYYY-MM-DD>"`.
