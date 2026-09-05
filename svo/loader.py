from pathlib import Path
import re
from typing import List

from openpyxl import load_workbook

from ._document_loader import load_document_rows
from .models import MasterItem, ArrivalItem


class Loader:
    """Loads MASTER and ARRIVAL Excel files."""

    @staticmethod
    def discover_master_workbook(input_dir: str | Path) -> Path:
        root = Path(input_dir)
        workbooks = [p for p in root.glob("*.xlsx") if p.is_file()]
        master_candidates = [
            p
            for p in workbooks
            if p.stem.lower().startswith("master")
        ]

        if len(master_candidates) == 0:
            raise ValueError(f"Expected at least one MASTER workbook in {root}, found 0")

        if len(master_candidates) == 1:
            return master_candidates[0]

        newest_master = max(master_candidates, key=lambda path: path.stat().st_mtime)
        print(f"Selected MASTER workbook: {newest_master}")
        return newest_master

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
        arrival_candidates = [p for p in workbooks if "arrival" in p.stem.lower()]

        if len(arrival_candidates) != 1:
            raise ValueError(f"Expected exactly one ARRIVAL workbook in {root}, found {len(arrival_candidates)}")

        master_file = self.discover_master_workbook(root)
        arrival_file = arrival_candidates[0]
        sales_candidates = [
            p
            for p in workbooks
            if p.resolve() != master_file.resolve() and p.resolve() != arrival_file.resolve()
        ]

        if len(sales_candidates) > 1:
            raise ValueError(f"Multiple SALES workbooks found in {root}: {len(sales_candidates)}")
        if require_sales and len(sales_candidates) == 0:
            raise ValueError(f"SALES workbook is missing in {root}")

        sales_file = sales_candidates[0] if sales_candidates else None
        arrival_date = self.parse_arrival_date_from_filename(arrival_file.name)
        sales_date = self.parse_arrival_date_from_filename(sales_file.name) if sales_file else None
        if arrival_date is None:
            print("WARNING:")
            print("Arrival date not found in filename.")

        return master_file, arrival_file, sales_file, arrival_date, sales_date

    def load_master(self, filename: str | Path) -> List[MasterItem]:
        source_path = Path(filename)

        # An explicitly supplied MASTER workbook is authoritative.
        # Never silently substitute a previously generated MASTER_DATASET.xlsx.
        master_path = source_path

        wb = load_workbook(filename=master_path, data_only=True)
        ws = wb.active

        items: List[MasterItem] = []

        headers = [cell.value for cell in ws[1]]
        header_to_index = {
            str(value).strip().upper(): idx
            for idx, value in enumerate(headers)
            if value is not None and str(value).strip()
        }

        sku_idx = header_to_index.get("SKU", 0)
        category_idx = header_to_index.get("CATEGORY", 1)
        brand_idx = header_to_index.get("BRAND", 2)
        variant_idx = header_to_index.get("VARIANT", 3)
        volume_idx = header_to_index.get("VOLUME", 4)
        aroma_idx = header_to_index.get("AROMA", 5)

        # MASTER_DATASET uses column J for MASTER_NAME. For a plain MASTER.xlsx
        # this column may be absent, in which case an empty master_name is used.
        master_name_idx = 9

        def value_at(row: tuple, index: int | None) -> str:
            if index is None or index >= len(row):
                return ""
            return str(row[index] or "").strip()

        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row:
                continue

            sku = value_at(row, sku_idx)
            if not sku:
                continue

            items.append(
                MasterItem(
                    sku=sku,
                    category=value_at(row, category_idx),
                    brand=value_at(row, brand_idx),
                    variant=value_at(row, variant_idx),
                    volume=value_at(row, volume_idx),
                    aroma=value_at(row, aroma_idx),
                    master_name=value_at(row, master_name_idx),
                )
            )

        return items

    def load_arrival(self, filename: str | Path) -> List[ArrivalItem]:
        return load_document_rows(filename)
