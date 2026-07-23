from pathlib import Path
import pytest

from svo.loader import Loader


def test_parse_arrival_date_dd_mm_yy():
    date_value = Loader.parse_arrival_date_from_filename("ARRIVAL_14.07.26.xlsx")

    assert date_value == "14.07.2026"


def test_parse_arrival_date_dd_mm_yyyy():
    date_value = Loader.parse_arrival_date_from_filename("Arrival 14.07.2026.xlsx")

    assert date_value == "14.07.2026"


def test_parse_arrival_date_yyyy_mm_dd_dash():
    date_value = Loader.parse_arrival_date_from_filename("2026-07-14 ARRIVAL.xlsx")

    assert date_value == "14.07.2026"


def test_parse_arrival_date_yyyy_mm_dd_underscore():
    date_value = Loader.parse_arrival_date_from_filename("ARRIVAL_2026_07_14.xlsx")

    assert date_value == "14.07.2026"


def test_parse_arrival_date_none_when_missing():
    date_value = Loader.parse_arrival_date_from_filename("ARRIVAL_without_date.xlsx")

    assert date_value is None


def test_discover_workbooks_finds_exact_files_and_date(tmp_path: Path):
    master = tmp_path / "MASTER_main.xlsx"
    arrival = tmp_path / "ARRIVAL_2026_07_14.xlsx"
    sales = tmp_path / "SALES_2026-07-15.xlsx"
    master.write_text("", encoding="utf-8")
    arrival.write_text("", encoding="utf-8")
    sales.write_text("", encoding="utf-8")

    discovered_master, discovered_arrival, discovered_sales, arrival_date, sales_date = Loader().discover_workbooks(
        tmp_path,
        require_sales=True,
    )

    assert discovered_master == master
    assert discovered_arrival == arrival
    assert discovered_sales == sales
    assert arrival_date == "14.07.2026"
    assert sales_date == "15.07.2026"


def test_discover_workbooks_raises_when_sales_missing(tmp_path: Path):
    (tmp_path / "MASTER_main.xlsx").write_text("", encoding="utf-8")
    (tmp_path / "ARRIVAL_2026_07_14.xlsx").write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="SALES workbook is missing"):
        Loader().discover_workbooks(tmp_path, require_sales=True)


def test_discover_workbooks_raises_when_multiple_sales_found(tmp_path: Path):
    (tmp_path / "MASTER_main.xlsx").write_text("", encoding="utf-8")
    (tmp_path / "ARRIVAL_2026_07_14.xlsx").write_text("", encoding="utf-8")
    (tmp_path / "SALES_2026-07-15.xlsx").write_text("", encoding="utf-8")
    (tmp_path / "SALES_2026-07-16.xlsx").write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="Multiple SALES workbooks found"):
        Loader().discover_workbooks(tmp_path, require_sales=True)
