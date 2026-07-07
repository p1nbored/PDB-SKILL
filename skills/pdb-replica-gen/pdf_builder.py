"""Compose the PDB replica PDF using reportlab.

Layout follows the dominant 1971-1976 declassified PDB booklet format
(ground truth: references/screenshots, esp. DOC_0006466841 of
September 9, 1976 and the 1971-73 issues):

- Cover: CIA seal white-on-black square upper left, serif roman
  title "The President's Daily Brief", italic serif date lower
  right, struck-through italic "Top Secret" with 25X1 stamp,
  empty control-line redaction box lower left.
- Inside cover: small ruled E.O. 11652 exemption box (original
  printing on 1972-76 issues).
- Table of Contents: all typewriter; centered date, centered
  underlined "Table of Contents", hanging-indent entries with the
  underlined region label, italic "(Page N)" refs, a "Notes:" line,
  a "Maps:" index line, and the "At Annex we discuss ..." sentence.
- Articles: hanging two-column typewriter grid — region label +
  italic lead-in summary in the narrow left column, body paragraphs
  in the wide right column (1976 convention). Bilingual EN/CN pairs.
- Banners: "FOR THE PRESIDENT ONLY" in letterspaced italic serif
  caps, centered top and bottom of every text page. Map plates and
  covers carry no banner (as in the originals).
- Page numbers: bare arabic numeral centered above the bottom
  banner; annex pages use "A1, A2, ..."; cover/TOC/plates unnumbered.
- 25X1 stamps in the right margin (declassification-artifact look).
- NOTES: centered display heading, run-in underlined country tags.
- Annex: full-width single-column typewriter, own A-numbering.

Page labels for the TOC "(Page N)" refs are resolved with a
two-pass build: pass 1 renders to a throwaway buffer recording the
page label at each anchor, pass 2 renders the real file.
"""
from __future__ import annotations

import io
import math
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    BaseDocTemplate, CondPageBreak, Flowable, Frame, Image, PageBreak,
    PageTemplate, Paragraph, Spacer, Table, TableStyle,
)
from reportlab.platypus.doctemplate import NextPageTemplate

from content_schema import Annex, Article, Brief, Note
import styles as S


# ---------------------------------------------------------------------------
# Canvas helpers
# ---------------------------------------------------------------------------
def _letterspaced_centered(c: Canvas, text: str, y: float, font: str,
                           size: float, charspace: float) -> None:
    """Centered text with letterspacing (banners are letterspaced caps)."""
    c.saveState()
    width = c.stringWidth(text, font, size) + charspace * (len(text) - 1)
    t = c.beginText((S.PAGE_WIDTH - width) / 2, y)
    t.setFont(font, size)
    t.setCharSpace(charspace)
    t.textOut(text)
    c.drawText(t)
    c.restoreState()


def _draw_declass_lines(c: Canvas, brief: Brief) -> None:
    """Modern sans release stamp, extreme top and bottom (scan artifact)."""
    c.saveState()
    c.setFont("Helvetica", S.DECLASS_SIZE)
    c.setFillColor(colors.black)
    c.drawCentredString(S.PAGE_WIDTH / 2, S.PAGE_HEIGHT - 0.32 * inch,
                        brief.declass_header)
    c.drawCentredString(S.PAGE_WIDTH / 2, 0.24 * inch, brief.declass_header)
    c.restoreState()


def _draw_banner(c: Canvas, y: float) -> None:
    """FOR THE PRESIDENT ONLY — letterspaced italic serif caps."""
    _letterspaced_centered(c, "FOR THE PRESIDENT ONLY", y,
                           S.SERIF_ITALIC, S.BANNER_SIZE, 1.6)


def _draw_margin_stamp(c: Canvas, text: str = "25X1") -> None:
    """Right-margin declassification exemption stamp."""
    c.saveState()
    c.setFont("Helvetica", S.STAMP_SIZE)
    c.drawString(S.PAGE_WIDTH - 0.62 * inch, S.PAGE_HEIGHT * 0.58, text)
    c.restoreState()


