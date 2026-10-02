"""Canvas-drawn page furniture for the PDB replica.

Everything here is positioned from measurements of the September 9,
1976 and July 28, 1976 booklets (see styles.py): the cover, the inside
cover exemption box, banners, release lines, page labels, the
"--continued" catchline, the vertical ANNEX tab, map plates, and the
back cover.
"""
from __future__ import annotations

import math
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas

import styles as S

STAMP = "25X1"
_MONTHS = ("January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December")
_EO_BOX_LINES = (
    "Exempt from general",
    "declassification schedule of E.O. 11652",
    "exemption category 5B(1),(2),(3)",
    "declassified only on approval of",
    "the Director of Central Intelligence",
)


def format_date(iso: str) -> str:
    """'2026-04-18' -> 'April 18, 2026' (the 1975-76 cover and TOC style)."""
    try:
        y, m, d = iso.split("-")
        return f"{_MONTHS[int(m) - 1]} {int(d)}, {y}"
    except (ValueError, IndexError):
        return iso


def classification_label(classification: str) -> str:
    """'TOP SECRET' -> 'Top Secret' (set in italic Garamond)."""
    return classification.title()


# ---- shared furniture -------------------------------------------------------
def draw_declass_lines(c: Canvas, header: str) -> None:
    """Release line stamped at the extreme top and bottom of every scan."""
    c.saveState()
    c.setFont(S.SANS, S.DECLASS_SIZE)
    c.setFillColor(colors.black)
    c.drawCentredString(S.PAGE_WIDTH / 2, S.DECLASS_TOP_Y, header)
    c.drawCentredString(S.PAGE_WIDTH / 2, S.DECLASS_BOTTOM_Y, header)
    c.restoreState()


def draw_banners(c: Canvas) -> None:
    """FOR THE PRESIDENT ONLY, italic Garamond caps, top and bottom."""
    c.saveState()
    text = "FOR THE PRESIDENT ONLY"
    spacing = 0.35
    width = (stringWidth(text, S.SERIF_ITALIC, S.BANNER_SIZE)
             + spacing * (len(text) - 1))
    for y in (S.BANNER_TOP_Y, S.BANNER_BOTTOM_Y):
        t = c.beginText((S.PAGE_WIDTH - width) / 2, y)
        t.setFont(S.SERIF_ITALIC, S.BANNER_SIZE)
        t.setCharSpace(spacing)
        t.textOut(text)
        c.drawText(t)
    c.restoreState()


def draw_page_label(c: Canvas, label: str) -> None:
    c.saveState()
    c.setFont(S.TYPE, S.EN_SIZE)
    c.drawCentredString(S.PAGE_WIDTH / 2, S.PAGE_NO_Y, label)
    c.restoreState()


def draw_continued(c: Canvas, right_x: float) -> None:
    """'--continued' catchline flush with the end of the text column."""
    c.saveState()
    c.setFont(S.TYPE, S.EN_SIZE)
    c.drawRightString(right_x, S.CONTINUED_Y, "--continued")
    c.restoreState()


def draw_stamp(c: Canvas, x: float, y: float, text: str = STAMP) -> None:
    """Sans-serif exemption stamp added by the declassification reviewer."""
    c.saveState()
    c.setFont(S.SANS, S.STAMP_SIZE)
    c.setFillColor(colors.black)
    c.drawString(x, y, text)
    c.restoreState()


# ---- cover ---------------------------------------------------------------------
def _arc_text(c: Canvas, text: str, cx: float, cy: float, radius: float,
              center_deg: float, span_deg: float, top: bool) -> None:
    """Letters fitted to *span_deg* of arc: upright along the top band,
    tops toward the centre along the bottom band."""
    size = math.radians(span_deg) * radius / stringWidth(text, "Helvetica-Bold", 1)
    widths = [stringWidth(ch, "Helvetica-Bold", size) for ch in text]
    span = sum(widths) / radius
    direction = -1 if top else 1
    angle = math.radians(center_deg) - direction * span / 2
    for ch, w in zip(text, widths):
        step = w / radius
        mid = angle + direction * step / 2
        c.saveState()
        c.translate(cx + radius * math.cos(mid), cy + radius * math.sin(mid))
        c.rotate(math.degrees(mid) + (-90 if top else 90))
        c.setFont("Helvetica-Bold", size)
        c.drawCentredString(0, 0, ch)
        c.restoreState()
        angle += direction * step


