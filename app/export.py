import os
from datetime import datetime

EXPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "exports")


def export_table(headers, rows, prefix="export"):
    """Export a table to an .xlsx file and open it.

    headers: list of column titles.
    rows: list of rows (each row is a list/tuple of cell values).
    Returns the file path or None on failure.
    """
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment
        from openpyxl.utils import get_column_letter
    except ImportError:
        return None

    os.makedirs(EXPORTS_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(EXPORTS_DIR, f"{prefix}_{stamp}.xlsx")

    wb = Workbook()
    ws = wb.active
    ws.title = prefix

    # header
    header_fill = PatternFill("solid", fgColor="0F172A")
    header_font = Font(bold=True, color="FFFFFF")
    for c, title in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=c, value=str(title))
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # data
    for r, row in enumerate(rows, start=2):
        for c, value in enumerate(row, start=1):
            if value is None:
                value = ""
            ws.cell(row=r, column=c, value=value)

    # auto width (best effort, cap at 40)
    for c in range(1, len(headers) + 1):
        width = max(len(str(headers[c - 1])), 8)
        for r in range(2, min(ws.max_row + 1, 200)):
            v = ws.cell(row=r, column=c).value
            if v is not None:
                width = max(width, min(len(str(v)), 40))
        ws.column_dimensions[get_column_letter(c)].width = width + 2

    wb.save(path)
    return path
