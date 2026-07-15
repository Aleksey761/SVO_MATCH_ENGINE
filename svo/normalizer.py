import re
from decimal import Decimal
from typing import Optional

from .models import ArrivalItem


class Normalizer:
    """Normalizes arrival item text and extracts basic fields."""

    _DEFAULT_CATEGORY_RULES = [
        ("Кондиционер", ["кондиционер"]),
        ("ЖМС", ["жмс", "жидкое средство"]),
        ("Гель для душа", ["гель для душа"]),
        ("Шампунь", ["шампун", "shampoo"]),
    ]

    _DEFAULT_BRAND_RULES = [
        ("SVO", ["svo"]),
        ("GILAR", ["gilar"]),
        ("BOSSFIX", ["bossfix"]),
    ]

    _DEFAULT_VOLUME_RULES = [
        ("л", ["л", "литр", "литра", "литров", "liter", "liters", "l"]),
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
        "parfume",
        "parfum",
        "junk",
    ]

    _DEFAULT_AROMA_ALIASES = {
        "ЛАЙМ": ["lime", "лайм"],
        "АКВА": ["aqua", "аква"],
        "ЦИТРУС": ["citrus", "цитрус"],
    }

    def __init__(
        self,
        category_rules: Optional[list[tuple[str, list[str]]]] = None,
        brand_rules: Optional[list[tuple[str, list[str]]]] = None,
        volume_rules: Optional[list[tuple[str, list[str]]]] = None,
        garbage_words: Optional[list[str]] = None,
        aroma_aliases: Optional[dict[str, list[str]]] = None,
    ):
        self._category_rules = self._coerce_rules(category_rules or self._DEFAULT_CATEGORY_RULES)
        self._brand_rules = self._coerce_rules(brand_rules or self._DEFAULT_BRAND_RULES)
        self._volume_rules = volume_rules or self._DEFAULT_VOLUME_RULES
        self._garbage_words = garbage_words or self._DEFAULT_GARBAGE_WORDS
        self._aroma_aliases = aroma_aliases or self._DEFAULT_AROMA_ALIASES
        self._volume_re = re.compile(
            r"(\d+(?:[.,]\d+)?)\s*(л|литр|литра|литров|мл|ml|liter|liters|l)",
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
                    normalized_aroma = self._normalize_aroma(candidate)
                    item.variant = normalized_aroma.upper()
                    item.aroma = normalized_aroma.upper()

        return item

    @staticmethod
    def _coerce_rules(rules) -> list[tuple[str, list[str]]]:
        if isinstance(rules, dict):
            return [(key, list(value)) for key, value in rules.items()]
        return list(rules)

    def _clean_text(self, value: str) -> str:
        return " ".join(str(value).replace(",", " ").split())

    def _detect_brand(self, text: str, upper_text: str) -> Optional[str]:
        lower_text = text.lower()
        for brand, patterns in self._brand_rules:
            for pattern in patterns:
                if re.search(rf"\b{re.escape(pattern.lower())}\b", lower_text):
                    return brand
        for brand in (brand for brand, _ in self._brand_rules):
            if brand in upper_text:
                return brand
        return None

    def _detect_category(self, text: str) -> Optional[str]:
        lower = text.lower()
        for category, patterns in self._category_rules:
            if any(re.search(rf"\b{re.escape(pattern.lower())}\b", lower) for pattern in patterns):
                return category
        return None

    def _detect_volume(self, text: str) -> Optional[str]:
        match = self._volume_re.search(text.lower())
        if not match:
            return None

        value = Decimal(match.group(1).replace(",", "."))
        unit = match.group(2).lower()
        normalized_unit = "мл"

        for canonical_unit, aliases in self._volume_rules:
            lowered_aliases = {alias.lower() for alias in aliases}
            if unit in lowered_aliases:
                normalized_unit = canonical_unit
                break

        if normalized_unit == "л":
            liters = value
            return f"{self._format_decimal(liters)} Л"
        return f"{self._format_decimal(value / Decimal('1000'))} Л" if value >= Decimal('1000') else f"{self._format_decimal(value)} МЛ"

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

    def _normalize_aroma(self, candidate: str) -> str:
        normalized = []
        for token in re.split(r"\s+", candidate.strip()):
            lowered = token.lower()
            mapped = None
            for canonical, aliases in self._aroma_aliases.items():
                if lowered in {alias.lower() for alias in aliases}:
                    mapped = canonical
                    break
            normalized.append(mapped or token)
        return " ".join(normalized).strip()

    @staticmethod
    def _format_decimal(value: Decimal) -> str:
        if value == value.to_integral_value():
            return str(int(value))
        text = format(value.normalize(), "f")
        text = text.rstrip("0").rstrip(".")
        return text.replace(".", ",")
