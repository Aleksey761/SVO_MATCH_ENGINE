from pathlib import Path
from decimal import Decimal

from openpyxl import Workbook

from svo.models import ArrivalItem
from svo.normalizer import Normalizer
from svo.price_cleaner import PriceCleaner
from svo.price_loader import PriceLoader


def _write_supplier_price(path: Path, rows: list[list[object]]) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "PRICE"
    ws.append(["Supplier article", "Product name", "Free stock", "Distributor price"])
    for row in rows:
        ws.append(row)
    wb.save(path)
    return path


def test_price_cleaner_removes_packaging_marks():
    cleaner = PriceCleaner()

    cleaned = cleaner.clean("SVO shampoo apple 1 l \\ 9 96/12 24/6")

    assert cleaned == "SVO shampoo apple 1 l"


def test_price_cleaner_removes_duplicated_spaces_and_trims():
    cleaner = PriceCleaner()

    cleaned = cleaner.clean("   SVO    shampoo   apple   1 l   ")

    assert cleaned == "SVO shampoo apple 1 l"


def test_price_cleaner_preserves_product_meaning_tokens():
    cleaner = PriceCleaner()

    cleaned = cleaner.clean("SVO, shampoo; apple_1 l")

    assert "SVO" in cleaned
    assert "shampoo" in cleaned
    assert "apple" in cleaned
    assert "1 l" in cleaned


def test_price_cleaner_is_idempotent():
    cleaner = PriceCleaner()

    once = cleaner.clean("SVO shampoo apple 1 l \\ 9 96/12")
    twice = cleaner.clean(once)

    assert once == twice


def test_price_cleaner_integrates_with_normalizer():
    cleaner = PriceCleaner()
    item = ArrivalItem(row_number=1, source_name=cleaner.clean("SVO shampoo apple 1 l \\ 9 96/12"))

    normalized = Normalizer().normalize(item)

    assert normalized.brand == "SVO"
    assert normalized.category == "Шампунь"
    assert normalized.volume == "1 Л"
    assert normalized.aroma == "APPLE"


def test_price_loader_uses_cleaner_for_supplier_schema(tmp_path: Path):
    price_file = _write_supplier_price(
        tmp_path / "PRICE_SUPPLIER.xlsx",
        [["A-100", "SVO shampoo apple 1 l \\ 9 96/12", 42, "35,50"]],
    )

    items = PriceLoader().load(price_file)

    assert len(items) == 1
    assert items[0].source_name == "SVO shampoo apple 1 l"
    assert items[0].unit_cost is not None
    assert items[0].retail_price is not None


def test_price_loader_maps_required_russian_supplier_headers(tmp_path: Path):
    wb = Workbook()
    ws = wb.active
    ws.title = "PRICE"
    ws.append(["Артикул", "Полное наименование", "Свободный остаток", "Дистрибьюторская цена"])
    ws.append(["IGNORED-100", "SVO shampoo apple 1 l", 42, "35,50"])

    price_file = tmp_path / "PRICE_SUPPLIER_RU.xlsx"
    wb.save(price_file)

    items = PriceLoader().load(price_file)

    assert len(items) == 1
    assert items[0].source_name == "SVO shampoo apple 1 l"
    assert items[0].unit_cost == Decimal("35.50")
    assert items[0].retail_price == Decimal("35.50")
    assert getattr(items[0], "stock_qty", None) == 42
    assert getattr(items[0], "supplier_article", None) == "IGNORED-100"


def test_price_loader_builds_canonical_price_dataset_fields():
    item = ArrivalItem(row_number=2, source_name="SVO shampoo apple 1 l")
    item.sku = "SKU-APPLE"
    item.master_name = "Shampoo SVO APPLE 1 L"
    item.status = "MATCH"
    item.confidence = 100.0
    item.review_reasons = []
    item.unit_cost = 35.5
    item.retail_price = 79.9
    item.supplier_article = "SHOULD_BE_IGNORED"

    rows = PriceLoader.to_canonical_price_dataset([item])

    assert rows == [
        {
            "SKU": "SKU-APPLE",
            "MASTER_NAME": "Shampoo SVO APPLE 1 L",
            "UnitCost": 35.5,
            "RetailPrice": 79.9,
            "Status": "MATCH",
            "Confidence": 100.0,
            "ReviewReason": "",
        }
    ]