def _compass_star(c: Canvas, cx: float, cy: float, radius: float) -> None:
    """Sixteen-point compass rose: long cardinal rays, short between."""
    for k in range(16):
        ang = math.radians(90 - k * 22.5)
        tip = radius * (1.0 if k % 4 == 0 else 0.72 if k % 2 == 0 else 0.48)
        half = radius * 0.11
        p = c.beginPath()
        p.moveTo(cx + half * math.cos(ang + math.pi / 2),
                 cy + half * math.sin(ang + math.pi / 2))
        p.lineTo(cx + tip * math.cos(ang), cy + tip * math.sin(ang))
        p.lineTo(cx + half * math.cos(ang - math.pi / 2),
                 cy + half * math.sin(ang - math.pi / 2))
        p.close()
        c.drawPath(p, stroke=0, fill=1)


def _shield_path(c: Canvas, cx: float, w: float, top: float, bottom: float):  # noqa: ANN202
    h = top - bottom
    p = c.beginPath()
    p.moveTo(cx - w / 2, top)
    p.lineTo(cx + w / 2, top)
    p.lineTo(cx + w / 2, top - h * 0.50)
    p.curveTo(cx + w / 2, top - h * 0.82, cx + w * 0.16, top - h * 0.94, cx, bottom)
    p.curveTo(cx - w * 0.16, top - h * 0.94, cx - w / 2, top - h * 0.82,
              cx - w / 2, top - h * 0.50)
    p.close()
    return p


def _shield(c: Canvas, cx: float, cy: float, s: float) -> float:
    """Double-ruled heater shield bearing the compass rose; returns its top."""
    w, top, bottom = s * 0.27, cy + s * 0.11, cy - s * 0.23
    inset = s * 0.014
    c.setFillColor(colors.white)
    c.setLineWidth(0.8)
    c.drawPath(_shield_path(c, cx, w, top, bottom), stroke=1, fill=1)
    c.setLineWidth(0.35)
    c.drawPath(_shield_path(c, cx, w - 2 * inset, top - inset, bottom + inset * 1.6),
               stroke=1, fill=0)
    c.setFillColor(colors.black)
    _compass_star(c, cx, cy - s * 0.045, s * 0.11)
    return top


def _eagle(c: Canvas, cx: float, base: float, s: float) -> None:
    """Eagle's head and folded wings as a line engraving, head to the
    viewer's left, perched on the shield."""
    u = s * 0.01
    wings = c.beginPath()
    wings.moveTo(cx - 9.5 * u, base)
    for k in range(5):            # ragged primary feathers along the base
        x = cx - 9.5 * u + k * 4.75 * u
        wings.lineTo(x + 1.2 * u, base - 1.4 * u)
        wings.lineTo(x + 2.4 * u, base)
    wings.lineTo(cx + 9.5 * u, base)
    wings.curveTo(cx + 9.0 * u, base + 5.5 * u, cx + 4.0 * u, base + 8.5 * u,
                  cx + 1.5 * u, base + 9.0 * u)
    wings.lineTo(cx + 1.0 * u, base + 12.5 * u)     # back of the neck
    wings.curveTo(cx + 0.5 * u, base + 15.0 * u, cx - 3.0 * u, base + 15.5 * u,
                  cx - 4.5 * u, base + 13.5 * u)    # crown
    wings.lineTo(cx - 7.2 * u, base + 12.0 * u)     # upper mandible
    wings.lineTo(cx - 6.2 * u, base + 10.6 * u)     # hooked tip
    wings.lineTo(cx - 4.2 * u, base + 11.3 * u)
    wings.curveTo(cx - 3.5 * u, base + 9.5 * u, cx - 3.0 * u, base + 8.5 * u,
                  cx - 4.0 * u, base + 8.0 * u)     # throat
    wings.curveTo(cx - 8.5 * u, base + 7.0 * u, cx - 9.5 * u, base + 4.0 * u,
                  cx - 9.5 * u, base)
    wings.close()
    c.setFillColor(colors.white)
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.55)
    c.drawPath(wings, stroke=1, fill=1)
    c.setFillColor(colors.black)
    c.circle(cx - 3.4 * u, base + 12.6 * u, 0.75 * u, stroke=0, fill=1)
    c.setLineWidth(0.35)
    for k in range(4):            # feather rows on the folded wing
        y = base + (1.6 + 1.7 * k) * u
        c.line(cx - 7.5 * u + k * 1.2 * u, y, cx + 8.0 * u - k * 1.6 * u, y + 0.9 * u)
    for k in range(3):            # hackles down the neck
        x = cx - 2.5 * u + k * 1.3 * u
        c.line(x, base + 9.2 * u, x + 0.6 * u, base + 11.6 * u)