def _draw_seal(c: Canvas, x: float, y: float, side: float) -> None:
    """CIA seal simplified as a white engraving on a solid black square."""
    c.saveState()
    c.setFillColor(colors.black)
    c.rect(x, y, side, side, stroke=0, fill=1)

    cx, cy = x + side / 2, y + side / 2
    r_outer = side * 0.42
    r_ring_in = side * 0.30

    c.setStrokeColor(colors.white)
    c.setLineWidth(0.9)
    c.circle(cx, cy, r_outer, stroke=1, fill=0)
    c.circle(cx, cy, r_ring_in, stroke=1, fill=0)

    # Ring text along the top and bottom arcs.
    c.setFillColor(colors.white)
    ring_font_size = side * 0.052
    r_text = (r_outer + r_ring_in) / 2 - ring_font_size * 0.35

    def _arc_text(text: str, start_deg: float, end_deg: float,
                  outward: bool) -> None:
        n = len(text)
        if n == 0:
            return
        for i, ch in enumerate(text):
            frac = i / max(n - 1, 1)
            ang = math.radians(start_deg + (end_deg - start_deg) * frac)
            tx = cx + r_text * math.cos(ang)
            ty = cy + r_text * math.sin(ang)
            c.saveState()
            c.translate(tx, ty)
            rot = math.degrees(ang) - 90 if outward else math.degrees(ang) + 90
            c.rotate(rot)
            c.setFont("Times-Roman", ring_font_size)
            c.drawCentredString(0, 0, ch)
            c.restoreState()

    _arc_text("CENTRAL INTELLIGENCE AGENCY", 160, 20, outward=True)
    _arc_text("UNITED STATES OF AMERICA", 200, 340, outward=False)

    # Compass rose: 16 rays alternating long/short.
    c.setFillColor(colors.white)
    c.setStrokeColor(colors.white)
    r_star_long = r_ring_in * 0.78
    r_star_short = r_ring_in * 0.42
    half_w = r_ring_in * 0.075
    for k in range(16):
        ang = math.radians(k * 22.5)
        r_tip = r_star_long if k % 2 == 0 else r_star_short * 1.35
        tipx = cx + r_tip * math.sin(ang)
        tipy = cy + r_tip * math.cos(ang)
        bx = half_w * math.cos(ang)
        by = -half_w * math.sin(ang)
        p = c.beginPath()
        p.moveTo(cx + bx, cy + by)
        p.lineTo(tipx, tipy)
        p.lineTo(cx - bx, cy - by)
        p.close()
        c.drawPath(p, stroke=0, fill=1)
    c.circle(cx, cy, r_ring_in * 0.10, stroke=0, fill=1)
    c.restoreState()


def _draw_page_number(c: Canvas, label: str) -> None:
    """Bare numeral centered above the bottom banner (typewriter face)."""
    c.saveState()
    c.setFont(S.BODY_EN, S.BODY_SIZE)
    c.drawCentredString(S.PAGE_WIDTH / 2, 0.86 * inch, label)
    c.restoreState()


