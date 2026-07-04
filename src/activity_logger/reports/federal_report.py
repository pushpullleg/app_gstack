"""Federal-style quarterly activity report PDF generator.

Pure function — no Qt, no database. Everything arrives in ReportData.
User-entered text is XML-escaped before any Platypus Paragraph.
"""

from __future__ import annotations

import xml.sax.saxutils as saxutils
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from activity_logger.models.entities import ReportData
from activity_logger.reports.styles import (
    BOLD_RIGHT_STYLE,
    BOLD_STYLE,
    CELL_RIGHT_STYLE,
    CELL_STYLE,
    CERT_STYLE,
    CONTENT_WIDTH,
    FOOTER_RIGHT_STYLE,
    FOOTER_STYLE,
    LABEL_STYLE,
    MARGIN,
    RULE_COLOR,
    SUBTITLE_STYLE,
    TABLE_HEADER_BG,
    TITLE_STYLE,
)


def _esc(text: str) -> str:
    """XML-escape user-provided text for safe use inside Platypus Paragraphs."""
    return saxutils.escape(str(text))


def build_report(data: ReportData, out_path: Path) -> None:
    """Render a federal quarterly activity report PDF to out_path."""
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # ── Page template with footer callback ────────────────────────────────────
    def _footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        left_text = f"Generated {data.generation_timestamp}"
        right_text = f"Page {doc.page}"
        canvas.drawString(MARGIN, 0.5 * inch, left_text)
        canvas.drawRightString(8.5 * inch - MARGIN, 0.5 * inch, right_text)
        canvas.restoreState()

    frame = Frame(MARGIN, MARGIN, CONTENT_WIDTH, 11 * inch - 2 * MARGIN, id="main")
    template = PageTemplate(id="federal", frames=[frame], onPage=_footer)
    doc = BaseDocTemplate(
        str(out_path),
        pagesize=LETTER,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
    )
    doc.addPageTemplates([template])

    story = []

    # ── Header ────────────────────────────────────────────────────────────────
    story.append(Paragraph(_esc(data.org_name), TITLE_STYLE))
    story.append(Paragraph(f"QUARTERLY ACTIVITY REPORT — {_esc(data.quarter_label)}", SUBTITLE_STYLE))
    story.append(Spacer(1, 6))

    # Horizontal rule
    rule_table = Table([[""]],  colWidths=[CONTENT_WIDTH])
    rule_table.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.75, RULE_COLOR)]))
    story.append(rule_table)
    story.append(Spacer(1, 8))

    # Employee info row
    emp_data = [
        [
            Paragraph(f"<b>Name:</b> {_esc(data.employee_name)}", LABEL_STYLE),
            Paragraph(f"<b>UIN:</b> {_esc(data.employee_uin)}", LABEL_STYLE),
            Paragraph(f"<b>Dept:</b> {_esc(data.department_code)}", LABEL_STYLE),
        ]
    ]
    emp_table = Table(emp_data, colWidths=[CONTENT_WIDTH * 0.45, CONTENT_WIDTH * 0.25, CONTENT_WIDTH * 0.30])
    emp_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(emp_table)
    story.append(Spacer(1, 4))

    period_str = f"{data.period_start.strftime('%B %d, %Y')} – {data.period_end.strftime('%B %d, %Y')}"
    story.append(Paragraph(f"<b>Reporting Period:</b> {period_str}", LABEL_STYLE))
    story.append(Spacer(1, 8))

    # Second horizontal rule
    story.append(rule_table)
    story.append(Spacer(1, 12))

    # ── Activity table ────────────────────────────────────────────────────────
    COL_CODE = CONTENT_WIDTH * 0.18
    COL_DESC = CONTENT_WIDTH * 0.62
    COL_HRS = CONTENT_WIDTH * 0.20

    table_header = [
        Paragraph("<b>ACTIVITY CODE</b>", BOLD_STYLE),
        Paragraph("<b>DESCRIPTION</b>", BOLD_STYLE),
        Paragraph("<b>TOTAL HRS</b>", BOLD_RIGHT_STYLE),
    ]
    table_rows = [table_header]

    for row in data.rows:
        table_rows.append([
            Paragraph(_esc(row.code), CELL_STYLE),
            Paragraph(_esc(row.description), CELL_STYLE),
            Paragraph(f"{row.hours:.2f}", CELL_RIGHT_STYLE),
        ])

    # Grand total row
    table_rows.append([
        Paragraph("", BOLD_STYLE),
        Paragraph("<b>GRAND TOTAL</b>", BOLD_STYLE),
        Paragraph(f"<b>{data.grand_total:.2f}</b>", BOLD_RIGHT_STYLE),
    ])

    act_table = Table(table_rows, colWidths=[COL_CODE, COL_DESC, COL_HRS], repeatRows=1)
    act_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TABLE_HEADER_BG),
        ("GRID", (0, 0), (-1, -2), 0.5, colors.HexColor("#cccccc")),
        ("LINEABOVE", (0, -1), (-1, -1), 1.0, RULE_COLOR),
        ("LINEBELOW", (0, -1), (-1, -1), 1.0, RULE_COLOR),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(act_table)
    story.append(Spacer(1, 24))

    # ── Certification block ───────────────────────────────────────────────────
    story.append(Paragraph("<b>CERTIFICATION</b>", BOLD_STYLE))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "I certify that the above is a true and accurate record of activities performed "
        "during the reporting period indicated.",
        CERT_STYLE,
    ))
    story.append(Spacer(1, 16))

    # Signature table — ruled lines, never underscores (rules stay aligned).
    def _sig_row(label: str, typed_info: str = "") -> list:
        return [
            Paragraph(f"<b>{label}:</b>", LABEL_STYLE),
            "",          # signature line (ruled via table style)
            Paragraph(typed_info, CELL_STYLE) if typed_info else "",
            "",          # date line
        ]

    emp_typed = f"{_esc(data.employee_name)} ({_esc(data.employee_uin)})"
    sig_data = [
        _sig_row("Employee", emp_typed),
        [Spacer(1, 4), "", "", ""],
        _sig_row("Supervisor"),
        [Spacer(1, 4), "", "", ""],
        _sig_row("Director"),
    ]
    sig_col_widths = [
        CONTENT_WIDTH * 0.14,  # label
        CONTENT_WIDTH * 0.44,  # signature
        CONTENT_WIDTH * 0.20,  # typed info
        CONTENT_WIDTH * 0.22,  # date
    ]
    sig_table = Table(sig_data, colWidths=sig_col_widths)
    sig_table.setStyle(TableStyle([
        # Signature lines for rows 0, 2, 4 (employee, supervisor, director)
        ("LINEBELOW", (1, 0), (1, 0), 0.75, colors.black),
        ("LINEBELOW", (3, 0), (3, 0), 0.75, colors.black),
        ("LINEBELOW", (1, 2), (1, 2), 0.75, colors.black),
        ("LINEBELOW", (3, 2), (3, 2), 0.75, colors.black),
        ("LINEBELOW", (1, 4), (1, 4), 0.75, colors.black),
        ("LINEBELOW", (3, 4), (3, 4), 0.75, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(sig_table)

    doc.build(story)