def _ribbon(c: Canvas, cx: float, cy: float, s: float) -> None:
    """Curved scroll carrying UNITED STATES OF AMERICA."""
    r_in, r_out = s * 0.268, s * 0.352
    c.setLineWidth(0.5)
    p = c.beginPath()
    p.arc(cx - r_out, cy - r_out, cx + r_out, cy + r_out, 208, 124)
    c.drawPath(p, stroke=1, fill=0)
    p = c.beginPath()
    p.arc(cx - r_in, cy - r_in, cx + r_in, cy + r_in, 208, 124)
    c.drawPath(p, stroke=1, fill=0)
    for deg, curl in ((208, -1), (332, 1)):
        rad = math.radians(deg)
        x0, y0 = cx + r_in * math.cos(rad), cy + r_in * math.sin(rad)
        x1, y1 = cx + r_out * math.cos(rad), cy + r_out * math.sin(rad)
        end = c.beginPath()
        end.moveTo(x0, y0)
        end.curveTo(x0 + curl * s * 0.03, y0 + s * 0.01,
                    x1 + curl * s * 0.03, y1 + s * 0.03, x1, y1)
        c.drawPath(end, stroke=1, fill=0)


def draw_seal(c: Canvas, x: float, y: float, side: float) -> None:
    """CIA seal as printed on the 1970s covers: a white roundel with a
    ringed legend inside a solid black square."""
    c.saveState()
    c.setFillColor(colors.black)
    c.rect(x, y, side, side, stroke=0, fill=1)
    cx, cy = x + side / 2, y + side / 2
    c.setFillColor(colors.white)
    c.circle(cx, cy, side * 0.405, stroke=0, fill=1)
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.7)
    c.circle(cx, cy, side * 0.383, stroke=1, fill=0)
    c.setFillColor(colors.black)
    _arc_text(c, "CENTRAL INTELLIGENCE AGENCY", cx, cy, side * 0.305, 90,
              218, top=True)
    _ribbon(c, cx, cy, side)
    c.setFillColor(colors.black)
    _arc_text(c, "UNITED STATES OF AMERICA", cx, cy, side * 0.333, 270,
              104, top=False)
    top = _shield(c, cx, cy, side)
    _eagle(c, cx, top + side * 0.004, side)
    c.restoreState()


def _hand_strike(c: Canvas, x0: float, y0: float, x1: float, y1: float) -> None:
    """A slightly bowed pen stroke, as drawn through 'Top Secret'."""
    c.saveState()
    c.setLineWidth(1.15)
    c.setLineCap(1)
    p = c.beginPath()
    p.moveTo(x0, y0)
    p.curveTo(x0 + (x1 - x0) * 0.35, y0 + (y1 - y0) * 0.30 + 1.2,
              x0 + (x1 - x0) * 0.70, y0 + (y1 - y0) * 0.72 + 0.8, x1, y1)
    c.drawPath(p, stroke=1, fill=0)
    c.restoreState()


