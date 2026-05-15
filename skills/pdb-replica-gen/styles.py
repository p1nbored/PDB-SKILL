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

# Font family names used in the PDF
BODY_EN = "Courier"
BODY_EN_BOLD = "Courier-Bold"
BODY_CN = "PDB-CN"
BODY_CN_BOLD = "PDB-CN-Bold"
TITLE_FONT = "Helvetica-Bold"

BODY_SIZE = 10.5
BODY_LEADING = 13.5
TITLE_SIZE = 11.5
COVER_TITLE_SIZE = 28
COVER_DATE_SIZE = 12
FOOTER_SIZE = 8
BANNER_SIZE = 8
COMPARTMENT_SIZE = 7.5

CJK_CANDIDATES = [
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
