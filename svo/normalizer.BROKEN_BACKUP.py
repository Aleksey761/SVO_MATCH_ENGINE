import re
from decimal import Decimal
from typing import Optional

from .models import ArrivalItem


class Normalizer:
    """Normalizes arrival item text and extracts basic fields."""

    _DEFAULT_CATEGORY_RULES = [
        ("Кондиционер", [
            "кондиционер",
            "кондиц. д/белья",
            "кондиц д/белья",
            "кондиц. для белья",
            "кондиц для белья",
        ]),
        ("ЖМС", [
            "жмс",
            "жидкое средство",
            "ж/моющее ср-во",
            "ж моющее ср-во",
            "жидкое моющее средство",
            "гель д\\стирки",
            "гель д/стирки",
            "гель для стирки",
        ]),
        ("Гель для душа", ["гель для душа"]),
        ("Порошок стиральный", [
            "порошок стиральный",
            "порош. стир.",
            "порошок стир.",
            "порошок для стирки",
            "порош. стир",
            "порош стир",
            "порошок стир",
        ]),
        ("Подгузники", ["подгузник", "подгузники", "одгузник", "одгузники", "етские", "детские"]),
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
        ("кг", ["кг", "kg", "килограмм", "килограмма", "килограммов"]),
        ("г", ["г", "гр", "грамм", "грамма", "граммов", "gram", "grams"]),
    ]

    _DEFAULT_GARBAGE_WORDS = [
        "парфюмированн",
        "для стирки",
        "детских вещей",
        "синий",
        "син",
        "красный",
        "красн",
        "желтый",
        "желт",
        "фиолетовый",
        "фиол",
        "розовый",
        "розов",
        "черный",
        "черн",
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
            r"(\d+(?:[.,]\d+)?)\s*(л|литр|литра|литров|мл|ml|liter|liters|l|кг|kg|килограмм|килограмма|килограммов|г|гр|грамм|грамма|граммов|gram|grams)",
            re.IGNORECASE,
        )

    def normalize(self, item: ArrivalItem) -> ArrivalItem:
        working_name = str(getattr(item, "match_name", None) or item.source_name or "")
        text = self._clean_text(working_name)
        upper = text.upper()

        item.brand, brand_match = self._detect_brand(text, upper)
        item.category = self._detect_category(text)
        item.volume = self._detect_volume(text)

        # Canonical MASTER routing for PRICE:
        # SVO 1 l / 1.5 l liquid detergents belong to the
        # SVO Elegant line in MASTER. A 2.7 l item must NOT be
        # routed to the separate "ЖМС 3в1" block by volume alone:
        # that block is selected only when the source explicitly
        # says 3-in-1 / 3в1 (or an equivalent combined-product marker).
        if item.brand == "SVO" and item.category == "ЖМС":
            # Baby is a separate SVO line in MASTER (SKU-093 at 1.5 l,
            # SKU-293 at 1 l), so it must not inherit the SVO Elegant brand.
            is_baby = bool(re.search(r"\bbaby\b", text, flags=re.IGNORECASE))
            if item.volume in {"1 Л", "1,5 Л"} and not is_baby:
                item.brand = "SVO Elegant"
            elif self._is_three_in_one(text):
                item.category = "ЖМС 3в1"

        if item.brand:
            candidate = self._cleanup_candidate(text, brand_match)

            if item.category == "Подгузники":
                # MASTER identifies diapers by size, not by the package-count suffix.
                size_match = re.search(
                    r"(?:№\s*)?([1-6])\s*(?:\(|$|шт|/)",
                    text,
                    flags=re.IGNORECASE,
                )
                if size_match:
                    candidate = f"Size {size_match.group(1)}"

            elif item.category == "Порошок стиральный":
                # Remove packaging/service tails, preserve the actual aroma/color.
                candidate = re.sub(
                    r"\b(?:12|24|3|6)\s*шт\b.*$",
                    "",
                    candidate,
                    flags=re.IGNORECASE,
                ).strip(" /-")
                candidate = re.sub(
                    r"\b(?:для\s+цв\.\s*и\s*бел|д[/\\]?цветного|д[/\\]?белого|для\s+цветных|для\s+белых|для\s+черных)\b",
                    "",
                    candidate,
                    flags=re.IGNORECASE,
                ).strip(" /-")

            if candidate:
                # PRICE aliases / Cyrillic-to-MASTER aroma normalization.
                aliases = {
                    "MEDINA": "MAGINA",
                    "MENTOL": "MINT",
                    "Я ССТЬ": "MOUNTAIN BREEZE",
                    "Ы ": "MOUNTAIN BREEZE",
                    "": "ROSE",
                    "С": "SNOWDROP",
                    "ШХ": "SHEIKH",
                    
                    "ЬС": "ORANGE",
                    "Т": "GRAPEFRUIT",
                    "Я": "APPLE",
                    "ТЫ": "YELLOW",
                    "ТЫ": "YELLOW",
                    "СЫ": "RED",
                    "Ы": "PINK",
                    "С": "BLUE",
                    "ТЫ": "PURPLE",
                    "Ы": "BLACK",
                    "Ы": "BLACK",
                }

                normalized_candidate = candidate.strip()
                upper_candidate = normalized_candidate.upper()
                for source, target in aliases.items():
                    upper_candidate = re.sub(
                        rf"\b{re.escape(source)}\b",
                        target,
                        upper_candidate,
                        flags=re.IGNORECASE,
                    )
                candidate = upper_candidate

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
        # Preserve decimal commas because PRICE contains volumes such as
        # 1,5 л / 2,7 л / 1,440 мл. Replacing "," with a space turns
        # those into "1 5" / "2 7" and breaks volume extraction.
        text = str(value).replace("\u00a0", " ")
        return " ".join(text.split())

    def _detect_brand(self, text: str, upper_text: str) -> tuple[Optional[str], Optional[str]]:
        lower_text = text.lower()
        for brand, patterns in self._brand_rules:
            for pattern in patterns:
                if re.search(rf"\b{re.escape(pattern.lower())}\b", lower_text):
                    return brand, pattern
        for brand in (brand for brand, _ in self._brand_rules):
            if brand in upper_text:
                return brand, brand
        return None, None

    def _detect_category(self, text: str) -> Optional[str]:
        lower = text.lower()
        for category, patterns in self._category_rules:
            if any(re.search(rf"\b{re.escape(pattern.lower())}\b", lower) for pattern in patterns):
                return category
        if re.search(r"\b(?:shamp(?:oo|un)|шампун)", lower):
            for category, patterns in self._category_rules:
                haystack = " ".join([category, *patterns]).upper()
                if "\u0428\u0410\u041c\u041f\u0423\u041d" in haystack:
                    return category

        # PRICE-specific categories.
        if re.search(r"\b(?:пятновыводитель|пятновыводит)", lower):
            return "ятновыводитель"

        if re.search(r"средств[оа]\s+(?:д/|для\s+)?посуд", lower):
            return "осуда моющее ср-во"

        return None

    @staticmethod
    def _is_three_in_one(text: str) -> bool:
        """Return True only for explicit 3-in-1 product markers.

        Volume (especially 2.7 l) is deliberately not used as a proxy
        for the 3-in-1 category because MASTER contains separate product
        blocks at the same volume.
        """
        lower = text.lower()
        patterns = (
            r"\b3\s*в\s*1\b",
            r"\b3\s*[-/]\s*в\s*[-/]?\s*1\b",
            r"\b3\s*[-/]\s*1\b",
            r"\b3in1\b",
            r"\b3\s*in\s*1\b",
        )
        return any(re.search(pattern, lower) for pattern in patterns)

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
        if normalized_unit == "мл":
            # PRICE uses forms such as "1,440 мл" for 1.44 litres.
            # Treat a value between 1 and 10 with three decimal places
            # as a litre value expressed in ml notation.
            if Decimal("1") <= value < Decimal("10") and "," in match.group(1) and len(match.group(1).split(",", 1)[1]) == 3:
                return f"{self._format_decimal(value)} Л"
            return f"{self._format_decimal(value / Decimal('1000'))} Л" if value >= Decimal('1000') else f"{self._format_decimal(value)} МЛ"
        if normalized_unit == "кг":
            return f"{self._format_decimal(value)} КГ"
        if normalized_unit == "г":
            return f"{self._format_decimal(value)} Г"

    def _cleanup_candidate(self, candidate: str, brand_match: Optional[str] = None) -> Optional[str]:
        cleaned = self._volume_re.sub("", candidate)
        # Remove PRICE packaging/count tails:
        #   /12, \\ 7, / 6, 90/12, 54/9, 30/6, etc.
        cleaned = re.sub(r"\s*\d+\s*[/\\]\s*\d+\s*$", "", cleaned)
        cleaned = re.sub(r"\s*[/\\]\s*\d+\s*$", "", cleaned)
        cleaned = cleaned.strip(" /\\-")
        removal_terms = []
        if brand_match:
            removal_terms.append(brand_match)
        for _, patterns in self._brand_rules:
            removal_terms.extend(patterns)
        for _, patterns in self._category_rules:
            removal_terms.extend(patterns)
        removal_terms.extend([
            "shampoo",
            "shampun",
            "гель д\\стирки",
            "гель д/стирки",
            "гель для стирки",
            "кондиц. д/белья",
            "кондиц д/белья",
            "кондиц. для белья",
            "кондиц для белья",
            "ж/моющее ср-во",
            "ж моющее ср-во",
            "3в1",
            "3 в 1",
            "3-в-1",
            "3/1",
            "3in1",
            "3 in 1",
            "порош. стир.",
            "порошок стир.",
            "порошок стиральный",
            "порошок для стирки",
            "для цв. и бел",
            "д\\цветного",
            "д/цветного",
            "для черных",
            "для цветных",
            "для белых",
            "12шт",
            "12 шт",
            "24шт",
            "24 шт",
            "3шт",
            "3 шт",
            "6шт",
            "6 шт",
        ])
        for term in sorted(set(removal_terms), key=len, reverse=True):
            cleaned = re.sub(
                rf"\b{re.escape(term)}\w*",
                "",
                cleaned,
                flags=re.IGNORECASE,
            )
        for garbage_word in self._garbage_words:
            cleaned = re.sub(
                rf"\b{re.escape(garbage_word)}\w*",
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
                    mapped = token
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