# ---- per-template onPage callbacks ----------------------------------------
def _onpage_cover(c: Canvas, doc) -> None:  # noqa: ANN001
    brief: Brief = doc._brief  # type: ignore[attr-defined]
    _draw_declass_lines(c, brief)

    # Seal on black square, upper-left region.
    side = 2.2 * inch
    _draw_seal(c, 1.55 * inch, S.PAGE_HEIGHT - 0.24 * S.PAGE_HEIGHT - side,
               side)

    # Title — serif roman, title case, flush with the seal margin.
    c.setFont(S.SERIF, S.COVER_TITLE_SIZE)
    c.drawString(1.55 * inch, S.PAGE_HEIGHT * 0.50,
                 "The President's Daily Brief")

    # Date — italic serif, right-of-center, low on the page.
    c.setFont(S.SERIF_ITALIC, S.COVER_DATE_SIZE)
    c.drawRightString(S.PAGE_WIDTH - 1.35 * inch, S.PAGE_HEIGHT * 0.155,
                      _format_date(brief.date))

    # Copy number under the date.
    c.setFont(S.SERIF, S.COVER_DATE_SIZE - 3)
    c.drawRightString(S.PAGE_WIDTH - 1.95 * inch, S.PAGE_HEIGHT * 0.125,
                      brief.copy_number)

    # "Top Secret" italic serif, hand-struck, 25X1 beside it.
    ts_y = S.PAGE_HEIGHT * 0.095
    c.setFont(S.SERIF_ITALIC, S.COVER_DATE_SIZE)
    ts_text = _classification_titlecase(brief.classification)
    tw = c.stringWidth(ts_text, S.SERIF_ITALIC, S.COVER_DATE_SIZE)
    ts_x = S.PAGE_WIDTH - 1.35 * inch - tw
    c.drawString(ts_x, ts_y, ts_text)
    c.setLineWidth(1.1)
    c.line(ts_x - 4, ts_y + 2.2, ts_x + tw + 6, ts_y + 4.8)
    c.setFont("Helvetica", S.STAMP_SIZE)
    c.drawString(S.PAGE_WIDTH - 0.62 * inch, ts_y, "25X1")

    # Empty control-line redaction box, bottom left (sanitized codeword).
    c.setLineWidth(0.5)
    c.rect(1.0 * inch, ts_y - 3, 1.9 * inch, 0.28 * inch, stroke=1, fill=0)


def _onpage_inside(c: Canvas, doc) -> None:  # noqa: ANN001
    brief: Brief = doc._brief  # type: ignore[attr-defined]
    _draw_declass_lines(c, brief)
    # E.O. 11652 exemption box — original printing on the inside cover.
    box_w, box_h = 2.6 * inch, 0.72 * inch
    bx, by = 1.0 * inch, 1.1 * inch
    c.setLineWidth(0.6)
    c.rect(bx, by, box_w, box_h, stroke=1, fill=0)
    c.setFont(S.SERIF, 6.5)
    lines = [
        "Exempt from general declassification schedule",
        "of E.O. 11652 exemption category 5B(1),(2),(3)",
        "declassified only on approval of",
        "the Director of Central Intelligence",
    ]
    ty = by + box_h - 0.16 * inch
    for ln in lines:
        c.drawCentredString(bx + box_w / 2, ty, ln)
        ty -= 0.135 * inch


def _onpage_toc(c: Canvas, doc) -> None:  # noqa: ANN001
    brief: Brief = doc._brief  # type: ignore[attr-defined]
    _draw_declass_lines(c, brief)
    _draw_banner(c, S.PAGE_HEIGHT - 0.62 * inch)
    _draw_banner(c, 0.52 * inch)
    # TOC is unnumbered in the originals.


def _onpage_body(c: Canvas, doc) -> None:  # noqa: ANN001
    brief: Brief = doc._brief  # type: ignore[attr-defined]
    doc._page_mode = "body"  # type: ignore[attr-defined]
    doc._body_no = getattr(doc, "_body_no", 0) + 1
    _draw_declass_lines(c, brief)
    _draw_banner(c, S.PAGE_HEIGHT - 0.62 * inch)
    _draw_banner(c, 0.52 * inch)
    _draw_margin_stamp(c)
    _draw_page_number(c, str(doc._body_no))


def _onpage_annex(c: Canvas, doc) -> None:  # noqa: ANN001
    brief: Brief = doc._brief  # type: ignore[attr-defined]
    doc._page_mode = "annex"  # type: ignore[attr-defined]
    doc._annex_no = getattr(doc, "_annex_no", 0) + 1
    _draw_declass_lines(c, brief)
    _draw_banner(c, S.PAGE_HEIGHT - 0.62 * inch)
    _draw_banner(c, 0.52 * inch)
    _draw_margin_stamp(c)
    _draw_page_number(c, f"A{doc._annex_no}")


def _onpage_plate(c: Canvas, doc) -> None:  # noqa: ANN001
    """Map plates carry no banner and no page number in the originals."""
    brief: Brief = doc._brief  # type: ignore[attr-defined]
    _draw_declass_lines(c, brief)
    _draw_margin_stamp(c)


