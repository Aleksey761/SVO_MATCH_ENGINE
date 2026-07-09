from pathlib import Path
from openpyxl import Workbook

from .models import ArrivalItem


class Reporter:
    """Writes matching results to RESULT.xlsx."""

    def write(self, items: list[ArrivalItem], output_file: str | Path) -> None:
        wb = Workbook()
        ws = wb.active
        ws.title = "RESULT"

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
