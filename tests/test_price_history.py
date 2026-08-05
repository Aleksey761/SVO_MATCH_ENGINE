from datetime import datetime, timedelta, timezone
from decimal import Decimal

from finance.price_history import PriceHistory


def _utc(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


def _row(
    *,
    sku: str = "SKU-001",
    master_name: str = "Product A",
    unit_cost: object = "100",
    retail_price: object = "150",
    source_unit: str | None = "шт",
) -> dict[str, object]:
    return {
        "SKU": sku,
        "MASTER_NAME": master_name,
        "UnitCost": unit_cost,
        "RetailPrice": retail_price,
        "SourceUnit": source_unit,
    }


def test_first_import_creates_active_record():
    history = PriceHistory()
    imported_at = _utc("2026-08-01T10:00:00")

    created = history.import_prices([_row()], source_file="PRC.xlsx", imported_at=imported_at)

    assert len(created) == 1
    record = created[0]
    assert record.Status == "ACTIVE"
    assert record.ValidFrom == imported_at
    assert record.ValidTo is None
    assert record.SourceFile == "PRC.xlsx"
    assert record.ImportedAt == imported_at


def test_same_price_does_not_duplicate_history():
    history = PriceHistory()
    t1 = _utc("2026-08-01T10:00:00")
    t2 = _utc("2026-08-02T10:00:00")

    history.import_prices([_row(unit_cost="100")], source_file="PRC_A.xlsx", imported_at=t1)
    created = history.import_prices([_row(unit_cost="100")], source_file="PRC_B.xlsx", imported_at=t2)

    assert len(created) == 0
    assert len(history.records) == 1
    assert history.records[0].Status == "ACTIVE"


def test_changed_price_closes_previous_record():
    history = PriceHistory()
    t1 = _utc("2026-08-01T10:00:00")
    t2 = _utc("2026-08-03T12:00:00")

    history.import_prices([_row(unit_cost="100")], source_file="PRC_A.xlsx", imported_at=t1)
    history.import_prices([_row(unit_cost="120")], source_file="PRC_B.xlsx", imported_at=t2)

    assert len(history.records) == 2
    first = history.records[0]
    second = history.records[1]

    assert first.Status == "CLOSED"
    assert first.ValidTo == t2 - timedelta(seconds=1)
    assert second.Status == "ACTIVE"
    assert second.ValidFrom == t2
    assert second.ValidTo is None


def test_package_price_converts_to_per_piece_correctly():
    history = PriceHistory()

    created = history.import_prices(
        [_row(unit_cost="1566", source_unit="упак (9 шт)")],
        source_file="PRC.xlsx",
        imported_at=_utc("2026-08-01T10:00:00"),
    )

    assert created[0].UnitCost == Decimal("174")


def test_original_price_preserved():
    history = PriceHistory()

    created = history.import_prices(
        [_row(unit_cost="1566", source_unit="упак (9 шт)")],
        source_file="PRC.xlsx",
        imported_at=_utc("2026-08-01T10:00:00"),
    )

    assert created[0].OriginalPrice == Decimal("1566")


def test_pack_qty_extracted():
    history = PriceHistory()

    created = history.import_prices(
        [_row(unit_cost="1566", source_unit="упак (9 шт)")],
        source_file="PRC.xlsx",
        imported_at=_utc("2026-08-01T10:00:00"),
    )

    assert created[0].PackQty == 9


def test_history_lookup_by_date_returns_correct_unit_cost():
    history = PriceHistory()
    t1 = _utc("2026-08-01T10:00:00")
    t2 = _utc("2026-08-03T12:00:00")

    history.import_prices([_row(unit_cost="100")], source_file="PRC_A.xlsx", imported_at=t1)
    history.import_prices([_row(unit_cost="120")], source_file="PRC_B.xlsx", imported_at=t2)

    assert history.lookup_unit_cost("SKU-001", _utc("2026-08-02T12:00:00")) == Decimal("100")
    assert history.lookup_unit_cost("SKU-001", _utc("2026-08-04T12:00:00")) == Decimal("120")