def _onpage_back(c: Canvas, doc) -> None:  # noqa: ANN001
    brief: Brief = doc._brief  # type: ignore[attr-defined]
    _draw_declass_lines(c, brief)
    # Back cover: italic serif "Top Secret", bottom LEFT, unstruck.
    c.setFont(S.SERIF_ITALIC, S.COVER_DATE_SIZE)
    c.drawString(1.0 * inch, S.PAGE_HEIGHT * 0.095,
                 _classification_titlecase(brief.classification))


# ---------------------------------------------------------------------------
# Page-label anchors (two-pass TOC page references)
# ---------------------------------------------------------------------------
class _PageMarker(Flowable):
    """Zero-size flowable that records the page label where it lands."""

    def __init__(self, key: str) -> None:
        super().__init__()
        self.key = key
        self.width = 0
        self.height = 0

    def draw(self) -> None:
        doc = self.canv._doctemplate  # noqa: SLF001
        if getattr(doc, "_page_mode", "body") == "annex":
            label = f"A{getattr(doc, '_annex_no', 1)}"
        else:
            label = str(getattr(doc, "_body_no", 1))
        doc._labels[self.key] = label  # type: ignore[attr-defined]


def _label(labels: dict[str, str] | None, key: str) -> str:
    return (labels or {}).get(key, "0")


def _fmt_pages(first: str, last: str) -> str:
    """'(Page 3)' / '(Pages 3 and 4)' / '(Pages 3, 4, and 5)'."""
    if first == last:
        return f"(Page {first})"
    try:
        lo, hi = int(first), int(last)
    except ValueError:
        return f"(Pages {first} and {last})"
    if hi - lo == 1:
        return f"(Pages {lo} and {hi})"
    middle = ", ".join(str(n) for n in range(lo + 1, hi))
    return f"(Pages {lo}, {middle}, and {hi})"


