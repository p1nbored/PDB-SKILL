"""Compose the PDB replica PDF with reportlab.

Layout follows the 1975-76 booklets (ground truth in references/,
especially DOC_0006466841 of September 9, 1976):

- Cover, inside cover with the E.O. 11652 box, typewritten Table of
  Contents.
- Articles flow continuously in the hanging two-column grid: an upright
  REGION: label and italic lead-in in the narrow left column, starting
  two lines above the body in the wide right column. Items are divided
  by "*  *  *" and every page but the last of a section ends with
  "--continued".
- A map plate is bound in after the page on which its article ends.
- NOTES use the same grid; the annex is one 48-character column on
  pages A1, A2, ... with an ANNEX tab on its first page.

TOC page references and the "--continued" catchlines depend on the
final pagination, so the document is built twice: pass 1 records page
labels, pass 2 renders with them.
"""
from __future__ import annotations

import io
import os
from pathlib import Path

from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    BaseDocTemplate, CondPageBreak, Flowable, Frame, PageBreak, PageTemplate,
    Paragraph, Spacer, Table, TableStyle,
)
from reportlab.lib import textsplit as _rl_textsplit
from reportlab.platypus import paragraph as _rl_paragraph
from reportlab.platypus.doctemplate import NextPageTemplate

from cjkwrap import kinsoku_split
from content_schema import Annex, Article, Brief, Note
import pdf_pages as P
import styles as S
from textfmt import (cjk, escape, headline_case, redaction_lines, typewriter,
                     underline_term)

NBSP = "&nbsp;"
_HUGE = 10_000

# reportlab's kinsoku table is Japanese-centric and lets Chinese
# full-width closing punctuation open a line. Both line breakers keep a
# module-level copy (textsplit for single-font paragraphs, paragraph for
# mixed ones), so extend both; the update is idempotent.
_CN_CANNOT_START = "，；：？！）》”’"
for _module in (_rl_textsplit, _rl_paragraph):
    _module.ALL_CANNOT_START += "".join(
        ch for ch in _CN_CANNOT_START if ch not in _module.ALL_CANNOT_START)
del _module


def _kinsoku_dumb_split(word: str, widths: list, max_widths) -> list:  # noqa: ANN001
    return kinsoku_split(word, widths, max_widths, _rl_textsplit.ALL_CANNOT_START,
                         _rl_textsplit.ALL_CANNOT_END)


# Single-font Chinese paragraphs (all of ours) break through
# textsplit.dumbSplit, which hangs only one closing mark; swap in a
# breaker that also handles pairs such as "”，".
_rl_textsplit.dumbSplit = _kinsoku_dumb_split


# ---------------------------------------------------------------------------
# Paragraph styles
# ---------------------------------------------------------------------------
def _hyphenation() -> dict:
    """Typists broke words at line ends; pyphen supplies the rules.

    Each part of a compound is hyphenated on its own (pyphen would split
    "kill-chain" as "kil-l-chain"), and break points next to an existing
    hyphen are dropped (reportlab would set "three-" / "-phase");
    embeddedHyphenation still lets a compound break after its own hyphen."""
    try:
        import pyphen  # noqa: PLC0415
    except ImportError:
        return {}
    dictionary = pyphen.Pyphen(lang="en_US")

    def hyphenate(word: str) -> list[tuple[str, str]]:
        points, offset = [], 0
        for part in word.split("-"):
            points += [offset + len(head) for head, _ in dictionary.iterate(part)]
            offset += len(part) + 1
        pairs = [(word[:p], word[p:]) for p in sorted(points, reverse=True)]
        return [(head, tail) for head, tail in pairs
                if not head.endswith("-") and not tail.startswith("-")]

    return {"hyphenationLang": hyphenate, "embeddedHyphenation": 1,
            "uriWasteReduce": 0.3}


