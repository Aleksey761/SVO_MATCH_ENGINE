from svo.matcher import Matcher
from svo.models import ArrivalItem, MasterItem
from svo.name_correction import NameCorrectionLayer
from svo.normalizer import Normalizer


def _master_items() -> list[MasterItem]:
    return [
        MasterItem(
            sku="SKU-CHOC",
            category="Жидкое мыло",
            brand="SVO",
            variant="CHOCOLATE",
            volume="500 МЛ",
            master_name="ЖИДКОЕ МЫЛО SVO CHOCOLATE 500 МЛ",
            aroma="CHOCOLATE",
        ),
        MasterItem(
            sku="SKU-WILD",
            category="Жидкое мыло",
            brand="SVO",
            variant="WILD BERRIES",
            volume="500 МЛ",
            master_name="ЖИДКОЕ МЫЛО SVO WILD BERRIES 500 МЛ",
            aroma="WILD BERRIES",
        ),
        MasterItem(
            sku="SKU-LAV",
            category="Шампунь органический",
            brand="GILAR",
            variant="LAVENDER OIL",
            volume="500 МЛ",
            master_name="ШАМПУНЬ ОРГАНИЧЕСКИЙ GILAR LAVENDER OIL 500 МЛ",
            aroma="LAVENDER OIL",
        ),
    ]


def test_name_correction_cocolade_to_chocolate():
    layer = NameCorrectionLayer(_master_items())
    decision = layer.apply_to_name("Жидкое мыло SVO COCOLADE 500 мл", source="PRICE")
    assert decision.applied is True
    assert "CHOCOLATE" in decision.after_name


def test_name_correction_wildberes_to_wild_berries():
    layer = NameCorrectionLayer(_master_items())
    decision = layer.apply_to_name("Жидкое мыло SVO WILDBERES 500 мл", source="SALES")
    assert decision.applied is True
    assert "WILD BERRIES" in decision.after_name


def test_name_correction_lavander_to_lavender():
    layer = NameCorrectionLayer(_master_items())
    decision = layer.apply_to_name("Шампунь GILAR Lavander Oil 500 мл", source="INVENTORY")
    assert decision.applied is True
    assert "LAVENDER" in decision.after_name


def test_unknown_typo_stays_review():
    masters = _master_items()
    layer = NameCorrectionLayer(masters)
    item = ArrivalItem(row_number=1, source_name="UNMAPPED TYPO PRODUCT 123")

    decision = layer.apply_to_item(item, source="PRICE")
    assert decision.applied is False

    Normalizer().normalize(item)
    matched = Matcher(masters).match(item)
    assert matched.status == "REVIEW"