# ---------------------------------------------------------------------------
# Paragraph styles
# ---------------------------------------------------------------------------
def _styles(cn_font: str, cn_font_bold: str) -> dict[str, ParagraphStyle]:
    # Widow/orphan control on every prose style; EN halves of bilingual
    # pairs bind to their CN half via keepWithNext (see _article_flowables).
    return {
        # Left-column lead-in: upright caps label + italic summary.
        "leadin_en": ParagraphStyle(
            "leadin_en", fontName=S.BODY_EN_ITALIC, fontSize=S.BODY_SIZE,
            leading=S.BODY_LEADING, alignment=TA_LEFT, textColor=colors.black,
            spaceAfter=6, allowWidows=0, allowOrphans=0, keepWithNext=1,
        ),
        "leadin_cn": ParagraphStyle(
            "leadin_cn", fontName=cn_font, fontSize=S.BODY_SIZE,
            leading=S.BODY_LEADING, alignment=TA_LEFT, textColor=colors.black,
            allowWidows=0, allowOrphans=0,
        ),
        # Right-column body: upright typewriter, block paragraphs, no
        # first-line indent, blank line between paragraphs (1976 style).
        "body_en": ParagraphStyle(
            "body_en", fontName=S.BODY_EN, fontSize=S.BODY_SIZE,
            leading=S.BODY_LEADING, alignment=TA_LEFT, textColor=colors.black,
            firstLineIndent=0, spaceAfter=3,
            allowWidows=0, allowOrphans=0, keepWithNext=1,
        ),
        "body_cn": ParagraphStyle(
            "body_cn", fontName=cn_font, fontSize=S.BODY_SIZE + 0.5,
            leading=S.BODY_LEADING + 1, alignment=TA_LEFT, textColor=colors.black,
            firstLineIndent=0, spaceAfter=S.BODY_LEADING * 0.75,
            allowWidows=0, allowOrphans=0,
        ),
        "body_cn_bind": ParagraphStyle(
            "body_cn_bind", fontName=cn_font, fontSize=S.BODY_SIZE + 0.5,
            leading=S.BODY_LEADING + 1, alignment=TA_LEFT, textColor=colors.black,
            firstLineIndent=0, spaceAfter=S.BODY_LEADING * 0.75,
            allowWidows=0, allowOrphans=0, keepWithNext=1,
        ),
        "sources": ParagraphStyle(
            "sources", fontName=S.BODY_EN_ITALIC, fontSize=S.FOOTER_SIZE + 0.5,
            leading=S.FOOTER_SIZE + 2.5, alignment=TA_LEFT,
            textColor=colors.black, spaceBefore=2,
            allowWidows=0, allowOrphans=0,
        ),
        # TOC (all typewriter).
        "toc_date": ParagraphStyle(
            "toc_date", fontName=S.BODY_EN, fontSize=S.BODY_SIZE,
            leading=S.BODY_LEADING, alignment=TA_CENTER, textColor=colors.black,
            spaceAfter=S.BODY_LEADING,
        ),
        "toc_heading": ParagraphStyle(
            "toc_heading", fontName=S.BODY_EN, fontSize=S.BODY_SIZE,
            leading=S.BODY_LEADING, alignment=TA_CENTER, textColor=colors.black,
            spaceAfter=S.BODY_LEADING * 1.3,
        ),
        "toc_entry": ParagraphStyle(
            "toc_entry", fontName=S.BODY_EN, fontSize=S.BODY_SIZE,
            leading=S.BODY_LEADING, alignment=TA_LEFT, textColor=colors.black,
            leftIndent=32, firstLineIndent=-32, spaceAfter=3,
        ),
        "toc_entry_cn": ParagraphStyle(
            "toc_entry_cn", fontName=cn_font, fontSize=S.BODY_SIZE - 0.5,
            leading=S.BODY_LEADING, alignment=TA_LEFT, textColor=colors.black,
            leftIndent=32, spaceAfter=8,
        ),
        # NOTES (1972 convention: run-in underlined tag).
        "notes_title": ParagraphStyle(
            "notes_title", fontName=S.DISPLAY, fontSize=S.DISPLAY_SIZE,
            leading=S.DISPLAY_SIZE + 4, alignment=TA_CENTER,
            textColor=colors.black, spaceBefore=6, spaceAfter=S.BODY_LEADING,
        ),
        "note": ParagraphStyle(
            "note", fontName=S.BODY_EN, fontSize=S.BODY_SIZE,
            leading=S.BODY_LEADING, alignment=TA_LEFT, textColor=colors.black,
            firstLineIndent=31, spaceAfter=3,
            allowWidows=0, allowOrphans=0, keepWithNext=1,
        ),
        "note_cn": ParagraphStyle(
            "note_cn", fontName=cn_font, fontSize=S.BODY_SIZE,
            leading=S.BODY_LEADING, alignment=TA_LEFT, textColor=colors.black,
            spaceAfter=S.BODY_LEADING,
            allowWidows=0, allowOrphans=0,
        ),
        # Annex (full-width single column).
        "annex_label": ParagraphStyle(
            "annex_label", fontName=S.DISPLAY, fontSize=S.DISPLAY_SIZE - 1,
            leading=S.DISPLAY_SIZE + 2, alignment=TA_CENTER,
            textColor=colors.black, spaceAfter=6,
        ),
        "annex_title": ParagraphStyle(
            "annex_title", fontName=S.DISPLAY, fontSize=S.DISPLAY_SIZE,
            leading=S.DISPLAY_SIZE + 4, alignment=TA_CENTER,
            textColor=colors.black, spaceAfter=2,
        ),
        "annex_title_cn": ParagraphStyle(
            "annex_title_cn", fontName=cn_font_bold, fontSize=S.BODY_SIZE + 1,
            leading=S.BODY_LEADING + 2, alignment=TA_CENTER,
            textColor=colors.black, spaceAfter=S.BODY_LEADING,
        ),
        "annex_body_en": ParagraphStyle(
            "annex_body_en", fontName=S.BODY_EN, fontSize=S.BODY_SIZE,
            leading=S.BODY_LEADING, alignment=TA_LEFT, textColor=colors.black,
            firstLineIndent=0, spaceAfter=3,
            allowWidows=0, allowOrphans=0, keepWithNext=1,
        ),
        "annex_body_cn": ParagraphStyle(
            "annex_body_cn", fontName=cn_font, fontSize=S.BODY_SIZE + 0.5,
            leading=S.BODY_LEADING + 1, alignment=TA_LEFT, textColor=colors.black,
            firstLineIndent=0, spaceAfter=S.BODY_LEADING * 0.75,
            allowWidows=0, allowOrphans=0,
        ),
    }


