from svo.normalizer import Normalizer
from svo.models import ArrivalItem


def normalize(source_name: str) -> ArrivalItem:
    item = ArrivalItem(source_name=source_name)
    return Normalizer().normalize(item)


def test_gilar_apostrophe_variant_normalizes_to_gilar():
    item = normalize("Шампунь GILA’R Intense 400 мл")
    assert item.brand == "GILAR"


def test_gilar_plain_variant_normalizes_to_gilar():
    item = normalize("Шампунь GILA'R Intense 400 мл")
    assert item.brand == "GILAR"


def test_conditioner_mountain_breeze_alias_is_canonical():
    item = normalize("Кондиционер SVO Горный бриз 1 л")
    assert item.aroma == "MOUNTAIN BREEZE"


def test_conditioner_lavender_alias_is_canonical():
    item = normalize("Кондиционер SVO Лаванда 1 л")
    assert item.aroma == "LAVENDER"


def test_conditioner_peony_alias_is_canonical():
    item = normalize("Кондиционер SVO Пион 1 л")
    assert item.aroma == "PEONY"


def test_conditioner_lotos_alias_is_canonical():
    item = normalize("Кондиционер SVO Таинственный лотос 2,7 л")
    assert item.aroma == "LOTOS"