def _styles() -> dict[str, ParagraphStyle]:
    en = ParagraphStyle("en", fontName=S.TYPE, fontSize=S.EN_SIZE,
                        leading=S.LINE, alignment=TA_LEFT,
                        allowWidows=0, allowOrphans=0, **_hyphenation())
    cn = ParagraphStyle("cn", fontName=S.CN, fontSize=S.CN_SIZE,
                        leading=S.CN_LEADING, alignment=TA_LEFT,
                        wordWrap="CJK", spaceBefore=3,
                        allowWidows=0, allowOrphans=0)
    return {
        "en": en,
        "cn": cn,
        "leadin_cn": ParagraphStyle("leadin_cn", parent=cn,
                                    fontSize=S.CN_LEADIN_SIZE,
                                    leading=S.CN_LEADIN_LEADING, spaceBefore=4),
        "sources": ParagraphStyle("sources", parent=en, fontName=S.TYPE_ITALIC,
                                  fontSize=S.SOURCES_SIZE,
                                  leading=S.SOURCES_SIZE + 1.6,
                                  spaceBefore=S.LINE / 2),
        "center": ParagraphStyle("center", parent=en, alignment=TA_CENTER),
        "center_cn": ParagraphStyle("center_cn", parent=cn, alignment=TA_CENTER),
        "toc": ParagraphStyle("toc", parent=en, leftIndent=S.HANG,
                              firstLineIndent=-S.HANG, spaceAfter=S.LINE),
        "toc_bound": ParagraphStyle("toc_bound", parent=en, leftIndent=S.HANG,
                                    firstLineIndent=-S.HANG, keepWithNext=1),
        "toc_cn": ParagraphStyle("toc_cn", parent=cn, fontSize=S.CN_LEADIN_SIZE,
                                 leading=S.CN_LEADIN_LEADING, leftIndent=S.HANG,
                                 spaceBefore=2, spaceAfter=S.LINE),
        "abstract": ParagraphStyle("abstract", parent=en, fontName=S.TYPE_ITALIC,
                                   rightIndent=S.ANNEX_COL_W * 0.24),
        "abstract_cn": ParagraphStyle("abstract_cn", parent=cn,
                                      rightIndent=S.ANNEX_COL_W * 0.24),
    }


# ---------------------------------------------------------------------------
# Flowables
# ---------------------------------------------------------------------------
class _Marker(Flowable):
    """Zero-size flowable that records the page label where it is drawn
    and optionally queues a map plate to follow that page."""

    def __init__(self, key: str, plate: Path | None = None) -> None:
        super().__init__()
        self.key, self.plate = key, plate
        self.width = self.height = 0

    def wrap(self, avail_width: float, avail_height: float) -> tuple[float, float]:
        return 0, 0

    def draw(self) -> None:
        self.canv._doctemplate.mark(self.key, self.plate)  # noqa: SLF001


class _Redaction(Flowable):
    """Empty ruled box left by the reviewer, stamped 25X1 at its right."""

    def __init__(self, width: float, lines: int) -> None:
        super().__init__()
        self.width, self.height = width, lines * S.LINE + 4

    def wrap(self, avail_width: float, avail_height: float) -> tuple[float, float]:
        return self.width, self.height

    def draw(self) -> None:
        self.canv.saveState()
        self.canv.setLineWidth(0.6)
        self.canv.rect(0, 0, self.width, self.height, stroke=1, fill=0)
        self.canv.restoreState()
        P.draw_stamp(self.canv, self.width + 6, self.height - S.STAMP_SIZE)


def _separator(st: dict[str, ParagraphStyle]) -> list:
    stars = f"*{NBSP * 6}*{NBSP * 6}*"
    return [Spacer(1, S.LINE), Paragraph(stars, st["center"]), Spacer(1, S.LINE)]


def _pair(en: str, cn: str, st: dict[str, ParagraphStyle], width: float) -> list:
    lines = redaction_lines(en)
    if lines is not None:
        return [_Redaction(width, lines)]
    return [Paragraph(typewriter(en), st["en"]), Paragraph(cjk(cn), st["cn"])]


def _height(flowables: list, width: float) -> float:
    return sum(f.wrap(width, _HUGE)[1] + f.getSpaceBefore() + f.getSpaceAfter()
               for f in flowables)