# ---------------------------------------------------------------------------
# Table of Contents
# ---------------------------------------------------------------------------
def _toc_flowables(brief: Brief, st: dict[str, ParagraphStyle],
                   article_maps: dict[int, Path],
                   annex_map: Path | None,
                   labels: dict[str, str] | None) -> list:
    flow: list = [
        Spacer(1, 0.55 * inch),
        Paragraph(_format_date(brief.date), st["toc_date"]),
        Paragraph("<u>Table of Contents</u>", st["toc_heading"]),
    ]
    for i, art in enumerate(brief.articles):
        summary = art.summary_en or (art.body_en[0].split(". ")[0] + ".")
        page = _label(labels, f"article:{i}")
        flow.append(Paragraph(
            f"<u>{art.region}</u>:  {summary}  <i>(Page {page})</i>",
            st["toc_entry"],
        ))
        if art.summary_cn:
            flow.append(Paragraph(art.summary_cn, st["toc_entry_cn"]))

    if brief.notes:
        topics = "; ".join(n.region for n in brief.notes)
        ref = _fmt_pages(_label(labels, "notes:first"),
                         _label(labels, "notes:last"))
        flow.append(Paragraph(
            f"<u>Notes</u>:  {topics}  <i>{ref}</i>", st["toc_entry"],
        ))

    # Map index — grammar matches the Notes line of the originals.
    map_refs = []
    for i, art in enumerate(brief.articles):
        if article_maps.get(i):
            title = art.map_title or art.region
            map_refs.append(
                f"{title}  <i>(follows Page {_label(labels, f'article_end:{i}')})</i>"
            )
    if annex_map and brief.annex:
        title = brief.annex.map_title or brief.annex.title_en
        map_refs.append(
            f"{title}  <i>(follows Page {_label(labels, 'annex:last')})</i>"
        )
    if map_refs:
        flow.append(Paragraph(
            "<u>Maps</u>:  " + "; ".join(map_refs), st["toc_entry"],
        ))

    if brief.annex:
        flow.append(Paragraph(
            f"At <u>Annex</u> we discuss {brief.annex.title_en.strip()}.",
            st["toc_entry"],
        ))
    return flow


