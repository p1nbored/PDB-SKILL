"""Compose the PDB replica PDF using reportlab.

Layout features:
- Cover: binding dashes, declass stamps, bold TOP SECRET banners
  top and bottom, block title, date + struck TOP SECRET bottom-right.
- Table of Contents: each article listed with region, short summary,
  and page number; annex topic listed at the end.
- Body pages: "FOR THE PRESIDENT ONLY" running header AND footer in
  addition to the declassification stamps.
- Article pages: REGION: TITLE in all caps, Chinese title beneath, a
  two-column layout with the pull-quote summary in the narrow left
  column and the bilingual analysis in the wide right column.
- NOTES section: shorter country-tagged briefs.
- Annex: independent "A1, A2, ..." pagination for the deep-dive
  analysis.
"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    BaseDocTemplate, CondPageBreak, Frame, Image, PageBreak,
    PageTemplate, Paragraph, Spacer, Table, TableStyle,
)
from reportlab.platypus.doctemplate import NextPageTemplate

from content_schema import Annex, Article, Brief, Note
import styles as S


# ---------------------------------------------------------------------------
# Page decorations
# ---------------------------------------------------------------------------
def _draw_binding_dashes(c: Canvas) -> None:
    c.saveState()
    c.setFillColor(colors.black)
    y = S.PAGE_HEIGHT - 0.25 * inch
    n = 18
    gutter = (S.PAGE_WIDTH - 0.6 * inch) / n
    for i in range(n):
        x = 0.3 * inch + i * gutter
        c.rect(x, y, gutter * 0.55, 0.05 * inch, stroke=0, fill=1)
    c.restoreState()


def _draw_declass_stamp(c: Canvas, brief: Brief, y: float) -> None:
    c.saveState()
    c.setFont("Helvetica", S.BANNER_SIZE)
    c.setFillColor(colors.black)
    c.drawString(0.45 * inch, y, brief.declass_header)
    c.restoreState()


def _draw_classification_banner(c: Canvas, text: str, y: float,
                                struck: bool = False) -> None:
    c.saveState()
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.black)
    tw = c.stringWidth(text, "Helvetica-Bold", 11)
    x = (S.PAGE_WIDTH - tw) / 2
    c.drawString(x, y, text)
    if struck:
        c.setLineWidth(0.9)
        c.line(x - 3, y + 3.5, x + tw + 3, y + 3.5)
    c.restoreState()


def _draw_for_president_only(c: Canvas, y: float, strike: bool = True) -> None:
    """Bold centered running banner used on body and annex pages."""
    c.saveState()
    c.setFont("Helvetica-Bold", S.FOOTER_SIZE + 1)
    c.setFillColor(colors.black)
    text = "FOR THE PRESIDENT ONLY"
    tw = c.stringWidth(text, "Helvetica-Bold", S.FOOTER_SIZE + 1)
    x = (S.PAGE_WIDTH - tw) / 2
    c.drawString(x, y, text)
    if strike:
        c.setLineWidth(0.6)
        c.line(x - 3, y - 2, x + tw + 3, y - 2)
    c.restoreState()


def _draw_page_number(c: Canvas, label: str) -> None:
    c.saveState()
    c.setFont("Helvetica", S.FOOTER_SIZE)
    c.drawRightString(S.PAGE_WIDTH - 0.5 * inch, 0.45 * inch, label)
    c.restoreState()


# ---- per-template onPage callbacks ----------------------------------------
def _onpage_cover(c: Canvas, doc) -> None:  # noqa: ANN001
    brief: Brief = doc._brief  # type: ignore[attr-defined]
    _draw_binding_dashes(c)
    _draw_declass_stamp(c, brief, S.PAGE_HEIGHT - 0.42 * inch)
    _draw_classification_banner(c, brief.classification,
                                S.PAGE_HEIGHT - 0.70 * inch)
    _draw_classification_banner(c, brief.classification, 0.75 * inch)
    _draw_declass_stamp(c, brief, 0.30 * inch)


def _onpage_toc(c: Canvas, doc) -> None:  # noqa: ANN001
    brief: Brief = doc._brief  # type: ignore[attr-defined]
    _draw_binding_dashes(c)
    _draw_declass_stamp(c, brief, S.PAGE_HEIGHT - 0.42 * inch)
    _draw_for_president_only(c, S.PAGE_HEIGHT - 0.62 * inch)
    _draw_for_president_only(c, 0.72 * inch)
    _draw_declass_stamp(c, brief, 0.30 * inch)
    _draw_page_number(c, "i")


def _body_page_label(doc) -> str:  # noqa: ANN001
    """Derive the page label for body vs annex."""
    mode = getattr(doc, "_page_mode", "body")
    if mode == "annex":
        annex_page = doc.page - getattr(doc, "_annex_start_page", doc.page) + 1
        return f"A{annex_page}"
    body_page = doc.page - getattr(doc, "_body_start_page", 2) + 1
    return f"-{body_page}-"


def _onpage_body(c: Canvas, doc) -> None:  # noqa: ANN001
    brief: Brief = doc._brief  # type: ignore[attr-defined]
    _draw_binding_dashes(c)
    _draw_declass_stamp(c, brief, S.PAGE_HEIGHT - 0.42 * inch)
    _draw_for_president_only(c, S.PAGE_HEIGHT - 0.62 * inch)
    _draw_for_president_only(c, 0.72 * inch)
    _draw_declass_stamp(c, brief, 0.30 * inch)
    _draw_page_number(c, _body_page_label(doc))


def _onpage_annex(c: Canvas, doc) -> None:  # noqa: ANN001
    # Mark the first annex-template page so the label math starts at A1.
    if not getattr(doc, "_annex_start_page", None):
        doc._annex_start_page = doc.page  # type: ignore[attr-defined]
    doc._page_mode = "annex"  # type: ignore[attr-defined]
    _onpage_body(c, doc)


# ---------------------------------------------------------------------------
# Paragraph styles
# ---------------------------------------------------------------------------
def _styles(cn_font: str, cn_font_bold: str) -> dict[str, ParagraphStyle]:
    # NOTE: widow/orphan control (allowWidows=0, allowOrphans=0) is applied
    # to every prose style so that no paragraph splits with a stray 1-2 line
    # tail onto a fresh page. Bilingual pairs are additionally bound via
    # keepWithNext on the English half -- see _article_flowables below.
    return {
        "heading_en": ParagraphStyle(
            "heading_en", fontName=S.BODY_EN_BOLD, fontSize=S.TITLE_SIZE + 1,
            leading=(S.TITLE_SIZE + 1) * 1.25, alignment=TA_LEFT,
            textColor=colors.black, spaceAfter=1,
            allowWidows=0, allowOrphans=0, keepWithNext=1,
        ),
        "heading_cn": ParagraphStyle(
            "heading_cn", fontName=cn_font_bold, fontSize=S.TITLE_SIZE + 1,
            leading=(S.TITLE_SIZE + 1) * 1.3, alignment=TA_LEFT,
            textColor=colors.black, spaceAfter=4,
            allowWidows=0, allowOrphans=0, keepWithNext=1,
        ),
        "summary_en": ParagraphStyle(
            "summary_en", fontName=S.BODY_EN_BOLD, fontSize=S.BODY_SIZE,
            leading=S.BODY_LEADING, alignment=TA_LEFT, textColor=colors.black,
            spaceAfter=6, allowWidows=0, allowOrphans=0, keepWithNext=1,
        ),
        "summary_cn": ParagraphStyle(
            "summary_cn", fontName=cn_font_bold, fontSize=S.BODY_SIZE + 0.5,
            leading=S.BODY_LEADING + 1, alignment=TA_LEFT, textColor=colors.black,
            allowWidows=0, allowOrphans=0,
        ),
        "body_en": ParagraphStyle(
            "body_en", fontName=S.BODY_EN, fontSize=S.BODY_SIZE,
            leading=S.BODY_LEADING, alignment=TA_LEFT, textColor=colors.black,
            firstLineIndent=16, spaceAfter=1,
            allowWidows=0, allowOrphans=0, keepWithNext=1,
        ),
        "body_cn": ParagraphStyle(
            "body_cn", fontName=cn_font, fontSize=S.BODY_SIZE + 0.5,
            leading=S.BODY_LEADING + 1, alignment=TA_LEFT, textColor=colors.black,
            firstLineIndent=22, spaceAfter=4,
            allowWidows=0, allowOrphans=0,
        ),
        # Variant used for the final CN paragraph when a sources line
        # follows, so the sources cannot orphan onto a fresh page.
        "body_cn_bind": ParagraphStyle(
            "body_cn_bind", fontName=cn_font, fontSize=S.BODY_SIZE + 0.5,
            leading=S.BODY_LEADING + 1, alignment=TA_LEFT, textColor=colors.black,
            firstLineIndent=22, spaceAfter=4,
            allowWidows=0, allowOrphans=0, keepWithNext=1,
        ),
        "sources": ParagraphStyle(
            "sources", fontName="Helvetica-Oblique", fontSize=S.FOOTER_SIZE + 0.5,
            leading=S.FOOTER_SIZE + 2, alignment=TA_LEFT, textColor=colors.black,
            leftIndent=10, spaceBefore=2,
            allowWidows=0, allowOrphans=0,
        ),
        "map_caption": ParagraphStyle(
            "map_caption", fontName=S.BODY_EN, fontSize=S.BODY_SIZE - 0.5,
            leading=S.BODY_LEADING - 2, alignment=TA_CENTER,
            textColor=colors.black, spaceBefore=6,
        ),
        "cover_title": ParagraphStyle(
            "cover_title", fontName="Helvetica-Bold", fontSize=S.COVER_TITLE_SIZE,
            leading=S.COVER_TITLE_SIZE * 1.1, alignment=TA_LEFT,
            textColor=colors.black,
        ),
        "cover_date": ParagraphStyle(
            "cover_date", fontName="Helvetica-Bold", fontSize=S.COVER_DATE_SIZE,
            leading=S.COVER_DATE_SIZE * 1.2, alignment=TA_RIGHT,
            textColor=colors.black,
        ),
        "toc_entry": ParagraphStyle(
            "toc_entry", fontName=S.BODY_EN, fontSize=S.BODY_SIZE,
            leading=S.BODY_LEADING + 1, alignment=TA_LEFT, textColor=colors.black,
            spaceAfter=4,
        ),
        "toc_heading": ParagraphStyle(
            "toc_heading", fontName="Helvetica-Bold", fontSize=16,
            leading=20, alignment=TA_LEFT, textColor=colors.black,
            spaceAfter=10,
        ),
        "toc_annex": ParagraphStyle(
            "toc_annex", fontName="Helvetica-Bold", fontSize=S.BODY_SIZE + 0.5,
            leading=S.BODY_LEADING + 1, alignment=TA_LEFT, textColor=colors.black,
            spaceBefore=10,
        ),
        "note": ParagraphStyle(
            "note", fontName=S.BODY_EN, fontSize=S.BODY_SIZE - 0.5,
            leading=S.BODY_LEADING - 1, alignment=TA_LEFT, textColor=colors.black,
            firstLineIndent=0, spaceAfter=2, leftIndent=0,
        ),
        "note_cn": ParagraphStyle(
            "note_cn", fontName=cn_font, fontSize=S.BODY_SIZE,
            leading=S.BODY_LEADING, alignment=TA_LEFT, textColor=colors.black,
            spaceAfter=8,
        ),
        "notes_title": ParagraphStyle(
            "notes_title", fontName="Helvetica-Bold", fontSize=S.TITLE_SIZE + 4,
            leading=22, alignment=TA_CENTER, textColor=colors.black,
            spaceAfter=10, spaceBefore=6,
        ),
        "note_region": ParagraphStyle(
            "note_region", fontName=S.BODY_EN_BOLD, fontSize=S.BODY_SIZE,
            leading=S.BODY_LEADING, alignment=TA_LEFT, textColor=colors.black,
            spaceBefore=4, spaceAfter=1,
        ),
        "annex_title": ParagraphStyle(
            "annex_title", fontName="Helvetica-Bold", fontSize=S.TITLE_SIZE + 6,
            leading=S.TITLE_SIZE + 10, alignment=TA_CENTER, textColor=colors.black,
            spaceBefore=0, spaceAfter=4,
        ),
        "annex_title_cn": ParagraphStyle(
            "annex_title_cn", fontName=cn_font_bold, fontSize=S.TITLE_SIZE + 3,
            leading=S.TITLE_SIZE + 8, alignment=TA_CENTER, textColor=colors.black,
            spaceAfter=16,
        ),
        "annex_label": ParagraphStyle(
            "annex_label", fontName="Helvetica-Bold", fontSize=12,
            leading=16, alignment=TA_CENTER, textColor=colors.black,
            spaceAfter=2,
        ),
    }


# ---------------------------------------------------------------------------
# Cover + TOC
# ---------------------------------------------------------------------------
def _cover_flowables(brief: Brief, st: dict[str, ParagraphStyle]) -> list:
    flow = [
        Spacer(1, 1.8 * inch),
        Paragraph("THE PRESIDENT'S", st["cover_title"]),
        Paragraph("DAILY BRIEF", st["cover_title"]),
        Spacer(1, 4.4 * inch),
        Paragraph(_format_date(brief.date), st["cover_date"]),
        Paragraph(f"<strike>{brief.classification}</strike>", st["cover_date"]),
        NextPageTemplate("toc"),
        PageBreak(),
    ]
    return flow


def _toc_flowables(brief: Brief, st: dict[str, ParagraphStyle],
                   article_pages: list[int]) -> list:
    flow = [
        Spacer(1, 0.2 * inch),
        Paragraph("CONTENTS", st["toc_heading"]),
    ]
    for art, page in zip(brief.articles, article_pages):
        one_line = art.summary_en or (art.body_en[0].split(". ")[0] + ".")
        line = (
            f"<b>{art.region.upper()}:</b> {art.title_en}"
            f" <font size='8'>..................... {page}</font><br/>"
            f"<i>{_ellipsize(one_line, 160)}</i>"
        )
        flow.append(Paragraph(line, st["toc_entry"]))
    if brief.annex:
        flow.append(Paragraph(
            f"ANNEX: {brief.annex.title_en}", st["toc_annex"],
        ))
    flow.append(NextPageTemplate("body"))
    flow.append(PageBreak())
    return flow


def _ellipsize(text: str, limit: int) -> str:
    text = text.strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "\u2026"


# ---------------------------------------------------------------------------
# Article layout (two-column)
# ---------------------------------------------------------------------------
def _article_flowables(article: Article, st: dict[str, ParagraphStyle],
                       map_image: Path | None) -> list:
    """Compose one article in the classic two-column PDB layout.

    Left column is the bilingual pull-quote summary (narrow). Right
    column is the bilingual analysis (wide). The heading paragraphs sit
    above the Table.

    To prevent heading-only orphan pages, the body is split into one
    Table row per EN/CN paragraph pair rather than a single giant row.
    reportlab's splitByRow then breaks cleanly between paragraph pairs,
    so the heading + summary + first body pair always fit together.
    """
    flow = []

    # Defensive: guarantee room for heading + at least one body pair.
    flow.append(CondPageBreak(5.0 * inch))

    heading_en_html = f"<u>{article.region.upper()}: {article.title_en.upper()}</u>"
    flow.append(Paragraph(heading_en_html, st["heading_en"]))
    flow.append(Paragraph(article.title_cn, st["heading_cn"]))

    marks = "  ".join(article.compartments) or "50X1"
    flow.append(Paragraph(
        f"<font name='Helvetica-Bold' size='{S.COMPARTMENT_SIZE}'>{marks}</font>",
        st["body_en"],
    ))
    flow.append(Spacer(1, 4))

    # Build left-column summary cells (shown only on the article's first page).
    summary_cells: list = []
    if article.summary_en:
        summary_cells.append(Paragraph(article.summary_en, st["summary_en"]))
    if article.summary_cn:
        summary_cells.append(Paragraph(article.summary_cn, st["summary_cn"]))
    if not summary_cells:
        lead = article.body_en[0].split(". ")[0] + "."
        summary_cells.append(Paragraph(
            f"<b>{_ellipsize(lead, 180)}</b>", st["summary_en"],
        ))

    # Build right-column analysis cells, one Table row per EN/CN pair so
    # splitByRow can split between paragraphs instead of orphaning the
    # heading when the whole row won't fit.
    pairs = list(zip(article.body_en, article.body_cn))
    table_data: list = []
    for i, (en_para, cn_para) in enumerate(pairs):
        is_last = (i == len(pairs) - 1)
        cn_style = st["body_cn_bind"] if (is_last and article.sources) else st["body_cn"]
        right_cells = [
            Paragraph(en_para, st["body_en"]),
            Paragraph(cn_para, cn_style),
        ]
        # Summary only occupies the very first row.
        left_cells = summary_cells if i == 0 else ""
        table_data.append([left_cells, right_cells])

    if article.sources:
        table_data.append([
            "",
            Paragraph(
                "<i>Sources: " + "; ".join(article.sources) + "</i>",
                st["sources"],
            ),
        ])

    avail_w = S.PAGE_WIDTH - S.LEFT_MARGIN - S.RIGHT_MARGIN
    left_w = avail_w * 0.30
    right_w = avail_w - left_w - 0.15 * inch
    last_row = len(table_data) - 1

    table = Table(
        table_data,
        colWidths=[left_w, right_w],
        hAlign="LEFT",
        splitByRow=1,
        splitInRow=1,
        style=TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            # Vertical divider runs the full height of the body table.
            ("LINEAFTER", (0, 0), (0, last_row), 0.4, colors.black),
            # Left column paddings.
            ("LEFTPADDING", (0, 0), (0, last_row), 2),
            ("RIGHTPADDING", (0, 0), (0, last_row), 8),
            # Right column paddings.
            ("LEFTPADDING", (1, 0), (1, last_row), 10),
            ("RIGHTPADDING", (1, 0), (1, last_row), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]),
    )
    flow.append(table)

    if map_image and map_image.exists():
        flow.append(PageBreak())
        flow += _map_flowables(map_image, article.map_title or
                               f"Reference map — {article.region}", st)

    flow.append(PageBreak())
    return flow


def _map_flowables(map_image: Path, caption: str,
                   st: dict[str, ParagraphStyle]) -> list:
    avail_w = S.PAGE_WIDTH - S.LEFT_MARGIN - S.RIGHT_MARGIN
    avail_h = S.PAGE_HEIGHT - S.TOP_MARGIN - S.BOTTOM_MARGIN - 1.3 * inch
    img = Image(str(map_image), width=avail_w, height=avail_h, kind="proportional")
    return [Spacer(1, 0.2 * inch), img, Paragraph(caption, st["map_caption"])]


# ---------------------------------------------------------------------------
# NOTES section
# ---------------------------------------------------------------------------
def _notes_flowables(notes: list[Note], st: dict[str, ParagraphStyle]) -> list:
    if not notes:
        return []
    flow = [Paragraph("NOTES", st["notes_title"])]
    for n in notes:
        flow.append(Paragraph(n.region.upper(), st["note_region"]))
        flow.append(Paragraph(n.text_en, st["note"]))
        flow.append(Paragraph(n.text_cn, st["note_cn"]))
    return flow


# ---------------------------------------------------------------------------
# Annex
# ---------------------------------------------------------------------------
def _annex_flowables(annex: Annex, st: dict[str, ParagraphStyle],
                     map_image: Path | None) -> list:
    flow = [
        NextPageTemplate("annex"),
        PageBreak(),
        Paragraph("ANNEX", st["annex_label"]),
        Paragraph(annex.title_en, st["annex_title"]),
        Paragraph(annex.title_cn, st["annex_title_cn"]),
    ]
    # Bilingual, single column (annex is long-form).
    for en, cn in zip(annex.body_en, annex.body_cn):
        flow.append(Paragraph(en, st["body_en"]))
        flow.append(Paragraph(cn, st["body_cn"]))
    if map_image and map_image.exists():
        flow.append(PageBreak())
        flow += _map_flowables(
            map_image, annex.map_title or f"Annex map — {annex.title_en}", st,
        )
    return flow


# ---------------------------------------------------------------------------
# Date helper
# ---------------------------------------------------------------------------
def _format_date(iso: str) -> str:
    try:
        y, m, d = iso.split("-")
        months = ["JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
                  "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER",
                  "DECEMBER"]
        return f"{int(d)} {months[int(m) - 1]} {y}"
    except Exception:  # noqa: BLE001
        return iso


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def build_pdf(brief: Brief, out_path: Path,
              article_maps: dict[int, Path] | None = None,
              annex_map: Path | None = None) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cn_font, cn_font_bold = S.register_cjk_fonts()
    st = _styles(cn_font, cn_font_bold)

    frame = Frame(
        S.LEFT_MARGIN, S.BOTTOM_MARGIN,
        S.PAGE_WIDTH - S.LEFT_MARGIN - S.RIGHT_MARGIN,
        S.PAGE_HEIGHT - S.TOP_MARGIN - S.BOTTOM_MARGIN,
        id="main", showBoundary=0,
    )
    cover_frame = Frame(
        S.LEFT_MARGIN, S.BOTTOM_MARGIN,
        S.PAGE_WIDTH - S.LEFT_MARGIN - S.RIGHT_MARGIN,
        S.PAGE_HEIGHT - S.TOP_MARGIN - S.BOTTOM_MARGIN,
        id="cover", showBoundary=0,
    )

    doc = BaseDocTemplate(
        str(out_path), pagesize=LETTER,
        leftMargin=S.LEFT_MARGIN, rightMargin=S.RIGHT_MARGIN,
        topMargin=S.TOP_MARGIN, bottomMargin=S.BOTTOM_MARGIN,
        title=f"President's Daily Brief — {brief.date}",
        author="CIA/DI (replica)",
    )
    doc._brief = brief  # type: ignore[attr-defined]
    doc._body_start_page = 3  # cover = 1, toc = 2, body begins at 3
    doc._page_mode = "body"  # type: ignore[attr-defined]
    doc.addPageTemplates([
        PageTemplate(id="cover", frames=[cover_frame], onPage=_onpage_cover),
        PageTemplate(id="toc", frames=[frame], onPage=_onpage_toc),
        PageTemplate(id="body", frames=[frame], onPage=_onpage_body),
        PageTemplate(id="annex", frames=[frame], onPage=_onpage_annex),
    ])

    # Pre-compute article page numbers for the TOC. Cover=1, TOC=2. Each
    # article takes one page for body plus one extra if it has a map.
    article_maps = article_maps or {}
    article_pages = []
    cursor = 3  # first body page after cover + toc
    for i, art in enumerate(brief.articles):
        article_pages.append(cursor - 2)  # body label starts at 1 on page 3
        cursor += 1 + (1 if article_maps.get(i) else 0)

    story: list = []
    story += _cover_flowables(brief, st)
    story += _toc_flowables(brief, st, article_pages)

    for idx, art in enumerate(brief.articles):
        story += _article_flowables(art, st, article_maps.get(idx))

    story += _notes_flowables(brief.notes, st)

    if brief.annex:
        story += _annex_flowables(brief.annex, st, annex_map)

    doc.build(story)
