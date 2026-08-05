from svo.business_rules import BusinessRules
from svo.models import ArrivalItem, MasterItem


def _master_item(
    sku: str,
    category: str,
    brand: str,
    variant: str,
    volume: str,
    master_name: str,
) -> MasterItem:
    return MasterItem(
        sku=sku,
        category=category,
        brand=brand,
        variant=variant,
        volume=volume,
        master_name=master_name,
    )


def test_lotos_rule_promotes_sku_064_from_review():
    sku_035 = _master_item("SKU-035", "Кондиционер", "SVO", "Lotos", "1,44 л", "Кондиционер SVO Lotos 1,44 л")
    sku_064 = _master_item("SKU-064", "Кондиционер", "SVO", "Lotos", "2,7 л", "Кондиционер SVO Lotos 2,7 л")
    item = ArrivalItem(
        row_number=17,
        source_name="Кондиционер SVO Таинственный лотос",
        status="REVIEW",
        review_reasons=["MULTIPLE_MATCH", "NO_VOLUME"],
        candidates=[sku_035, sku_064],
    )

    BusinessRules([sku_035, sku_064]).apply([item])

    assert item.status == "MATCH"
    assert item.sku == "SKU-064"
    assert item.master_name == "Кондиционер SVO Lotos 2,7 л"
    assert item.review_reasons == []


def test_botanic_rule_promotes_botanic_144():
    botanic_144 = _master_item("SKU-051", "Кондиционер", "SVO", "Botanic Rainy April", "1,44 л", "Кондиционер SVO Botanic Rainy April 1,44 л")
    botanic_270 = _master_item("SKU-070", "Кондиционер", "SVO", "Botanic Rainy April", "2,7 л", "Кондиционер SVO Botanic Rainy April 2,7 л")
    item = ArrivalItem(
        row_number=155,
        source_name="Кондиционер для стирки, SVO Botanic парфюмированный",
        category="Кондиционер",
        status="REVIEW",
        review_reasons=["LOW_SCORE", "NO_VOLUME"],
        candidates=[botanic_270],
    )

    BusinessRules([botanic_270, botanic_144]).apply([item])

    assert item.status == "MATCH"
    assert item.sku == "SKU-051"
    assert item.master_name == "Кондиционер SVO Botanic Rainy April 1,44 л"


def test_bossfix_diapers_without_size_promotes_size1():
    size1 = _master_item("SKU-283", "Подгузники", "BOSSFIX", "Size 1", "1 уп", "Подгузники BOSSFIX Size 1")
    size2 = _master_item("SKU-284", "Подгузники", "BOSSFIX", "Size 2", "1 уп", "Подгузники BOSSFIX Size 2")
    item = ArrivalItem(
        row_number=143,
        source_name="Подгузники одноразовые BOSSFIX",
        category="Подгузники",
        brand="BOSSFIX",
        status="REVIEW",
        review_reasons=["MULTIPLE_MATCH", "NO_VOLUME"],
        candidates=[size2],
    )

    BusinessRules([size2, size1]).apply([item])

    assert item.status == "MATCH"
    assert item.sku == "SKU-283"
    assert item.master_name == "Подгузники BOSSFIX Size 1"


def test_bundle_keywords_keep_item_in_review():
    sku_035 = _master_item("SKU-035", "Кондиционер", "SVO", "Lotos", "1,44 л", "Кондиционер SVO Lotos 1,44 л")
    sku_064 = _master_item("SKU-064", "Кондиционер", "SVO", "Lotos", "2,7 л", "Кондиционер SVO Lotos 2,7 л")
    item = ArrivalItem(
        row_number=177,
        source_name="Сборка SVO Lotos",
        status="REVIEW",
        review_reasons=["MULTIPLE_MATCH", "NO_VOLUME"],
        candidates=[sku_035, sku_064],
    )

    BusinessRules([sku_035, sku_064]).apply([item])

    assert item.status == "REVIEW"
    assert item.sku is None
    assert item.review_reasons == ["MULTIPLE_MATCH", "NO_VOLUME"]
