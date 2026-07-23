from pathlib import Path

from openpyxl import Workbook

from svo.arrival_loader import ArrivalLoader
from svo.sales_loader import SalesLoader
from svo.models import ArrivalItem


def _create_document(path: Path, values: list[str | None]) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(["NAME"])
    for value in values:
        ws.append([value])
    wb.save(path)
    return path


def test_sales_loader_loads_rows_into_shared_model(tmp_path: Path):
    workbook = _create_document(
        tmp_path / "SALES_2026-07-15.xlsx",
        ["Sales row 1", "Sales row 2", None, "  Sales row 4  "],
    )

    rows = SalesLoader().load(workbook)

    assert rows == [
        ArrivalItem(row_number=2, source_name="Sales row 1"),
        ArrivalItem(row_number=3, source_name="Sales row 2"),
        ArrivalItem(row_number=5, source_name="Sales row 4"),
    ]


def test_sales_loader_interface_matches_arrival_loader(tmp_path: Path):
    workbook = _create_document(tmp_path / "SALES_2026-07-15.xlsx", ["One"])

    sales_loader = SalesLoader()
    arrival_loader = ArrivalLoader()

    assert sales_loader.load(workbook) == arrival_loader.load(workbook)
    assert sales_loader.load_sales(workbook) == arrival_loader.load(workbook)
    assert sales_loader.load_arrival(workbook) == arrival_loader.load(workbook)