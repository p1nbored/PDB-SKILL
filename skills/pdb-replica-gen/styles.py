"""Fonts, colors, margins for the PDB replica."""
from __future__ import annotations

import os
from pathlib import Path

from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

PAGE_WIDTH = 8.5 * inch
PAGE_HEIGHT = 11.0 * inch
LEFT_MARGIN = 1.0 * inch
RIGHT_MARGIN = 1.0 * inch
TOP_MARGIN = 1.0 * inch
BOTTOM_MARGIN = 0.9 * inch

# Font family names used in the PDF.
# Typography mapping derived from the 1971-76 reference PDBs:
#   serif roman/italic (Garamond-class)  -> Times-Roman / Times-Italic
#   typewriter roman/italic (Courier)    -> Courier / Courier-Oblique
#   square gothic display heads          -> Courier-Bold (closest built-in)
#   modern sans release stamps (artifact)-> Helvetica
BODY_EN = "Courier"
BODY_EN_BOLD = "Courier-Bold"
BODY_EN_ITALIC = "Courier-Oblique"
BODY_CN = "PDB-CN"
BODY_CN_BOLD = "PDB-CN-Bold"
SERIF = "Times-Roman"
SERIF_ITALIC = "Times-Italic"
DISPLAY = "Courier-Bold"

BODY_SIZE = 10.5
BODY_LEADING = 13.5
DISPLAY_SIZE = 14
COVER_TITLE_SIZE = 30
COVER_DATE_SIZE = 15
FOOTER_SIZE = 8
BANNER_SIZE = 12.5
DECLASS_SIZE = 7
STAMP_SIZE = 7.5

CJK_CANDIDATES = [
    ("C:/Windows/Fonts/simsun.ttc", "C:/Windows/Fonts/simhei.ttf"),
    ("C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/msyhbd.ttc"),
    ("/mnt/c/Windows/Fonts/simsun.ttc", "/mnt/c/Windows/Fonts/simhei.ttf"),
    ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
     "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
    ("/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
     "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc"),
    ("/mnt/c/Windows/Fonts/NotoSansSC-VF.ttf",
     "/mnt/c/Windows/Fonts/NotoSansSC-VF.ttf"),
]


def register_cjk_fonts() -> tuple[str, str]:
    """Register the best available CJK fonts and return (regular, bold) names."""
    for regular, bold in CJK_CANDIDATES:
        if os.path.exists(regular) and os.path.exists(bold):
            try:
                # reportlab needs a subfontIndex for .ttc
                reg_kwargs = {"subfontIndex": 0} if regular.endswith(".ttc") else {}
                bold_kwargs = {"subfontIndex": 0} if bold.endswith(".ttc") else {}
                pdfmetrics.registerFont(TTFont(BODY_CN, regular, **reg_kwargs))
                pdfmetrics.registerFont(TTFont(BODY_CN_BOLD, bold, **bold_kwargs))
                return BODY_CN, BODY_CN_BOLD
            except Exception:  # noqa: BLE001
                continue
    raise RuntimeError(
        "No CJK font found. Install Noto Sans CJK or make SimSun available."
    )
