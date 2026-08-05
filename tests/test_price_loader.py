from datetime import date
from decimal import Decimal
from pathlib import Path

from openpyxl import Workbook

from finance.loader import PriceLoader


def _write_price_workbook(path: Path, rows: list[list[object]]) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "PRICE"
    ws.append(
        [
            "SKU",
            "UnitCost",
            "RetailPrice",
            "WholesalePrice",
            "MarketplacePrice",
            "EffectiveFrom",
            "EffectiveTo",
            "Status",
        ]
    )
    for row in rows:
        ws.append(row)
    wb.save(path)
    return path


def test_price_loader_loads_price_xlsx_and_parses_types(tmp_path: Path):
    price_file = _write_price_workbook(
        tmp_path / "PRICE.xlsx",
        [
            ["sku-001", 35.5, 79.9, 58, 82, date(2026, 7, 1), None, "Active"],
            ["SKU-002", 12, 25, 21, 27, date(2026, 1, 1), date(2026, 12, 31), "inactive"],
        ],
    )

    dataset = PriceLoader().load(price_file, valuation_date=date(2026, 7, 15))

    assert dataset.row_count == 2
    assert dataset.valid_row_count == 2
    assert dataset.rejected_row_count == 0
    assert dataset.warning_count == 0

    first = dataset.records[0]
    assert first.sku == "SKU-001"
    assert first.unit_cost == Decimal("35.5")
    assert first.retail_price == Decimal("79.9")
    assert first.wholesale_price == Decimal("58")
    assert first.marketplace_price == Decimal("82")
    assert first.effective_from == date(2026, 7, 1)
    assert first.effective_to is None
    assert first.status == "Active"


def test_price_loader_rejects_invalid_rows_by_validation_rules(tmp_path: Path):
    price_file = _write_price_workbook(
        tmp_path / "PRICE.xlsx",
        [
            ["", 10, 20, 15, 25, date(2026, 1, 1), None, "Active"],
            ["SKU-NEG", -1, 20, 15, 25, date(2026, 1, 1), None, "Active"],
            ["SKU-DATE", 10, 20, 15, 25, date(2026, 2, 1), date(2026, 1, 1), "Active"],
            ["SKU-STATUS", 10, 20, 15, 25, date(2026, 1, 1), None, "Unknown"],
            ["SKU-OK", 10, 20, 15, 25, date(2026, 1, 1), None, "Active"],
        ],
    )

    dataset = PriceLoader().load(price_file, valuation_date=date(2026, 7, 15))

    assert dataset.row_count == 5
    assert dataset.valid_row_count == 1
    assert dataset.rejected_row_count == 4
    assert dataset.warning_count == 0
    assert [record.sku for record in dataset.records] == ["SKU-OK"]


def test_price_loader_detects_duplicate_active_overlaps_and_marks_ambiguous(tmp_path: Path):
    price_file = _write_price_workbook(
        tmp_path / "PRICE.xlsx",
        [
            ["SKU-001", 10, 20, 15, 25, date(2026, 1, 1), None, "Active"],
            ["SKU-001", 11, 21, 16, 26, date(2026, 7, 1), None, "Active"],
        ],
    )

    dataset = PriceLoader().load(price_file, valuation_date=date(2026, 7, 15))

    assert dataset.warning_count == 1
    assert dataset.duplicate_active_skus == ["SKU-001"]
    assert dataset.pricing_status_by_sku["SKU-001"] == "AmbiguousPrice"


def test_price_loader_assigns_pricing_statuses_for_active_inactive_future_expired(tmp_path: Path):
    price_file = _write_price_workbook(
        tmp_path / "PRICE.xlsx",
        [
            ["SKU-OK", 10, 20, 15, 25, date(2026, 1, 1), None, "Active"],
            ["SKU-INACTIVE", 10, 20, 15, 25, date(2026, 1, 1), None, "Inactive"],
            ["SKU-FUTURE", 10, 20, 15, 25, date(2026, 8, 1), None, "Active"],
            ["SKU-EXPIRED", 10, 20, 15, 25, date(2025, 1, 1), date(2026, 6, 30), "Active"],
        ],
    )

    loader = PriceLoader()
    dataset = loader.load(price_file, valuation_date=date(2026, 7, 15))

    assert dataset.pricing_status_by_sku["SKU-OK"] == "OK"
    assert dataset.pricing_status_by_sku["SKU-INACTIVE"] == "InactivePrice"
    assert dataset.pricing_status_by_sku["SKU-FUTURE"] == "FuturePrice"
    assert dataset.pricing_status_by_sku["SKU-EXPIRED"] == "ExpiredPrice"
    assert dataset.resolve_pricing_status("SKU-MISSING", date(2026, 7, 15)) == "MissingPrice"
