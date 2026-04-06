"""
PDF export matching the April 2026 Trauma ACS Schedule template.
"""
import calendar
from datetime import date, timedelta
from io import BytesIO
from typing import List, Dict, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
pt = 1  # 1 point = 1 reportlab unit
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus.flowables import Flowable

from .models import DaySchedule

# ── Colours ─────────────────────────────────────────────────────────────────
GRAY_LIGHT   = colors.HexColor("#D9D9D9")
GRAY_HEADER  = colors.HexColor("#404040")
WHITE        = colors.white
BLACK        = colors.black

# ── Meeting schedule ─────────────────────────────────────────────────────────
# dow: 0=Mon … 6=Sun
WEEKLY_MEETINGS = {
    2: "UH Gr Rds, M&M",   # Wednesday
    3: "Tr M&M, Teaching",  # Thursday
}
SECOND_MONDAY_LABEL = "Tr Div & MultiD"

FOOTER = (
    "Day shift 7a to 530p, Night shift 530p to 7a; "
    "Non-Trauma/ACS QUMG surgery covers Wednesday General Surgery call. "
    "630a sign-out on Wed."
)


class RotatedText(Flowable):
    """Draws text rotated 90° CCW — used for Block 1 / Block 2 cells."""
    def __init__(self, text, font="Helvetica", size=7, width=14, height=60):
        Flowable.__init__(self)
        self.text  = text
        self.font  = font
        self.size  = size
        self.width  = width
        self.height = height

    def draw(self):
        canvas = self.canv
        canvas.saveState()
        canvas.setFont(self.font, self.size)
        canvas.translate(self.width / 2, self.height / 2)
        canvas.rotate(90)
        canvas.drawCentredString(0, -self.size / 3, self.text)
        canvas.restoreState()

    def wrap(self, availWidth, availHeight):
        return self.width, self.height


def _name(sid: Optional[str], surgeon_names: Dict[str, str]) -> str:
    if not sid or sid == "TBD":
        return sid or ""
    return surgeon_names.get(sid, sid)


def _is_second_monday(d: date) -> bool:
    """True if d is the second Monday of its month."""
    if d.weekday() != 0:
        return False
    # Count how many Mondays have occurred so far in the month (including d)
    monday_count = sum(
        1 for day in range(1, d.day + 1)
        if date(d.year, d.month, day).weekday() == 0
    )
    return monday_count == 2


def _meeting_label(d: date, start: date) -> str:
    if d.weekday() in WEEKLY_MEETINGS:
        return WEEKLY_MEETINGS[d.weekday()]
    if _is_second_monday(d):
        return SECOND_MONDAY_LABEL
    return ""


