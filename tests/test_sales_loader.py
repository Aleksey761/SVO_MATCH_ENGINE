from pathlib import Path

from openpyxl import Workbook

from svo.sales_loader import SalesLoader
from svo.models import ArrivalItem


def _create_document(path: Path, values: list[str | None]) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append([None, None, None, None, None, None, None, None])
    ws.append([None, "Наименование", None, "Воронеж", None, None, "Краснодар 1", "Краснодар 2"])
    for value in values:
        ws.append([None, value, None, 10, None, None, 20, 30])
    wb.save(path)
    return path


def test_sales_loader_loads_sales_rows_into_shared_model(tmp_path: Path):
    workbook = _create_document(
        tmp_path / "SALES_2026-07-15.xlsx",
        ["Sales row 1", "Sales row 2", None, "  Sales row 4  "],
    )

    rows = SalesLoader().load(workbook)

    assert rows == [
        ArrivalItem(row_number=3, source_name="Sales row 1", shipped_qty=60),
        ArrivalItem(row_number=4, source_name="Sales row 2", shipped_qty=60),
        ArrivalItem(row_number=6, source_name="Sales row 4", shipped_qty=60),
    ]


def test_sales_loader_uses_sales_contract_columns(tmp_path: Path):
    workbook = _create_document(tmp_path / "SALES_2026-07-15.xlsx", ["One"])

    rows = SalesLoader().load(workbook)

    assert rows[0].row_number == 3
    assert rows[0].source_name == "One"
    assert rows[0].shipped_qty == 60