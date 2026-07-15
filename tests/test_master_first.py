from svo.models import ArrivalItem, MasterItem
from svo.matcher import Matcher
from svo.normalizer import Normalizer


def test_master_first_indexing_supports_sku_and_other_keys():
    master_items = [
        MasterItem(sku="SKU-1", category="Шампунь", brand="SVO", variant="AQUA", volume="1 л"),
        MasterItem(sku="SKU-2", category="Гель для душа", brand="GILAR", variant="LIME", volume="500 мл"),
    ]

    matcher = Matcher(master_items)

    assert matcher.master_index["SKU-1"] == master_items[0]
    assert matcher.master_index["SHAMPUN"].sku == "SKU-1"
    assert matcher.master_index["SVO"].sku == "SKU-1"
    assert matcher.master_index["1 Л"].sku == "SKU-1"
    assert matcher.master_index["AQUA"].sku == "SKU-1"


def test_match_prefers_master_catalog_matches_before_fuzzy_fallback():
    master_items = [
        MasterItem(sku="SKU-10", category="Шампунь", brand="SVO", variant="AQUA", volume="1 л"),
    ]
    matcher = Matcher(master_items)

    arrival = ArrivalItem(row_number=1, source_name="SVO SHAMPUN AQUA 1 л")
    arrival.category = "Шампунь"
    arrival.brand = "SVO"
    arrival.variant = "AQUA"
    arrival.volume = "1 л"

    matched = matcher.match(arrival)

    assert matched.status == "MATCH"
    assert matched.sku == "SKU-10"


def test_normalizer_supports_configurable_rules():
    normalizer = Normalizer(
        brand_rules=[("SVO", ["svo", "sv"]), ("GILAR", ["gilar"])],
        volume_rules=[("л", ["л", "liter"]), ("мл", ["ml"])],
        garbage_words=["parfume", "junk"],
        aroma_aliases={"ЛАЙМ": ["lime", "лайм"]},
    )
    item = ArrivalItem(row_number=1, source_name="SV GILAR SHAMPOO 500 ml JUNK LIME")

    result = normalizer.normalize(item)

    assert result.brand == "SVO"
    assert result.volume == "500 МЛ"
    assert result.variant == "LIME"
    assert result.aroma == "LIME"


def test_normalizer_converts_large_volumes_to_liters_and_removes_garbage_words():
    normalizer = Normalizer(
        category_rules=[("Шампунь", ["шампунь"])],
        brand_rules=[("SVO", ["svo"])],
        aroma_aliases={"АКВА": ["aqua", "аква"]},
    )
    item = ArrivalItem(row_number=2, source_name="SVO Shampun 1000 ml PARFUME AQUA")

    result = normalizer.normalize(item)

    assert result.category == "Шампунь"
    assert result.brand == "SVO"
    assert result.volume == "1 Л"
    assert result.variant == "AQUA"
    assert result.aroma == "AQUA"
