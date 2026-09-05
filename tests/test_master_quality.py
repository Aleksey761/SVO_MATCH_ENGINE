from pathlib import Path

import pytest
from openpyxl import Workbook

from svo.engine import Engine


def _create_master(path: Path, rows: list[list[object]]) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "MASTER"
    ws.append(["SKU", "CATEGORY", "BRAND", "VARIANT", "VOLUME", "MASTER_NAME"])
    for row in rows:
        ws.append(row)
    wb.save(path)
    return path


def _create_arrival(path: Path) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "ARRIVAL"
    ws.append(["SOURCE_NAME"])
    ws.append(["Test product"])
    wb.save(path)
    return path


def test_engine_stops_when_master_quality_fails(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    master = _create_master(
        tmp_path / "MASTER.xlsx",
        [
            ["SKU-1", "C1", "B1", "V1", "1L", "Name 1"],
            ["SKU-1", "C2", "B2", "V2", "2L", "Name 2"],
        ],
    )
    arrival = _create_arrival(tmp_path / "ARRIVAL.xlsx")

    with pytest.raises(RuntimeError) as exc:
        Engine().run(master_file=master, arrival_file=arrival, output_file=tmp_path / "RESULT.xlsx")

    assert "MASTER AUDIT FAILED" in str(exc.value)
    assert "See output/MASTER_AUDIT.txt" in str(exc.value)
    assert (tmp_path / "output" / "MASTER_AUDIT.txt").exists()


def test_engine_continues_when_master_quality_passes(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    master = _create_master(
        tmp_path / "MASTER.xlsx",
        [
            ["SKU-1", "C1", "B1", "V1", "1L", "Name 1"],
            ["SKU-2", "C2", "B2", "V2", "2L", "Name 2"],
        ],
    )
    arrival = _create_arrival(tmp_path / "ARRIVAL.xlsx")

    result = Engine().run(master_file=master, arrival_file=arrival, output_file=tmp_path / "RESULT.xlsx")

    assert result["rows"] == 1
    assert (tmp_path / "RESULT.xlsx").exists()
    assert (tmp_path / "output" / "MASTER_AUDIT.txt").exists()