def draw_cover(c: Canvas, date: str, copy_number: str,
               classification: str) -> None:
    left = 1.3 * inch
    side = 1.57 * inch
    draw_seal(c, left, S.PAGE_HEIGHT - 2.35 * inch - side, side)

    c.setFont(S.SERIF, S.COVER_TITLE_SIZE)
    c.drawString(left, S.PAGE_HEIGHT - 5.48 * inch,
                 "The President’s Daily Brief")

    right = 6.25 * inch
    c.setFont(S.SERIF_ITALIC, S.COVER_DATE_SIZE)
    c.drawRightString(right, S.PAGE_HEIGHT - 9.39 * inch, format_date(date))
    c.setFont(S.SERIF, 15)
    c.drawCentredString(right - 0.38 * inch, S.PAGE_HEIGHT - 9.79 * inch,
                        copy_number)

    label = classification_label(classification)
    target_w = 0.75 * inch
    size = target_w / stringWidth(label, S.SERIF_ITALIC, 1)
    ts_x, ts_y = right - 0.77 * inch, S.PAGE_HEIGHT - 10.02 * inch
    c.setFont(S.SERIF_ITALIC, size)
    c.drawString(ts_x, ts_y, label)
    _hand_strike(c, right - 0.97 * inch, S.PAGE_HEIGHT - 9.85 * inch,
                 right + 0.46 * inch, S.PAGE_HEIGHT - 10.20 * inch)
    draw_stamp(c, right - 0.07 * inch, ts_y + 0.05 * inch)

    # Sanitized control line: an empty ruled box, bottom left.
    c.saveState()
    c.setLineWidth(0.5)
    c.rect(1.06 * inch, S.PAGE_HEIGHT - 10.15 * inch, 3.12 * inch,
           0.28 * inch, stroke=1, fill=0)
    c.restoreState()


def draw_inside_cover(c: Canvas) -> None:
    """E.O. 11652 exemption box, small, at the top right (1975-76)."""
    w, h = 0.92 * inch, 0.38 * inch
    x, top = 7.15 * inch - w, S.PAGE_HEIGHT - 0.45 * inch
    c.saveState()
    c.setLineWidth(0.5)
    c.rect(x, top - h, w, h, stroke=1, fill=0)
    c.setFont("Times-Roman", 4.0)
    line_y = top - 0.085 * inch
    for line in _EO_BOX_LINES:
        c.drawCentredString(x + w / 2, line_y, line)
        line_y -= 0.062 * inch
    c.restoreState()


def draw_back_cover(c: Canvas, classification: str) -> None:
    c.setFont(S.SERIF_ITALIC, 14)
    c.drawString(1.15 * inch, 1.4 * inch, classification_label(classification))


def draw_annex_tab(c: Canvas) -> None:
    """Outlined A-N-N-E-X stacked down the fore-edge of the first annex page."""
    c.saveState()
    c.setLineWidth(0.45)
    size = 13
    x = S.PAGE_WIDTH - 0.95 * inch
    y = S.PAGE_HEIGHT - 1.95 * inch
    for ch in "ANNEX":
        t = c.beginText(x, y)
        t.setTextRenderMode(1)
        t.setFont("Helvetica", size)
        t.textOut(ch)
        c.drawText(t)
        y -= size * 1.45
    c.restoreState()


def draw_plate(c: Canvas, image: Path) -> None:
    """Full-page map plate scaled into the live area, centred."""
    box_w, box_h = S.PAGE_WIDTH - 1.2 * inch, S.PAGE_HEIGHT - 1.4 * inch
    reader = ImageReader(str(image))
    iw, ih = reader.getSize()
    scale = min(box_w / iw, box_h / ih)
    w, h = iw * scale, ih * scale
    c.drawImage(reader, (S.PAGE_WIDTH - w) / 2, (S.PAGE_HEIGHT - h) / 2,
                width=w, height=h)
