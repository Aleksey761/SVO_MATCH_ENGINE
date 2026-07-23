from pathlib import Path
import re
from typing import List

from openpyxl import load_workbook

from .models import MasterItem, ArrivalItem


class Loader:
    """Loads MASTER and ARRIVAL Excel files."""

    @staticmethod
    def parse_arrival_date_from_filename(filename: str | Path) -> str | None:
        stem = Path(filename).stem

        # DD.MM.YY or DD.MM.YYYY
        m = re.search(r"(?<!\d)(\d{2})\.(\d{2})\.(\d{2}|\d{4})(?!\d)", stem)
        if m:
            day, month, year = m.group(1), m.group(2), m.group(3)
            if len(year) == 2:
                year = f"20{year}"
            return f"{day}.{month}.{year}"

        # YYYY-MM-DD
        m = re.search(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)", stem)
        if m:
            year, month, day = m.group(1), m.group(2), m.group(3)
            return f"{day}.{month}.{year}"

        # YYYY_MM_DD
        m = re.search(r"(?<!\d)(\d{4})_(\d{2})_(\d{2})(?!\d)", stem)
        if m:
            year, month, day = m.group(1), m.group(2), m.group(3)
            return f"{day}.{month}.{year}"

        return None

    def discover_workbooks(
        self,
        input_dir: str | Path,
        require_sales: bool = False,
    ) -> tuple[Path, Path, Path | None, str | None, str | None]:
        root = Path(input_dir)
        workbooks = [p for p in root.glob("*.xlsx") if p.is_file()]

        master_candidates = [p for p in workbooks if "master" in p.stem.lower()]
        arrival_candidates = [p for p in workbooks if "arrival" in p.stem.lower()]
        sales_candidates = [p for p in workbooks if "sales" in p.stem.lower()]

        if len(master_candidates) != 1:
            raise ValueError(f"Expected exactly one MASTER workbook in {root}, found {len(master_candidates)}")
        if len(arrival_candidates) != 1:
            raise ValueError(f"Expected exactly one ARRIVAL workbook in {root}, found {len(arrival_candidates)}")
        if len(sales_candidates) > 1:
            raise ValueError(f"Multiple SALES workbooks found in {root}: {len(sales_candidates)}")
        if require_sales and len(sales_candidates) == 0:
            raise ValueError(f"SALES workbook is missing in {root}")

        master_file = master_candidates[0]
        arrival_file = arrival_candidates[0]
        sales_file = sales_candidates[0] if sales_candidates else None
        arrival_date = self.parse_arrival_date_from_filename(arrival_file.name)
        sales_date = self.parse_arrival_date_from_filename(sales_file.name) if sales_file else None
        if arrival_date is None:
            print("WARNING:")
            print("Arrival date not found in filename.")

        return master_file, arrival_file, sales_file, arrival_date, sales_date

    def load_master(self, filename: str | Path) -> List[MasterItem]:
        wb = load_workbook(filename=filename, data_only=True)
        ws = wb.active

        items: List[MasterItem] = []

        # Expected columns:
        # A=SKU B=Category C=Brand D=Variant E=Volume
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row or not row[0]:
                continue

            items.append(
                MasterItem(
                    sku=str(row[0]).strip(),
                    category=str(row[1] or "").strip(),
                    brand=str(row[2] or "").strip(),
                    variant=str(row[3] or "").strip(),
                    volume=str(row[4] or "").strip(),
                )
            )

        return items

    def load_arrival(self, filename: str | Path) -> List[ArrivalItem]:
        wb = load_workbook(filename=filename, data_only=True)
        ws = wb.active

        items: List[ArrivalItem] = []

        # Column A = НАИМЕНОВАНИЕ
        for excel_row, row in enumerate(
            ws.iter_rows(min_row=2, values_only=True),
            start=2,
        ):
            name = row[0]

            if name is None:
                continue

            text = str(name).strip()

            if not text:
                continue

            items.append(
                ArrivalItem(
                    row_number=excel_row,
                    source_name=text,
                )
            )

        return items
