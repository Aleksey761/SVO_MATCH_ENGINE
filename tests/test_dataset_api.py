from pathlib import Path

from openpyxl import Workbook

from svo.dataset_api import load_master_dataset


def _create_master(path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.append(["SKU", "Category", "Brand", "Variant", "Volume"])
    ws.append(["SKU-001", "Cat", "Brand", "AromaX", "1L"])
    wb.save(path)


def test_load_master_dataset_rebuilds_if_missing(tmp_path: Path):
    data_dir = tmp_path / "data"
    output_dir = tmp_path / "output"
    data_dir.mkdir()
    output_dir.mkdir()

    _create_master(data_dir / "MASTER.xlsx")

    dataset_file = output_dir / "MASTER_DATASET.xlsx"
    records = load_master_dataset(
        dataset_file=dataset_file,
        input_dir=data_dir,
        rebuild_if_missing=True,
    )

    assert dataset_file.exists()
    assert len(records) == 1
    assert records[0].sku == "SKU-001"
