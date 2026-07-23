from pathlib import Path
from openpyxl import Workbook
from openpyxl import load_workbook

from .models import ArrivalItem


class Reporter:
    """Writes matching results to RESULT.xlsx."""

    def write(
        self,
        items: list[ArrivalItem],
        output_file: str | Path,
        arrival_date: str | None = None,
    ) -> None:
        wb = Workbook()
        ws = wb.active
        ws.title = "RESULT"

        ws.append(["REPORT", "SVO Match Engine"])
        ws.append(["ARRIVAL_DATE", arrival_date if arrival_date is not None else ""])
        ws.append(["METADATA", f"arrival_date={arrival_date}"])
        ws.append([])

        ws.append([
            "SOURCE_NAME",
            "CATEGORY",
            "BRAND",
            "VARIANT",
            "VOLUME",
            "SKU",
            "MASTER_NAME",
            "STATUS",
        ])

        for item in items:
            ws.append([
                item.source_name,
                item.category,
                item.brand,
                item.variant,
                item.volume,
                item.sku,
                item.master_name,
                item.status,
            ])

        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        wb.save(output_file)

    def write_matched_arrival(
        self,
        source_arrival_file: str | Path,
        items: list[ArrivalItem],
        output_file: str | Path,
    ) -> None:
        """Clones ARRIVAL workbook and appends match result columns."""
        wb = load_workbook(filename=source_arrival_file, data_only=False)
        ws = wb.active

        start_col = ws.max_column + 1
        headers = [
            "MATCH_STATUS",
            "MATCH_SKU",
            "MATCH_MASTER_NAME",
            "MATCH_CONFIDENCE",
            "MATCH_REASONS",
        ]

        for offset, header in enumerate(headers):
            ws.cell(row=1, column=start_col + offset, value=header)

        items_by_row = {item.row_number: item for item in items}
        max_row = ws.max_row

        for row_number in range(2, max_row + 1):
            item = items_by_row.get(row_number)
            if item is None:
                continue

            reasons = ",".join(item.review_reasons) if item.review_reasons else ""
            ws.cell(row=row_number, column=start_col + 0, value=item.status)
            ws.cell(row=row_number, column=start_col + 1, value=item.sku or "")
            ws.cell(row=row_number, column=start_col + 2, value=item.master_name or "")
            ws.cell(row=row_number, column=start_col + 3, value=item.confidence)
            ws.cell(row=row_number, column=start_col + 4, value=reasons)

        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        wb.save(output_file)
