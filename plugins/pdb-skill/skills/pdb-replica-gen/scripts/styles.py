"""Fonts and page geometry for the PDB replica.

Measurements come from the 150 dpi scans of the 1975-76 booklets
(DOC_0006466841, DOC_0006015175, DOC_0006014785) and are re-centered on
a US Letter page:

- Body copy is IBM Letter Gothic at 12 pitch photo-reduced to ~9.4 pt,
  with a 9.6 pt line pitch (20 px). IBM Plex Mono stands in for it.
- Lead-ins are set with the Selectric italic element; Courier Prime
  Italic matches its true-italic letterforms.
- Cover, banners, and dates are Garamond; EB Garamond stands in.
- Right column holds 34 characters, left column 23, separated by a
  0.62 in gutter; the annex runs a single 48-character column.
"""
from __future__ import annotations

import os
from pathlib import Path

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

PAGE_WIDTH, PAGE_HEIGHT = LETTER
FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"

# ---- Typefaces ------------------------------------------------------------
TYPE = "PDB-Typewriter"
TYPE_ITALIC = "PDB-Typewriter-Italic"
SERIF = "PDB-Serif"
SERIF_ITALIC = "PDB-Serif-Italic"
SANS = "Helvetica"           # release stamps added at declassification
CN = "PDB-CN"
CN_BOLD = "PDB-CN-Bold"

_BUNDLED = {
    TYPE: "IBMPlexMono-Regular.ttf",
    TYPE_ITALIC: "CourierPrime-Italic.ttf",
    SERIF: "EBGaramond-Medium.ttf",
    SERIF_ITALIC: "EBGaramond-Italic.ttf",
}

# ---- Type sizes (points) ---------------------------------------------------
EN_SIZE = 9.4
LINE = 9.6                    # typewriter line pitch
CHAR_W = EN_SIZE * 0.6        # monospace advance
CN_SIZE = 9.0
CN_LEADING = 12.6
CN_LEADIN_SIZE = 8.6
CN_LEADIN_LEADING = 11.8
SOURCES_SIZE = 7.6
BANNER_SIZE = 12.9
DECLASS_SIZE = 7.8
STAMP_SIZE = 8.4
COVER_TITLE_SIZE = 24.3
COVER_DATE_SIZE = 12.3

# ---- Column grid -------------------------------------------------------------
_FIT = 0.5                    # slack so a full-measure line is not pushed down
LEFT_COL_CHARS = 23
RIGHT_COL_CHARS = 34
ANNEX_COL_CHARS = 48
GUTTER = 0.62 * inch
LEFT_COL_W = LEFT_COL_CHARS * CHAR_W + _FIT
RIGHT_COL_W = RIGHT_COL_CHARS * CHAR_W + _FIT
BLOCK_W = LEFT_COL_W + GUTTER + RIGHT_COL_W
BLOCK_X = (PAGE_WIDTH - BLOCK_W) / 2
RIGHT_COL_X = BLOCK_X + LEFT_COL_W + GUTTER
RIGHT_COL_END = RIGHT_COL_X + RIGHT_COL_W
ANNEX_COL_W = ANNEX_COL_CHARS * CHAR_W + _FIT
ANNEX_X = (PAGE_WIDTH - ANNEX_COL_W) / 2
HANG = 5 * CHAR_W             # Table of Contents hanging indent

# ---- Vertical placement (distances from the bottom edge unless noted) -------
FRAME_TOP = 2.0 * inch        # from the top edge
FRAME_BOTTOM = 2.05 * inch
CONTINUED_Y = 1.72 * inch
PAGE_NO_Y = 1.35 * inch
BANNER_TOP_Y = PAGE_HEIGHT - 0.62 * inch
BANNER_BOTTOM_Y = 0.30 * inch
DECLASS_TOP_Y = PAGE_HEIGHT - 0.22 * inch
DECLASS_BOTTOM_Y = 0.10 * inch

# CJK fonts: TrueType outlines only (reportlab cannot embed CFF/OTF CJK).
CJK_ENV = "PDB_CJK_FONT"
CJK_CANDIDATES = [
    ("C:/Windows/Fonts/simsun.ttc", "C:/Windows/Fonts/simhei.ttf"),
    ("C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/msyhbd.ttc"),
    ("/mnt/c/Windows/Fonts/simsun.ttc", "/mnt/c/Windows/Fonts/simhei.ttf"),
    ("/System/Library/Fonts/Supplemental/Songti.ttc",
     "/System/Library/Fonts/STHeiti Medium.ttc"),
    ("/Library/Fonts/Arial Unicode.ttf", "/Library/Fonts/Arial Unicode.ttf"),
    ("/usr/share/fonts/truetype/arphic/uming.ttc",
     "/usr/share/fonts/truetype/arphic/ukai.ttc"),
    ("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
     "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
    ("/usr/share/fonts/wqy-microhei/wqy-microhei.ttc",
     "/usr/share/fonts/wqy-microhei/wqy-microhei.ttc"),
    ("/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
     "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"),
]


def _ttfont(name: str, path: str) -> TTFont:
    kwargs = {"subfontIndex": 0} if path.lower().endswith(".ttc") else {}
    return TTFont(name, path, **kwargs)


def register_fonts() -> None:
    """Register the bundled Latin faces and the best available CJK face.

    Raises RuntimeError when a bundled font is missing or no usable CJK
    font is found (set PDB_CJK_FONT to a TrueType .ttf/.ttc to override).
    """
    for name, filename in _BUNDLED.items():
        path = FONT_DIR / filename
        if not path.exists():
            raise RuntimeError(f"bundled font missing: {path}")
        pdfmetrics.registerFont(TTFont(name, str(path)))
    pdfmetrics.registerFontFamily(TYPE, normal=TYPE, bold=TYPE,
                                  italic=TYPE_ITALIC, boldItalic=TYPE_ITALIC)
    _register_cjk()


def _register_cjk() -> None:
    override = os.environ.get(CJK_ENV)
    candidates = [(override, override)] if override else CJK_CANDIDATES
    for regular, bold in candidates:
        if not (os.path.exists(regular) and os.path.exists(bold)):
            continue
        try:
            pdfmetrics.registerFont(_ttfont(CN, regular))
            pdfmetrics.registerFont(_ttfont(CN_BOLD, bold))
        except Exception:  # noqa: BLE001 - unsupported outline format; try next
            continue
        pdfmetrics.registerFontFamily(CN, normal=CN, bold=CN_BOLD,
                                      italic=CN, boldItalic=CN_BOLD)
        return
    raise RuntimeError(
        "No TrueType CJK font found. Install SimSun, WenQuanYi Micro Hei, "
        f"or AR PL UMing, or set {CJK_ENV} to a .ttf/.ttc path.")
