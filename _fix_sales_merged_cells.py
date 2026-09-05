from pathlib import Path

p = Path("svo/reporter.py")
s = p.read_text(encoding="utf-8")

# 1. Import MergedCell
old_import = "from openpyxl import load_workbook\n"
new_import = "from openpyxl import load_workbook\nfrom openpyxl.cell.cell import MergedCell\n"

if "from openpyxl.cell.cell import MergedCell" not in s:
    if old_import not in s:
        raise SystemExit("OPENPYXL IMPORT NOT FOUND")
    s = s.replace(old_import, new_import, 1)

# 2. Add safe cell writer
needle = '''    @staticmethod
    def _normalize_header(value: object) -> str:
        return str(value or "").strip().upper()

'''

helper = '''    @staticmethod
    def _normalize_header(value: object) -> str:
        return str(value or "").strip().upper()

    @staticmethod
    def _set_cell_value(ws, row: int, column: int, value: object) -> bool:
        cell = ws.cell(row=row, column=column)
        if isinstance(cell, MergedCell):
            return False
        cell.value = value
        return True

'''

if "_set_cell_value(" not in s:
    if needle not in s:
        raise SystemExit("NORMALIZE HEADER BLOCK NOT FOUND")
    s = s.replace(needle, helper, 1)

# 3. Replace direct assignments used by the SALES finalizer.
replacements = {
    'ws.cell(row=1, column=col, value=title)':
        'self._set_cell_value(ws, 1, col, title)',
    'ws.cell(row=stale_row, column=col).value = None':
        'self._set_cell_value(ws, stale_row, col, None)',
    'ws.cell(row=target_row, column=col).value = value':
        'self._set_cell_value(ws, target_row, col, value)',
    'ws.cell(row=row, column=col, value=None)':
        'self._set_cell_value(ws, row, col, None)',
}

for old, new in replacements.items():
    s = s.replace(old, new)

# 4. The appended MATCH columns also go through the safe writer.
for old, new in {
    'ws.cell(row=1, column=start_col + offset, value=header)':
        'self._set_cell_value(ws, 1, start_col + offset, header)',
    'ws.cell(row=row_number, column=start_col + 0, value=item.status)':
        'self._set_cell_value(ws, row_number, start_col + 0, item.status)',
    'ws.cell(row=row_number, column=start_col + 1, value=item.sku or "")':
        'self._set_cell_value(ws, row_number, start_col + 1, item.sku or "")',
    'ws.cell(row=row_number, column=start_col + 2, value=item.master_name or "")':
        'self._set_cell_value(ws, row_number, start_col + 2, item.master_name or "")',
    'ws.cell(row=row_number, column=start_col + 3, value=item.confidence)':
        'self._set_cell_value(ws, row_number, start_col + 3, item.confidence)',
    'ws.cell(row=row_number, column=start_col + 4, value=reasons)':
        'self._set_cell_value(ws, row_number, start_col + 4, reasons)',
}.items():
    s = s.replace(old, new)

p.write_text(s, encoding="utf-8")
print("SALES MERGED-CELL FIX APPLIED")