# ---------------------------------------------------------------------------
# Article layout — hanging two-column typewriter grid (1976 convention)
# ---------------------------------------------------------------------------
def _article_flowables(article: Article, index: int,
                       st: dict[str, ParagraphStyle],
                       map_image: Path | None) -> list:
    flow: list = []

    # Guarantee room for the lead-in plus at least one body pair.
    flow.append(CondPageBreak(4.2 * inch))
    flow.append(_PageMarker(f"article:{index}"))
    # Articles start with deliberate sinkage below the top banner.
    flow.append(Spacer(1, 0.5 * inch))

    # Left column: REGION: label (upright caps) run into italic summary.
    summary = article.summary_en or (article.body_en[0].split(". ")[0] + ".")
    leadin_cells: list = [Paragraph(
        f"<font name='{S.BODY_EN}'>{article.region.upper()}:</font>  {summary}",
        st["leadin_en"],
    )]
    if article.summary_cn:
        leadin_cells.append(Paragraph(article.summary_cn, st["leadin_cn"]))

    # Right column: one Table row per EN/CN paragraph pair so splitByRow
    # breaks between pairs instead of orphaning the lead-in.
    pairs = list(zip(article.body_en, article.body_cn))
    table_data: list = []
    for i, (en_para, cn_para) in enumerate(pairs):
        is_last = (i == len(pairs) - 1)
        cn_style = st["body_cn_bind"] if (is_last and article.sources) else st["body_cn"]
        right_cells = [
            Paragraph(en_para, st["body_en"]),
            Paragraph(cn_para, cn_style),
        ]
        left_cells = leadin_cells if i == 0 else ""
        table_data.append([left_cells, right_cells])

    if article.sources:
        table_data.append([
            "",
            Paragraph("<i>(Sources: " + "; ".join(article.sources) + ")</i>",
                      st["sources"]),
        ])

    avail_w = S.PAGE_WIDTH - S.LEFT_MARGIN - S.RIGHT_MARGIN
    left_w = avail_w * 0.32
    right_w = avail_w - left_w

    table = Table(
        table_data,
        colWidths=[left_w, right_w],
        hAlign="LEFT",
        splitByRow=1,
        splitInRow=1,
        style=TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            # No vertical rule between columns in the originals.
            ("LEFTPADDING", (0, 0), (0, -1), 0),
            ("RIGHTPADDING", (0, 0), (0, -1), 14),
            ("LEFTPADDING", (1, 0), (1, -1), 6),
            ("RIGHTPADDING", (1, 0), (1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]),
    )
    flow.append(table)
    flow.append(_PageMarker(f"article_end:{index}"))

    if map_image and map_image.exists():
        flow.append(NextPageTemplate("plate"))
        flow.append(PageBreak())
        flow += _map_flowables(map_image)
        flow.append(NextPageTemplate("body"))

    flow.append(PageBreak())
    return flow


def _map_flowables(map_image: Path) -> list:
    """Full-page plate: image only — the plate's own title box carries the
    caption in the originals; no text is set beneath the frame."""
    avail_w = S.PAGE_WIDTH - S.LEFT_MARGIN - S.RIGHT_MARGIN
    avail_h = S.PAGE_HEIGHT - S.TOP_MARGIN - S.BOTTOM_MARGIN - 0.4 * inch
    img = Image(str(map_image), width=avail_w, height=avail_h,
                kind="proportional")
    return [Spacer(1, 0.15 * inch), img]


# ---------------------------------------------------------------------------
# NOTES section
# ---------------------------------------------------------------------------
def _notes_flowables(notes: list[Note],
                     st: dict[str, ParagraphStyle]) -> list:
    if not notes:
        return []
    flow: list = [
        _PageMarker("notes:first"),
        Spacer(1, 0.5 * inch),
        Paragraph("NOTES", st["notes_title"]),
    ]
    for n in notes:
        flow.append(Paragraph(
            f"<u>{n.region}</u>:  {n.text_en}", st["note"],
        ))
        flow.append(Paragraph(n.text_cn, st["note_cn"]))
    flow.append(_PageMarker("notes:last"))
    return flow


# ---------------------------------------------------------------------------
# Annex — full-width single-column typewriter, A-numbered pages
# ---------------------------------------------------------------------------
def _annex_flowables(annex: Annex, st: dict[str, ParagraphStyle],
                     map_image: Path | None) -> list:
    flow: list = [
        NextPageTemplate("annex"),
        PageBreak(),
        Spacer(1, 0.4 * inch),
        Paragraph("ANNEX", st["annex_label"]),
        Paragraph(annex.title_en.upper(), st["annex_title"]),
        Paragraph(annex.title_cn, st["annex_title_cn"]),
    ]
    for en, cn in zip(annex.body_en, annex.body_cn):
        flow.append(Paragraph(en, st["annex_body_en"]))
        flow.append(Paragraph(cn, st["annex_body_cn"]))
    flow.append(_PageMarker("annex:last"))
    if map_image and map_image.exists():
        flow.append(NextPageTemplate("plate"))
        flow.append(PageBreak())
        flow += _map_flowables(map_image)
    return flow


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------
_MONTHS = ["January", "February", "March", "April", "May", "June",
           "July", "August", "September", "October", "November", "December"]


