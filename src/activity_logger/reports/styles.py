"""ReportLab style constants — Base-14 fonts only, no embedding."""

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch

# Page geometry
PAGE_WIDTH = 8.5 * inch
PAGE_HEIGHT = 11 * inch
MARGIN = 1.0 * inch
CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN

# Colours
HEADER_BG = colors.HexColor("#2b4c7e")
HEADER_FG = colors.white
TABLE_HEADER_BG = colors.HexColor("#e4e8ee")
RULE_COLOR = colors.HexColor("#aaaaaa")

# Base styles
_base = getSampleStyleSheet()

TITLE_STYLE = ParagraphStyle(
    "title",
    fontName="Times-Bold",
    fontSize=14,
    leading=18,
    alignment=TA_CENTER,
    spaceAfter=4,
)

SUBTITLE_STYLE = ParagraphStyle(
    "subtitle",
    fontName="Times-Bold",
    fontSize=11,
    leading=14,
    alignment=TA_CENTER,
    spaceAfter=2,
)

LABEL_STYLE = ParagraphStyle(
    "label",
    fontName="Helvetica",
    fontSize=9,
    leading=12,
    alignment=TA_LEFT,
)

CELL_STYLE = ParagraphStyle(
    "cell",
    fontName="Helvetica",
    fontSize=9,
    leading=12,
    alignment=TA_LEFT,
)

CELL_RIGHT_STYLE = ParagraphStyle(
    "cell_right",
    fontName="Helvetica",
    fontSize=9,
    leading=12,
    alignment=TA_RIGHT,
)

BOLD_STYLE = ParagraphStyle(
    "bold",
    fontName="Helvetica-Bold",
    fontSize=9,
    leading=12,
    alignment=TA_LEFT,
)

BOLD_RIGHT_STYLE = ParagraphStyle(
    "bold_right",
    fontName="Helvetica-Bold",
    fontSize=9,
    leading=12,
    alignment=TA_RIGHT,
)

CERT_STYLE = ParagraphStyle(
    "cert",
    fontName="Times-Italic",
    fontSize=9,
    leading=12,
    alignment=TA_LEFT,
    spaceAfter=6,
)

FOOTER_STYLE = ParagraphStyle(
    "footer",
    fontName="Helvetica",
    fontSize=8,
    leading=10,
    alignment=TA_LEFT,
)

FOOTER_RIGHT_STYLE = ParagraphStyle(
    "footer_right",
    fontName="Helvetica",
    fontSize=8,
    leading=10,
    alignment=TA_RIGHT,
)
