from pathlib import Path
from decimal import Decimal

import pytest
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


def test_price_cleaner_preserves_decimal_commas_in_sizes():
    cleaner = PriceCleaner()

    cleaned = cleaner.clean("SVO кондиц. д/белья 1,440 мл FLORAL MIST / 9")

    assert "1,440 мл" in cleaned


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


@pytest.mark.parametrize(
    ("source_name", "expected_volume"),
    [
        ("SVO гель д/стирки 1,5 л SPRING", "1,5 Л"),
        ("SVO кондиц. д/белья 1,440 мл FLORAL MIST", "1,44 Л"),
        ("SVO кондиц. д/белья 2,700 мл SWEET TROPIC", "2,7 Л"),
    ],
)
def test_normalizer_parses_supplier_split_and_decimal_volumes(source_name: str, expected_volume: str):
    normalized = Normalizer().normalize(ArrivalItem(row_number=1, source_name=source_name))

    assert normalized.volume == expected_volume


@pytest.mark.parametrize(
    ("source_name", "expected_category", "expected_variant", "expected_volume"),
    [
        ("SVO Гель д/Стирки 1 л FLORAL MIST", "Кондиционер", "FLORAL MIST", "1 Л"),
        ("SVO Смягчитель 5 л ASK", "Кондиционер", "ASK", "5 Л"),
        ("SVO средство д/посуды 750 гр ЯБЛОКО Apple", "Посуда моющее ср-во", "APPLE", "750 МЛ"),
        ("BOSSFIX Подгузники Детские №4 (60шт) / 3", "Подгузники", "SIZE 4", "1 УП"),
        ("GILAR Шампунь 400 мл мужс. ARGAN OIL", "Шампунь men", "ARGAN OIL", "400 МЛ"),
        ("GILAR Шампунь 500 мл дозат GINSENG OIL", "Шампунь органический", "GINSENG", "500 МЛ"),
        ("SVO гель д/стирки 2,7 л ЖЁЛТЫЙ", "Кондиционер", "VANILLA", "2,7 Л"),
        ("SVO гель д/стирки 2,7 л ЧЁРНЫЙ", "Кондиционер", "BLACK", "2,7 Л"),
        ("SVO кондиц. д/белья 2,700 мл АРОМАТ СТРАСТИ", "Кондиционер", "BLACK GEL", "2,7 Л"),
        ("SVO порош. стир. 5 кг ШЕЙХ для цв. и бел", "Порошок стиральный", "MAGINA", "5 КГ"),
    ],
)
def test_normalizer_applies_price_context_refinements(
    source_name: str,
    expected_category: str,
    expected_variant: str,
    expected_volume: str,
):
    normalized = Normalizer().normalize(ArrivalItem(row_number=1, source_name=source_name))

    assert normalized.category == expected_category
    assert normalized.product_type == expected_category
    assert normalized.variant == expected_variant
    assert normalized.aroma == expected_variant
    assert normalized.volume == expected_volume


@pytest.mark.parametrize(
    ("source_name", "expected_variant"),
    [
        ("SVO порош. стир. 1,3 кг РОМАШКА Daisy / 12", "BABY"),
        ("SVO порош. стир. 1,3 кг РОМАШКА Daisy для цв. и бел / 12", "COLOR"),
        ("SVO порош. стир. 9 кг ПОДСНЕЖНИК для цв. и бел 100/1", "SNOWDROP"),
        ("GILAR Шампунь 600 мл MENTOL \\12", "MINT"),
        ("SVO порош. стир. 4 кг РОМАШКА Daisy для цв. и бел / 4", "COLOR"),
        ("SVO порош. стир. 6 кг РОМАШКА для цветных", "COLOR"),
        ("SVO порош. стир.10 кг РОМАШКА д\\цветного 90/1", "COLOR"),
    ],
)
def test_normalizer_applies_confirmed_variant_and_color_canonicalization(source_name: str, expected_variant: str):
    normalized = Normalizer().normalize(ArrivalItem(row_number=1, source_name=source_name))

    assert normalized.variant == expected_variant
    assert normalized.aroma == expected_variant


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