def _format_date(iso: str) -> str:
    """'September 9, 1976' — the 1976 cover/TOC date format."""
    try:
        y, m, d = iso.split("-")
        return f"{_MONTHS[int(m) - 1]} {int(d)}, {y}"
    except Exception:  # noqa: BLE001
        return iso


def _classification_titlecase(classification: str) -> str:
    """'TOP SECRET' -> 'Top Secret' (italic serif, caps T and S only)."""
    return classification.title()


# ---------------------------------------------------------------------------
# Story assembly + two-pass build
# ---------------------------------------------------------------------------
def _build_story(brief: Brief, st: dict[str, ParagraphStyle],
                 article_maps: dict[int, Path], annex_map: Path | None,
                 labels: dict[str, str] | None) -> list:
    story: list = [
        # Cover and inside cover are drawn entirely on the canvas.
        Spacer(1, 1),
        NextPageTemplate("inside"),
        PageBreak(),
        Spacer(1, 1),
        NextPageTemplate("toc"),
        PageBreak(),
    ]
    story += _toc_flowables(brief, st, article_maps, annex_map, labels)
    story.append(NextPageTemplate("body"))
    story.append(PageBreak())

    for idx, art in enumerate(brief.articles):
        story += _article_flowables(art, idx, st, article_maps.get(idx))

    story += _notes_flowables(brief.notes, st)

    if brief.annex:
        story += _annex_flowables(brief.annex, st, annex_map)

    story.append(NextPageTemplate("back"))
    story.append(PageBreak())
    story.append(Spacer(1, 1))
    return story


def _make_doc(brief: Brief, target) -> BaseDocTemplate:  # noqa: ANN001
    frame = Frame(
        S.LEFT_MARGIN, S.BOTTOM_MARGIN,
        S.PAGE_WIDTH - S.LEFT_MARGIN - S.RIGHT_MARGIN,
        S.PAGE_HEIGHT - S.TOP_MARGIN - S.BOTTOM_MARGIN,
        id="main", showBoundary=0,
    )
    doc = BaseDocTemplate(
        target, pagesize=LETTER,
        leftMargin=S.LEFT_MARGIN, rightMargin=S.RIGHT_MARGIN,
        topMargin=S.TOP_MARGIN, bottomMargin=S.BOTTOM_MARGIN,
        title=f"The President's Daily Brief — {brief.date}",
        author="CIA (replica)",
    )
    doc._brief = brief  # type: ignore[attr-defined]
    doc._labels = {}  # type: ignore[attr-defined]
    doc._page_mode = "body"  # type: ignore[attr-defined]
    doc.addPageTemplates([
        PageTemplate(id="cover", frames=[frame], onPage=_onpage_cover),
        PageTemplate(id="inside", frames=[frame], onPage=_onpage_inside),
        PageTemplate(id="toc", frames=[frame], onPage=_onpage_toc),
        PageTemplate(id="body", frames=[frame], onPage=_onpage_body),
        PageTemplate(id="plate", frames=[frame], onPage=_onpage_plate),
        PageTemplate(id="annex", frames=[frame], onPage=_onpage_annex),
        PageTemplate(id="back", frames=[frame], onPage=_onpage_back),
    ])
    return doc


def build_pdf(brief: Brief, out_path: Path,
              article_maps: dict[int, Path] | None = None,
              annex_map: Path | None = None) -> dict[str, str]:
    """Render the PDF; returns the resolved page-label map
    (e.g. {"article:0": "1", "notes:first": "9", ...})."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cn_font, cn_font_bold = S.register_cjk_fonts()
    st = _styles(cn_font, cn_font_bold)
    article_maps = article_maps or {}

    # Pass 1: throwaway render to resolve page labels for the TOC.
    doc1 = _make_doc(brief, io.BytesIO())
    doc1.build(_build_story(brief, st, article_maps, annex_map, labels=None))
    labels: dict[str, str] = dict(doc1._labels)  # type: ignore[attr-defined]

    # Pass 2: real render with resolved labels.
    doc2 = _make_doc(brief, str(out_path))
    doc2.build(_build_story(brief, st, article_maps, annex_map, labels=labels))
    return labels
