from pathlib import Path

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
    master.write_text("", encoding="utf-8")
    arrival.write_text("", encoding="utf-8")

    discovered_master, discovered_arrival, arrival_date = Loader().discover_workbooks(tmp_path)

    assert discovered_master == master
    assert discovered_arrival == arrival
    assert arrival_date == "14.07.2026"
