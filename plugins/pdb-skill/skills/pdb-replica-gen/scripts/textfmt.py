"""Text conventions applied before typesetting.

English copy is converted to 1970s typewriter conventions (double
hyphen for a dash, straight quotes, two spaces after a sentence) and
Chinese copy gets full-width punctuation. Both return reportlab
paragraph markup, so every function escapes its input.
"""
from __future__ import annotations

import re

NBSP = " "
DEFAULT_REDACTION_LINES = 4
MAX_REDACTION_LINES = 30      # a box must fit in one text frame

_ABBREVIATIONS = frozenset({
    "mr", "mrs", "ms", "dr", "gen", "lt", "col", "maj", "capt", "sgt", "adm",
    "sen", "rep", "gov", "pres", "amb", "st", "mt", "ft", "no", "vs", "etc",
    "jan", "feb", "mar", "apr", "aug", "sep", "sept", "oct", "nov", "dec",
    "e.g", "i.e", "u.s", "u.n", "u.k", "jr", "sr", "inc", "co", "corp",
})

_HAN = "㐀-䶿一-鿿豈-﫿"
_FULLWIDTH = {",": "，", ";": "；", ":": "：", "?": "？",
              "!": "！", "(": "（", ")": "）"}

_SENTENCE_END = re.compile(r"(?P<token>\S+?)(?P<end>[.?!][\"')\]]*) (?=[\"'(\[]?[A-Z0-9])")
_REDACTION = re.compile(r"^\s*\[redacted(?:\s*:\s*(?P<n>\d+))?\]\s*$", re.IGNORECASE)


def escape(text: str) -> str:
    """Escape the three characters reportlab's paragraph parser reserves."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _is_abbreviation(token: str) -> bool:
    bare = token.lstrip("\"'([").lower()
    if bare in _ABBREVIATIONS:
        return True
    # Initials ("J.") and dotted acronyms ("U.S", "e.g").
    return len(bare) == 1 or "." in bare


def _double_space(match: re.Match[str]) -> str:
    token, end = match.group("token"), match.group("end")
    if end.startswith(".") and _is_abbreviation(token):
        return f"{token}{end} "
    return f"{token}{end}{NBSP} "


def typewriter(text: str) -> str:
    """English copy as it would leave a 1970s Selectric, as markup."""
    out = re.sub(r"\s*—\s*", "--", text)
    out = re.sub(r"(?<=\d)–(?=\d)", "-", out)
    out = re.sub(r"\s*–\s*", "--", out)
    out = (out.replace("“", '"').replace("”", '"')
              .replace("‘", "'").replace("’", "'"))
    out = _SENTENCE_END.sub(_double_space, out)
    return escape(out)


def cjk(text: str) -> str:
    """Chinese copy with full-width punctuation next to Han characters."""
    def _swap(match: re.Match[str]) -> str:
        return _FULLWIDTH[match.group(0)]

    out = re.sub(rf"(?<=[{_HAN}])[,;:?!]|[,;:?!](?=[{_HAN}])", _swap, text)
    out = re.sub(rf"\((?=[^()]*[{_HAN}][^()]*\))|(?<=[{_HAN}])\)", _swap, out)
    out = re.sub(r"（([^()）]*)\)", "（\\1）", out)
    return escape(out)


_MINOR_WORDS = frozenset({
    "a", "an", "and", "as", "at", "but", "by", "for", "from", "in", "into",
    "of", "on", "or", "over", "the", "to", "with", "after", "amid", "via", "vs",
})
# Short words that are ordinary English rather than acronyms like PLA, IMF.
_COMMON_SHORT = frozenset({
    "new", "war", "oil", "gas", "end", "two", "key", "law", "ban", "aid", "set",
    "way", "sea", "air", "army", "navy", "deal", "vote", "rise", "fall", "risk",
    "bid", "cut", "hit", "row", "win", "loss", "gain", "lead", "plan", "move",
    "rule", "role", "post", "test", "jet", "jets", "arms", "base", "zone",
    "line", "pact", "case", "next", "last", "more", "less", "most", "high",
    "low", "old", "era", "age", "aim", "ally", "eye", "due", "top", "its",
    "his", "her", "our", "not", "now", "out", "off", "up", "why", "how",
    "who", "what", "east", "west", "red", "food", "debt", "fuel", "port",
})
_LONG_ACRONYMS = frozenset({
    "nato", "opec", "dprk", "irgc", "iaea", "asean", "brics", "oecd",
    "ecowas", "unsc", "unhcr", "swift", "nasa", "icbm", "slbm",
})


def _case_part(part: str, first: bool) -> str:
    core = re.sub(r"[^A-Za-z]", "", part).lower()
    if core in _MINOR_WORDS and not first:
        return part.lower()
    short_acronym = 2 <= len(core) <= 3 and core not in _MINOR_WORDS | _COMMON_SHORT
    if short_acronym or core in _LONG_ACRONYMS:
        return part                       # PLA, IMF, DPRK stay in capitals
    return part[:1].upper() + part[1:].lower()


def headline_case(title: str) -> str:
    """Title-case an ALL-CAPS headline, keeping minor words lowercase and
    short acronyms uppercase; mixed-case titles are returned unchanged."""
    if not title.isupper():
        return title
    words, first = [], True
    for token in title.split():
        words.append("-".join(_case_part(p, first and i == 0)
                              for i, p in enumerate(token.split("-"))))
        first = token.endswith(":")
    return " ".join(words)


def redaction_lines(text: str) -> int | None:
    """Height in lines of a "[REDACTED]" / "[REDACTED:n]" marker, else None."""
    match = _REDACTION.match(text)
    if match is None:
        return None
    lines = int(match.group("n")) if match.group("n") else DEFAULT_REDACTION_LINES
    return min(lines, MAX_REDACTION_LINES) if lines > 0 else None


def underline_term(sentence: str, term: str) -> str | None:
    """Escaped sentence with the first occurrence of *term* (and any
    possessive suffix) underlined, or None when the term is absent."""
    match = re.search(rf"\b{re.escape(term)}(?:'s)?\b", sentence, re.IGNORECASE)
    if match is None:
        return None
    start, end = match.span()
    return (typewriter(sentence[:start]) + "<u>" + escape(sentence[start:end])
            + "</u>" + typewriter(sentence[end:]))