def _hanging_item(left: list, groups: list[list], start_key: str | None,
                  end_key: str | None, plate: Path | None) -> list:
    """Left lead-in beside right-column paragraph groups; the lead-in sits
    two lines above the first body line, as typed in 1976."""
    need = max(_height(left, S.LEFT_COL_W), 8 * S.LINE) + 2 * S.LINE
    first_left = ([_Marker(start_key)] if start_key else []) + left
    rows = [[first_left, [Spacer(1, 2 * S.LINE), *groups[0]]]]
    rows += [["", [Spacer(1, S.LINE), *g]] for g in groups[1:]]
    if end_key:
        rows[-1][1].append(_Marker(end_key, plate))
    table = Table(
        rows, colWidths=[S.LEFT_COL_W + S.GUTTER, S.RIGHT_COL_W], hAlign="LEFT",
        splitByRow=1, splitInRow=1,
        style=TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (0, -1), S.GUTTER),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]),
    )
    return [CondPageBreak(need), table]


def _first_sentence(paragraphs: tuple[str, ...]) -> str:
    return paragraphs[0].split(". ")[0].rstrip(".") + "."


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------
def _label(labels: dict[str, str] | None, key: str) -> str:
    return (labels or {}).get(key, "0")


def _fmt_pages(first: str, last: str) -> str:
    """'(Page 3)' / '(Pages 3 and 4)' / '(Pages 3, 4, and 5)'."""
    if first == last:
        return f"(Page{NBSP}{first})"
    try:
        lo, hi = int(first), int(last)
    except ValueError:
        return f"(Pages {first} and {last})"
    if hi - lo == 1:
        return f"(Pages {lo} and {hi})"
    middle = ", ".join(str(n) for n in range(lo + 1, hi))
    return f"(Pages {lo}, {middle}, and {hi})"


def _toc(brief: Brief, st: dict[str, ParagraphStyle],
         article_maps: dict[int, Path], annex_map: Path | None,
         labels: dict[str, str] | None) -> list:
    flow: list = [
        Spacer(1, 0.55 * inch),
        Paragraph(P.format_date(brief.date), st["center"]),
        Spacer(1, 2 * S.LINE),
        Paragraph("<u>Table of Contents</u>", st["center"]),
        Spacer(1, 2 * S.LINE),
    ]
    for i, art in enumerate(brief.articles):
        summary = art.summary_en or _first_sentence(art.body_en)
        page = _label(labels, f"article:{i}")
        flow.append(Paragraph(
            f"<u>{escape(art.region)}</u>:{NBSP} {typewriter(summary)}{NBSP} "
            f"<i>(Page{NBSP}{page})</i>",
            st["toc_bound" if art.summary_cn else "toc"]))
        if art.summary_cn:
            flow.append(Paragraph(cjk(art.summary_cn), st["toc_cn"]))
    if brief.notes:
        topics = "; ".join(escape(n.region) for n in brief.notes)
        ref = _fmt_pages(_label(labels, "notes:first"), _label(labels, "notes:last"))
        flow.append(Paragraph(f"<u>Notes</u>:{NBSP} {topics}{NBSP} <i>{ref}</i>",
                              st["toc"]))
    maps = [f"{escape(art.map_title or art.region)}{NBSP} <i>(follows "
            f"Page{NBSP}{_label(labels, f'article_end:{i}')})</i>"
            for i, art in enumerate(brief.articles) if article_maps.get(i)]
    if annex_map and brief.annex:
        maps.append(f"{escape(brief.annex.map_title or brief.annex.title_en)}"
                    f"{NBSP} <i>(follows Page{NBSP}{_label(labels, 'annex:last')})</i>")
    if maps:
        flow.append(Paragraph(f"<u>Maps</u>:{NBSP} " + "; ".join(maps), st["toc"]))
    if brief.annex:
        title = headline_case(brief.annex.title_en.strip()).rstrip(".")
        flow.append(Paragraph(f"At <u>Annex</u> we discuss {typewriter(title)}.",
                              st["toc"]))
    return flow


def _article(article: Article, index: int, st: dict[str, ParagraphStyle],
             plate: Path | None) -> list:
    summary = article.summary_en or _first_sentence(article.body_en)
    left = [Paragraph(f"{escape(article.region.upper())}:{NBSP} "
                      f"<i>{typewriter(summary)}</i>", st["en"])]
    if article.summary_cn:
        left.append(Paragraph(cjk(article.summary_cn), st["leadin_cn"]))
    groups = [_pair(en, cn, st, S.RIGHT_COL_W)
              for en, cn in zip(article.body_en, article.body_cn)]
    if article.sources:
        cited = escape("; ".join(article.sources))
        groups[-1] = [*groups[-1], Paragraph(f"(Sources: {cited})", st["sources"])]
    plate = plate if plate and plate.exists() else None
    flow = _separator(st) if index else []
    return flow + _hanging_item(left, groups, f"article:{index}",
                                f"article_end:{index}", plate)


