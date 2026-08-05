from pathlib import Path

from openpyxl import Workbook

from svo.arrival_loader import ArrivalLoader
from svo.engine import Engine
from svo.revision_loader import RevisionLoader


def _create_revision_workbook(path: Path) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "REVISION"
    ws.append([
        "Наименование",
        "Остаток на складе (шт) на 20.02.2024",
        "Воронеж",
        "Краснодар 1",
        "Краснодар 2",
        "розница",
        "Екатеринбург",
        "Остаток на складе (шт) на 10.07.24",
    ])
    ws.append(["Товар A", 100, 10, 5, 3, 4, 999, 114])
    ws.append([None, 50, 1, 1, 1, 0, 123, 53])
    wb.save(path)
    return path


def _create_master_workbook(path: Path) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "MASTER"
    ws.append(["SKU", "Category", "Brand", "Variant", "Volume", "MASTER_NAME"])
    ws.append(["SKU-1", "Товар", "A", "V1", "1 шт", "Товар A"])
    wb.save(path)
    return path


def test_revision_loader_loads_rows_with_revision_quantities(tmp_path: Path):
    workbook = _create_revision_workbook(tmp_path / "REVISION 10.07.24.xlsx")

    rows = RevisionLoader().load(workbook)

    assert len(rows) == 1
    item = rows[0]
    assert item.row_number == 2
    assert item.source_name == "Товар A"
    assert item.ProductName == "Товар A"
    assert item.OpeningQty == 100
    assert item.ShippedQty == 14
    assert item.ClosingQty == 114


def test_revision_loader_interface_matches_arrival_loader(tmp_path: Path):
    workbook = _create_revision_workbook(tmp_path / "REVISION 10.07.24.xlsx")

    revision_loader = RevisionLoader()
    arrival_loader = ArrivalLoader()

    assert hasattr(revision_loader, "load")
    assert hasattr(revision_loader, "load_arrival")
    assert revision_loader.load_arrival(workbook) == revision_loader.load(workbook)
    assert arrival_loader.load(workbook)[0].source_name == revision_loader.load(workbook)[0].source_name


def test_engine_uses_revision_loader_and_preserves_revision_date_in_output_name(tmp_path: Path):
    master_file = _create_master_workbook(tmp_path / "MASTER.xlsx")
    revision_file = _create_revision_workbook(tmp_path / "REVISION 10.07.24.xlsx")

    result = Engine().run(
        master_file=master_file,
        arrival_file=revision_file,
        output_file=None,
    )

    assert result["document"] == "REVISION"
    assert Path(result["output"]).name == "RESULT 10.07.24.xlsx"
    assert Path(result["arrival_output"]).name == "REVISION_MATCH_10.07.24.xlsx"
    assert Path(result["output"]).exists()
