"""Visual constants for the CIA-style map renderer."""

# Page layout
FIG_WIDTH_IN = 8.5
FIG_HEIGHT_IN = 11.0
DPI = 200

# Colors (grayscale only, CIA reference aesthetic)
BG = "white"
SEA = "white"
LAND_OTHER = "white"
LAND_FOCUS_EDGE = "black"
COUNTRY_EDGE = "black"
LAKE_FILL = "white"
LAKE_EDGE = "black"
RIVER = "black"
FRAME = "black"
DECLASS_TEXT = "#333333"

# Line widths (points)
LW_COUNTRY = 0.38
LW_COUNTRY_FOCUS = 0.78
LW_LAKE = 0.38
LW_RIVER = 0.28
LW_RIVER_MAIN = 0.55
LW_FRAME = 1.6
LW_SCALE = 1.2
LW_COASTLINE = 0.5
LW_GRID = 0.3
GRID_COLOR = "black"

# Hatching
FOCUS_HATCH = None  # focus country rendered with slightly heavier border instead of hatch to match samples

# Fonts (tuned against CIA PDB plate typography: bold tight sans for land,
# italic serif for water, very small sans for cities and scale caps)
FONT_COUNTRY = {"family": "DejaVu Sans", "weight": "bold",
                "stretch": "condensed", "size": 10.5}
FONT_COUNTRY_FOCUS = {"family": "DejaVu Sans", "weight": "bold",
                      "stretch": "condensed", "size": 13.5}
FONT_CITY = {"family": "DejaVu Sans", "weight": "normal", "size": 6.5}
FONT_CAPITAL = {"family": "DejaVu Sans", "weight": "bold", "size": 7.5}
FONT_SEA = {"family": "DejaVu Serif", "weight": "normal",
            "style": "italic", "size": 9.5}
FONT_MARKER = {"family": "DejaVu Sans", "weight": "bold", "size": 8}
FONT_DECLASS = {"family": "DejaVu Sans", "weight": "normal", "size": 5.5}
FONT_SCALE = {"family": "DejaVu Sans", "weight": "normal",
              "size": 6.5}

# Scale bar position (axes fraction, lower-left anchor)
SCALE_ANCHOR = (0.03, 0.04)

# City rendering threshold (Natural Earth SCALERANK: 0=always, higher=less important)
CITY_MAX_SCALERANK = 6
CAPITAL_FEATURECLASS = {"Admin-0 capital", "Admin-0 capital alt"}

# Bbox padding fraction — extra room so neighbor countries and labeled
# water bodies show in the frame (CIA reference maps always include context).
BBOX_PAD = 0.35