def _note_leadin(note: Note) -> str:
    if not note.summary_en:
        return f"<u>{escape(note.region)}</u>:"
    marked = underline_term(note.summary_en, note.region)
    if marked:
        return f"<i>{marked}</i>"
    return f"<u>{escape(note.region)}</u>:{NBSP} <i>{typewriter(note.summary_en)}</i>"


def _notes(notes: tuple[Note, ...], st: dict[str, ParagraphStyle]) -> list:
    flow: list = [PageBreak(), Paragraph("NOTES", st["center"]), Spacer(1, S.LINE)]
    for i, note in enumerate(notes):
        left = [Paragraph(_note_leadin(note), st["en"])]
        if note.summary_cn:
            left.append(Paragraph(cjk(note.summary_cn), st["leadin_cn"]))
        groups = [_pair(note.text_en, note.text_cn, st, S.RIGHT_COL_W)]
        start = "notes:first" if i == 0 else None
        end = "notes:last" if i == len(notes) - 1 else None
        flow += (_separator(st) if i else []) + _hanging_item(left, groups, start,
                                                              end, None)
    return flow


def _annex(annex: Annex, st: dict[str, ParagraphStyle], plate: Path | None) -> list:
    flow: list = [
        NextPageTemplate("annex_first"), PageBreak(),
        Spacer(1, 2 * S.LINE), _Marker("annex:first"),
        Paragraph(typewriter(annex.title_en.upper()), st["center"]),
        Paragraph(cjk(annex.title_cn), st["center_cn"]),
        Spacer(1, 2 * S.LINE),
    ]
    if annex.summary_en:
        flow.append(Paragraph(typewriter(annex.summary_en), st["abstract"]))
        if annex.summary_cn:
            flow.append(Paragraph(cjk(annex.summary_cn), st["abstract_cn"]))
        flow.append(Spacer(1, S.LINE))
    for en, cn in zip(annex.body_en, annex.body_cn):
        flow += _pair(en, cn, st, S.ANNEX_COL_W) + [Spacer(1, S.LINE)]
    flow.append(_Marker("annex:last", plate if plate and plate.exists() else None))
    return flow


def _story(brief: Brief, st: dict[str, ParagraphStyle],
           article_maps: dict[int, Path], annex_map: Path | None,
           labels: dict[str, str] | None) -> list:
    story: list = [Spacer(1, 1), NextPageTemplate("inside"), PageBreak(),
                   Spacer(1, 1), NextPageTemplate("toc"), PageBreak()]
    story += _toc(brief, st, article_maps, annex_map, labels)
    story += [NextPageTemplate("body"), PageBreak()]
    for i, art in enumerate(brief.articles):
        story += _article(art, i, st, article_maps.get(i))
    if brief.notes:
        story += _notes(brief.notes, st)
    if brief.annex:
        story += _annex(brief.annex, st, annex_map)
    return story + [NextPageTemplate("back"), PageBreak(), Spacer(1, 1)]


# ---------------------------------------------------------------------------
# Document and page templates
# ---------------------------------------------------------------------------
class _PdbDoc(BaseDocTemplate):
    """Doc template carrying pagination state for one build pass."""

    def __init__(self, target, brief: Brief,  # noqa: ANN001
                 last_pages: dict[str, str] | None) -> None:
        super().__init__(
            target, pagesize=LETTER,
            title=f"The President's Daily Brief, {P.format_date(brief.date)}",
            author="Central Intelligence Agency (replica)",
            subject="Replica in the 1975-76 PDB format; not a government document",
        )
        self.brief = brief
        self.last_pages = last_pages or {}
        self.labels: dict[str, str] = {}
        self.section_pages: dict[str, str] = {}
        self.counters = {"body": 0, "annex": 0}
        self.section = "body"
        self.pending_plates: list[Path] = []
        self.addPageTemplates(_templates())

    def current_label(self) -> str:
        if self.section == "annex":
            return f"A{self.counters['annex']}"
        return str(self.counters["body"])

    def begin_numbered_page(self, section: str) -> str:
        self.section = section
        self.counters = {**self.counters, section: self.counters[section] + 1}
        label = self.current_label()
        self.section_pages = {**self.section_pages, section: label}
        return label

    def mark(self, key: str, plate: Path | None) -> None:
        self.labels = {**self.labels, key: self.current_label()}
        if plate is not None:
            self.pending_plates = [*self.pending_plates, plate]


