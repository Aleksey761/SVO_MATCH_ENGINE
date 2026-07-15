import re
from typing import Optional

from .models import ArrivalItem


class Normalizer:
    """Normalizes arrival item text and extracts basic fields."""

    _DEFAULT_CATEGORY_RULES = [
        ("Кондиционер", ["кондиционер"]),
        ("ЖМС", ["жмс", "жидкое средство"]),
        ("Гель для душа", ["гель для душа"]),
        ("Шампунь", ["шампун"]),
    ]

    _DEFAULT_BRAND_RULES = [
        ("SVO", ["svo"]),
        ("GILAR", ["gilar"]),
        ("BOSSFIX", ["bossfix"]),
    ]

    _DEFAULT_VOLUME_RULES = [
        ("л", ["л", "литр", "литра", "литров"]),
        ("мл", ["мл", "ml"]),
    ]

    _DEFAULT_GARBAGE_WORDS = [
        "парфюмированн",
        "для стирки",
        "детских вещей",
        "синий",
        "красный",
        "желтый",
        "фиолетовый",
        "розовый",
        "черный",
    ]

    def __init__(
        self,
        category_rules: Optional[list[tuple[str, list[str]]]] = None,
        brand_rules: Optional[list[tuple[str, list[str]]]] = None,
        volume_rules: Optional[list[tuple[str, list[str]]]] = None,
        garbage_words: Optional[list[str]] = None,
    ):
        self._category_rules = category_rules or self._DEFAULT_CATEGORY_RULES
        self._brand_rules = brand_rules or self._DEFAULT_BRAND_RULES
        self._volume_rules = volume_rules or self._DEFAULT_VOLUME_RULES
        self._garbage_words = garbage_words or self._DEFAULT_GARBAGE_WORDS
        self._volume_re = re.compile(
            r"(\d+(?:[.,]\d+)?)\s*(л|литр|литра|литров|мл|ml)",
            re.IGNORECASE,
        )

    def normalize(self, item: ArrivalItem) -> ArrivalItem:
        text = self._clean_text(item.source_name)
        upper = text.upper()

        item.brand = self._detect_brand(text, upper)
        item.category = self._detect_category(text)
        item.volume = self._detect_volume(text)

        if item.brand:
            parts = re.split(re.escape(item.brand), text, flags=re.IGNORECASE, maxsplit=1)
            if len(parts) == 2:
                candidate = self._cleanup_candidate(parts[1])
                if candidate:
                    item.variant = candidate.upper()
                    item.aroma = candidate.upper()

        return item

    def _clean_text(self, value: str) -> str:
        return " ".join(str(value).replace(",", " ").split())

    def _detect_brand(self, text: str, upper_text: str) -> Optional[str]:
        for brand, patterns in self._brand_rules:
            if any(pattern.lower() in text.lower() for pattern in patterns):
                return brand
        for brand in (brand for brand, _ in self._brand_rules):
            if brand in upper_text:
                return brand
        return None

    def _detect_category(self, text: str) -> Optional[str]:
        lower = text.lower()
        for category, patterns in self._category_rules:
            if any(pattern in lower for pattern in patterns):
                return category
        return None

    def _detect_volume(self, text: str) -> Optional[str]:
        match = self._volume_re.search(text.lower())
        if not match:
            return None

        value = match.group(1).replace(",", ".")
        unit = match.group(2).lower()
        normalized_unit = "л"
        for canonical_unit, aliases in self._volume_rules:
            if unit in {alias.lower() for alias in aliases}:
                normalized_unit = canonical_unit
                break

        return f"{value} {normalized_unit}"

    def _cleanup_candidate(self, candidate: str) -> Optional[str]:
        cleaned = self._volume_re.sub("", candidate)
        for garbage_word in self._garbage_words:
            cleaned = re.sub(
                rf"\b{re.escape(garbage_word)}\b",
                "",
                cleaned,
                flags=re.IGNORECASE,
            )
        cleaned = " ".join(cleaned.replace(",", " ").split()).strip()
        return cleaned if cleaned else None