def generate_pdf(
    month_schedule: List[DaySchedule],
    surgeon_names: Dict[str, str],
    month_label: str,      # e.g. "April 2026"
    schedule_start: date,  # first day of full schedule (for biweekly calc)
) -> bytes:
    """Return PDF bytes for one month's schedule."""

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(letter),
        leftMargin=0.4*inch,
        rightMargin=0.4*inch,
        topMargin=0.35*inch,
        bottomMargin=0.35*inch,
    )

    # ── Styles ───────────────────────────────────────────────────────────────
    title_style = ParagraphStyle(
        "title", fontName="Helvetica-Bold", fontSize=10, leading=14,
        spaceAfter=4, alignment=TA_LEFT,
    )
    cell_style = ParagraphStyle(
        "cell", fontName="Helvetica", fontSize=7, leading=9, alignment=TA_CENTER,
    )
    cell_bold = ParagraphStyle(
        "cell_bold", fontName="Helvetica-Bold", fontSize=7, leading=9, alignment=TA_CENTER,
    )
    note_style = ParagraphStyle(
        "note", fontName="Helvetica", fontSize=6.5, leading=8, alignment=TA_LEFT,
    )
    header_style = ParagraphStyle(
        "hdr", fontName="Helvetica-Bold", fontSize=7, leading=9,
        textColor=WHITE, alignment=TA_CENTER,
    )
    footer_style = ParagraphStyle(
        "footer", fontName="Helvetica", fontSize=6.5, leading=8, alignment=TA_LEFT,
    )

    def P(text, bold=False):
        return Paragraph(text, cell_bold if bold else cell_style)

    def H(text):
        return Paragraph(text, header_style)

    # ── Column widths (landscape letter = 11 × 8.5 in, usable ~10.2 in) ────
    # Notes | Day | Date | TrEGS | Office | Blk1 | Blk2 | ICU | TrN | EGS/ICU N | Tr D b/u | Tr N b/u
    CW = [
        1.05*inch,   # Notes
        0.28*inch,   # Day
        0.55*inch,   # Date
        0.65*inch,   # TrEGS Day
        0.60*inch,   # Office
        0.20*inch,   # Block 1
        0.20*inch,   # Block 2
        0.65*inch,   # ICU Day
        0.70*inch,   # Tr/EGS/SICU N  (TrN + EGS/ICU N merged)
        0.65*inch,   # EGS/ICU N (same person — shown blank or same)
        0.65*inch,   # Tr D b/u
        0.65*inch,   # Tr N b/u
    ]

    # ── Build rows ───────────────────────────────────────────────────────────
    header_row = [
        H(""), H(""), H(""),
        H("TrEGS Day"), H("Office"),
        H("1"), H("2"),
        H("ICU Day"),
        H("TrN"), H("EGS/ICU N"),
        H("Tr D b/u"), H("Tr N b/u"),
    ]

    rows = [header_row]
    style_cmds = [
        # Header
        ("BACKGROUND",  (0, 0), (-1, 0), GRAY_HEADER),
        ("TEXTCOLOR",   (0, 0), (-1, 0), WHITE),
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, 0), 7),
        ("ALIGN",       (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("GRID",        (0, 0), (-1, -1), 0.4, colors.HexColor("#AAAAAA")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, colors.HexColor("#F7F7F7")]),
        ("LEFTPADDING",  (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING",   (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 2),
    ]

    # Group days by week (Mon-Sun)
    sched_map: Dict[str, DaySchedule] = {d.date: d for d in month_schedule}
    day_list   = sorted(month_schedule, key=lambda x: x.date)

    # Collect block week groups so we can span Block 1/2 columns
    # A "block week" = Mon to Sun sharing same block1/block2
    week_spans: Dict[str, tuple] = {}   # date_iso -> (block1, block2, span_start_row, span_len)
    # We'll compute row spans after building rows

    block_col_rows: Dict[int, dict] = {}  # row_index -> {block1, block2, is_first}

    row_idx = 1  # after header
    first_row_of_week: Dict[str, int] = {}   # week_mon_iso -> row_idx of first row in that week
    week_of_row: Dict[int, str] = {}          # row_idx -> week_mon_iso

    for ds_obj in day_list:
        d     = date.fromisoformat(ds_obj.date)
        dow   = d.weekday()
        wmon  = (d - timedelta(days=dow)).isoformat()

        meeting = _meeting_label(d, schedule_start)
        date_str = f"{d.month}/{d.day}/{d.year}"
        day_str  = d.strftime("%a")

        n = lambda sid: P(_name(sid, surgeon_names))

        tr_night_name = _name(ds_obj.tr_egs_sicu_night, surgeon_names)

        row = [
            Paragraph(meeting, note_style),
            P(day_str),
            P(date_str),
            n(ds_obj.tregs_day),
            n(ds_obj.tregs_day_office),
            "",   # Block 1 placeholder
            "",   # Block 2 placeholder
            n(ds_obj.icu_day),
            P(tr_night_name),
            P(tr_night_name),
            n(ds_obj.tr_day_backup),
            n(ds_obj.tr_night_backup),
        ]
        rows.append(row)

        if wmon not in first_row_of_week:
            first_row_of_week[wmon] = row_idx
        week_of_row[row_idx] = wmon

        block_col_rows[row_idx] = {
            "block1": _name(ds_obj.block1, surgeon_names),
            "block2": _name(ds_obj.block2, surgeon_names),
            "is_first": (wmon not in first_row_of_week or first_row_of_week[wmon] == row_idx),
            "wmon": wmon,
        }
        row_idx += 1

    # ── Compute row spans for Block 1 / Block 2 columns ─────────────────────
    # Group consecutive rows with same wmon
    week_row_ranges: Dict[str, list] = {}
    for ri, info in block_col_rows.items():
        wmon = info["wmon"]
        if wmon not in week_row_ranges:
            week_row_ranges[wmon] = []
        week_row_ranges[wmon].append(ri)

    for wmon, row_indices in week_row_ranges.items():
        row_indices.sort()
        start_ri = row_indices[0]
        span     = len(row_indices)
        b1 = block_col_rows[start_ri]["block1"]
        b2 = block_col_rows[start_ri]["block2"]

        if span > 1:
            # Merge Block1 col (index 5) and Block2 col (index 6)
            style_cmds.append(("SPAN", (5, start_ri), (5, start_ri + span - 1)))
            style_cmds.append(("SPAN", (6, start_ri), (6, start_ri + span - 1)))

        # Insert rotated text into first row of the span
        rows[start_ri][5] = RotatedText(b1, width=CW[5]/pt, height=span * 18)
        rows[start_ri][6] = RotatedText(b2, width=CW[6]/pt, height=span * 18)

        # Clear other rows in span
        for ri in row_indices[1:]:
            rows[ri][5] = ""
            rows[ri][6] = ""

        # Gray background for Block cols
        style_cmds.append(("BACKGROUND", (5, start_ri), (5, start_ri + span - 1), GRAY_LIGHT))
        style_cmds.append(("BACKGROUND", (6, start_ri), (6, start_ri + span - 1), GRAY_LIGHT))

    # ── Row heights ──────────────────────────────────────────────────────────
    row_heights = [16] + [14] * (len(rows) - 1)

    # ── Assemble table ───────────────────────────────────────────────────────
    table = Table(rows, colWidths=CW, rowHeights=row_heights, repeatRows=1)
    table.setStyle(TableStyle(style_cmds))

    # ── Build document ───────────────────────────────────────────────────────
    story = [
        Paragraph(f"{month_label} Trauma ACS Schedule", title_style),
        table,
        Spacer(1, 4),
        Paragraph(FOOTER, footer_style),
    ]
    doc.build(story)
    return buf.getvalue()