def _numbered(section: str, right_x: float, tab: bool = False):  # noqa: ANN202
    def on_page(c: Canvas, doc: _PdbDoc) -> None:
        label = doc.begin_numbered_page(section)
        P.draw_declass_lines(c, doc.brief.declass_header)
        P.draw_banners(c)
        P.draw_page_label(c, label)
        if doc.last_pages.get(section, label) != label:
            P.draw_continued(c, right_x)
        if tab:
            P.draw_annex_tab(c)
    return on_page


def _flush_plates(c: Canvas, doc: _PdbDoc) -> None:
    """Bind queued map plates in after the page being finished."""
    plates, doc.pending_plates = doc.pending_plates, []
    for plate in plates:
        c.showPage()
        P.draw_declass_lines(c, doc.brief.declass_header)
        P.draw_plate(c, plate)


def _templates() -> list[PageTemplate]:
    height = S.PAGE_HEIGHT - S.FRAME_TOP - S.FRAME_BOTTOM

    def frame(x: float, width: float) -> Frame:
        return Frame(x, S.FRAME_BOTTOM, width, height, leftPadding=0,
                     rightPadding=0, topPadding=0, bottomPadding=0)

    def furniture(draw):  # noqa: ANN001, ANN202
        def on_page(c: Canvas, doc: _PdbDoc) -> None:
            P.draw_declass_lines(c, doc.brief.declass_header)
            draw(c, doc.brief)
        return on_page

    annex_end = S.ANNEX_X + S.ANNEX_COL_W
    return [
        PageTemplate("cover", [frame(S.BLOCK_X, S.BLOCK_W)], onPage=furniture(
            lambda c, b: P.draw_cover(c, b.date, b.copy_number, b.classification))),
        PageTemplate("inside", [frame(S.BLOCK_X, S.BLOCK_W)],
                     onPage=furniture(lambda c, b: P.draw_inside_cover(c))),
        PageTemplate("toc", [frame(S.BLOCK_X, S.BLOCK_W)],
                     onPage=furniture(lambda c, b: P.draw_banners(c))),
        PageTemplate("body", [frame(S.BLOCK_X, S.BLOCK_W)],
                     onPage=_numbered("body", S.RIGHT_COL_END),
                     onPageEnd=_flush_plates),
        PageTemplate("annex_first", [frame(S.ANNEX_X, S.ANNEX_COL_W)],
                     autoNextPageTemplate="annex",
                     onPage=_numbered("annex", annex_end, tab=True),
                     onPageEnd=_flush_plates),
        PageTemplate("annex", [frame(S.ANNEX_X, S.ANNEX_COL_W)],
                     onPage=_numbered("annex", annex_end), onPageEnd=_flush_plates),
        PageTemplate("back", [frame(S.BLOCK_X, S.BLOCK_W)], onPage=furniture(
            lambda c, b: P.draw_back_cover(c, b.classification))),
    ]


def build_pdf(brief: Brief, out_path: Path,
              article_maps: dict[int, Path] | None = None,
              annex_map: Path | None = None) -> dict[str, str]:
    """Render the PDF and return the resolved page labels, e.g.
    {"article:0": "1", "article_end:0": "2", "notes:first": "7", ...}."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    S.register_fonts()
    st = _styles()
    maps = dict(article_maps or {})

    rehearsal = _PdbDoc(io.BytesIO(), brief, last_pages=None)
    rehearsal.build(_story(brief, st, maps, annex_map, labels=None))

    # Render to a sibling temp file, then swap in, so a failed build never
    # leaves a truncated PDF behind.
    partial = out_path.with_name(out_path.name + ".partial")
    final = _PdbDoc(str(partial), brief, last_pages=rehearsal.section_pages)
    try:
        final.build(_story(brief, st, maps, annex_map, labels=rehearsal.labels))
        os.replace(partial, out_path)
    finally:
        partial.unlink(missing_ok=True)
    return dict(final.labels)
