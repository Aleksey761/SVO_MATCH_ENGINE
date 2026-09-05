import re
from decimal import Decimal
from typing import Optional

from .models import ArrivalItem
from .dictionary import Dictionary


class Normalizer:
    """Normalizes arrival item text and extracts basic fields."""

    _DEFAULT_PRODUCT_TYPE_RULES = [
        ("Гель для стирки", ["гель для стирки", "моющее средство для белья", "средство для стирки"]),
        ("Кондиционер", ["кондиционер"]),
        ("Порошок", ["порошок", "порошок стиральный"]),
        ("Гель для душа", ["гель для душа"]),
        ("Шампунь", ["шампун", "shampoo"]),
        ("Мыло", ["мыло", "soap"]),
        ("ЖМС", ["жмс", "жидкое средство"]),
    ]

    _DEFAULT_CATEGORY_RULES = [
        ("Кондиционер", ["кондиционер"]),
        ("ЖМС", ["жмс", "жидкое средство"]),
        ("Гель для душа", ["гель для душа"]),
        ("Шампунь", ["шампун", "shampoo"]),
        ("Шампунь men", ["шампунь men", "men shampoo", "мужской шампунь"]),
        ("Шампунь women", ["шампунь women", "women shampoo", "женский шампунь"]),
        ("Шампунь sport", ["шампунь sport", "sport shampoo"]),
        ("Шампунь органический", ["шампунь органический", "organic shampoo"]),
    ]

    _DEFAULT_BRAND_RULES = [
        ("SVO", ["svo"]),
        ("GILAR", ["gilar"]),
        ("BOSSFIX", ["bossfix"]),
        ("SVO ELEGANT", ["svo elegant", "elegant"]),
        ("PEARLIS", ["pearlis"]),
        ("YUNIS EFFENDI", ["yunis effendi"]),
        ("DOMIX", ["domix"]),
    ]

    _DEFAULT_VOLUME_RULES = [
        ("л", ["л", "литр", "литра", "литров", "liter", "liters", "l"]),
        ("мл", ["мл", "ml"]),
        ("кг", ["кг", "kg"]),
        ("г", ["г", "гр", "g"]),
        ("уп", ["уп", "шт"]),
    ]

    _DEFAULT_GARBAGE_WORDS = [
        "парфюмированн",
        "парфюмирова",
        "парфюм",
        "для стирки",
        "моющее средство",
        "для мытья посуды",
        "посуды",
        "средство",
        "моющее",
        "мужской",
        "женский",
        "oil",
        "extract",
        "extracts",
        "plus",
        "детских вещей",
        "аромат",
        "ароматы",
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

    _DEFAULT_AROMA_ALIASES = {}

    _AROMA_STOP_TOKENS = {
        "для",
        "с",
        "и",
        "в",
        "на",
        "по",
        "из",
        "мужчин",
        "мужской",
        "женский",
        "women",
        "woman",
        "men",
        "man",
        "sport",
        "шампунь",
        "гель",
        "душа",
        "жидкое",
        "моющее",
        "средство",
        "мытья",
        "посуды",
        "белья",
        "крем",
        "блок",
        "туалетный",
        "унитаза",
        "автомат",
        "натуральное",
        "натуральный",
        "романтик",
        "тропик",
        "масло",
        "масла",
        "маслом",
        "масляный",
        "масляная",
        "oil",
    }

    _CYR_TO_LAT = str.maketrans(
        {
            "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
            "ж": "zh", "з": "z", "и": "i", "й": "i", "к": "k", "л": "l", "м": "m",
            "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
            "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "",
            "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
        }
    )

    def __init__(
        self,
        category_rules: Optional[list[tuple[str, list[str]]]] = None,
        brand_rules: Optional[list[tuple[str, list[str]]]] = None,
        volume_rules: Optional[list[tuple[str, list[str]]]] = None,
        garbage_words: Optional[list[str]] = None,
        aroma_aliases: Optional[dict[str, list[str]]] = None,
    ):
        dictionary = self._load_dictionary()

        if category_rules is not None:
            self._category_rules = self._coerce_rules(category_rules)
        else:
            self._category_rules = self._merge_rules(
                self._DEFAULT_CATEGORY_RULES,
                self._rules_from_mapping(dictionary.categories),
            )

        self._product_type_rules = self._merge_rules(
            self._DEFAULT_PRODUCT_TYPE_RULES,
            self._rules_from_mapping(dictionary.categories),
        )

        if brand_rules is not None:
            self._brand_rules = self._coerce_rules(brand_rules)
        else:
            self._brand_rules = self._merge_rules(
                self._DEFAULT_BRAND_RULES,
                self._rules_from_mapping(dictionary.brands),
            )
        self._volume_rules = volume_rules or self._DEFAULT_VOLUME_RULES
        self._garbage_words = garbage_words or self._DEFAULT_GARBAGE_WORDS
        if aroma_aliases is not None:
            self._aroma_aliases = aroma_aliases
        else:
            dictionary_aromas = dictionary.aromas if isinstance(getattr(dictionary, "aromas", None), dict) else {}
            self._aroma_aliases = self._merge_alias_dicts(self._DEFAULT_AROMA_ALIASES, dictionary_aromas)
        self._aroma_alias_lookup = self._build_aroma_alias_lookup(self._aroma_aliases)
        self._volume_re = re.compile(
            r"(?<!\d)(\d+(?:[.,]\d+)?)\s*(л|литр|литра|литров|мл|ml|liter|liters|l|кг|kg|г|гр|g|уп|шт)\b",
            re.IGNORECASE,
        )

    @staticmethod
    def _load_dictionary() -> Dictionary:
        try:
            return Dictionary()
        except Exception:
            return Dictionary.__new__(Dictionary)

    @staticmethod
    def _rules_from_mapping(mapping) -> list[tuple[str, list[str]]]:
        if not isinstance(mapping, dict):
            return []
        return [(str(key), [str(v) for v in values]) for key, values in mapping.items()]

    @staticmethod
    def _build_aroma_alias_lookup(aroma_aliases: dict[str, list[str]]) -> dict[str, str]:
        lookup: dict[str, str] = {}
        for canonical, aliases in aroma_aliases.items():
            normalized_canonical = str(canonical).strip().upper()
            preferred = normalized_canonical
            if aliases:
                preferred = str(aliases[0]).strip().upper() or normalized_canonical
            lookup[normalized_canonical.lower()] = preferred
            for alias in aliases:
                key = str(alias).strip().lower()
                if key:
                    lookup[key] = preferred
        return lookup

    def normalize(self, item: ArrivalItem) -> ArrivalItem:
        text = self._clean_text(item.source_name)
        upper = text.upper()

        item.product_type = self._detect_product_type(text)
        item.brand, brand_match = self._detect_brand(text, upper)
        item.category = self._detect_category(text)
        item.volume = self._detect_volume(text)

        if item.brand is None and item.category in {
            "Кондиционер",
            "ЖМС",
            "Гель для душа",
            "Шампунь",
            "Шампунь men",
            "Шампунь women",
            "Шампунь sport",
            "Шампунь органический",
            "Жидкое мыло",
            "Крем-мыло",
            "Мыло",
        }:
            item.brand = "SVO"

        if item.brand:
            candidate = self._cleanup_candidate(text, brand_match, item.product_type)
            if candidate:
                normalized_aroma = self._normalize_aroma(candidate)
                normalized_aroma = self._refine_aroma_for_category(
                    normalized_aroma,
                    item.category,
                    item.brand,
                    text,
                )
                item.variant = normalized_aroma.upper()
                item.aroma = normalized_aroma.upper()

        self._apply_confirmed_price_context(item, text)

        return item

    def _apply_confirmed_price_context(self, item: ArrivalItem, source_text: str) -> None:
        """Apply only confirmed supplier-specific canonical refinements.

        These rules are intentionally narrow: they cover known PRICE/SALES
        representations where the supplier wording differs from the canonical
        MASTER meaning. Generic product-type detection remains unchanged.
        """
        source = re.sub(r"\s+", " ", str(source_text or "")).strip()
        compact = source.upper()

        # SVO conditioner representations that arrive as "gel for washing".
        if (
            re.search(r"^SVO\s+ГЕЛЬ\s+Д/СТИРКИ\s+1\s*Л\b", compact)
            and "FLORAL MIST" in compact
        ):
            item.product_type = "Кондиционер"
            item.category = "Кондиционер"
            item.variant = "FLORAL MIST"
            item.aroma = "FLORAL MIST"
            item.volume = "1 Л"
            return

        if re.search(r"^SVO\s+СМЯГЧИТЕЛЬ\s+5\s*Л\s+ASK\b", compact):
            item.product_type = "Кондиционер"
            item.category = "Кондиционер"
            item.variant = "ASK"
            item.aroma = "ASK"
            item.volume = "5 Л"
            return

        # SVO dishwashing supplier notation: 750 g is canonically 750 ml here.
        if re.search(
            r"^SVO\s+СРЕДСТВО\s+Д/ПОСУДЫ\s+750\s*ГР\b.*(?:ЯБЛОКО|APPLE)",
            compact,
        ):
            item.product_type = "Посуда моющее ср-во"
            item.category = "Посуда моющее ср-во"
            item.variant = "APPLE"
            item.aroma = "APPLE"
            item.volume = "750 МЛ"
            return

        # BOSSFIX diaper packaging: canonical size/pack representation.
        diaper_match = re.search(r"BOSSFIX.*ПОДГУЗ.*?№\s*(\d+)", compact, re.IGNORECASE)
        if diaper_match:
            item.product_type = "Подгузники"
            item.category = "Подгузники"
            item.variant = f"SIZE {diaper_match.group(1)}"
            item.aroma = f"SIZE {diaper_match.group(1)}"
            item.volume = "1 УП"
            return

        # GILAR shampoo canonical subcategories.
        if (
            "GILAR" in compact
            and "ШАМПУН" in compact
            and re.search(r"\b400\s*МЛ\b", compact)
            and re.search(r"МУЖС", compact)
            and "ARGAN OIL" in compact
        ):
            item.product_type = "Шампунь men"
            item.category = "Шампунь men"
            item.variant = "ARGAN OIL"
            item.aroma = "ARGAN OIL"
            item.volume = "400 МЛ"
            return

        if (
            "GILAR" in compact
            and "ШАМПУН" in compact
            and re.search(r"\b500\s*МЛ\b", compact)
            and "ДОЗАТ" in compact
            and "GINSENG" in compact
        ):
            item.product_type = "Шампунь органический"
            item.category = "Шампунь органический"
            item.variant = "GINSENG"
            item.aroma = "GINSENG"
            item.volume = "500 МЛ"
            return

        if (
            "SVO" in compact
            and re.search(r"ГЕЛЬ\s+Д/СТИРКИ\s+2[,.]7\s*Л", compact)
            and "ЖЁЛТЫЙ" in compact
        ):
            item.product_type = "Кондиционер"
            item.category = "Кондиционер"
            item.variant = "VANILLA"
            item.aroma = "VANILLA"
            item.volume = "2,7 Л"
            return

        if (
            "SVO" in compact
            and re.search(r"ГЕЛЬ\s+Д/СТИРКИ\s+2[,.]7\s*Л", compact)
            and "ЧЁРНЫЙ" in compact
        ):
            item.product_type = "Кондиционер"
            item.category = "Кондиционер"
            item.variant = "BLACK"
            item.aroma = "BLACK"
            item.volume = "2,7 Л"
            return

        if (
            re.search(r"^SVO\s+КОНДИЦ\.\s+Д/БЕЛЬЯ\s+2,700\s*МЛ\b", compact)
            and "АРОМАТ СТРАСТИ" in compact
        ):
            item.product_type = "Кондиционер"
            item.category = "Кондиционер"
            item.variant = "BLACK GEL"
            item.aroma = "BLACK GEL"
            item.volume = "2,7 Л"
            return

        if (
            "SVO" in compact
            and re.search(r"ПОРОШ\.\s*СТИР\.\s*5\s*КГ\b", compact)
            and "ШЕЙХ" in compact
        ):
            item.product_type = "Порошок стиральный"
            item.category = "Порошок стиральный"
            item.variant = "MAGINA"
            item.aroma = "MAGINA"
            item.volume = "5 КГ"
            return

        # Confirmed powder variants/colors.
        if (
            "SVO" in compact
            and re.search(r"ПОРОШ\.\s*СТИР\.\s*1,3\s*КГ\b", compact)
            and "РОМАШКА" in compact
            and "DAISY" in compact
            and re.search(r"/\s*12\b", compact)
            and not re.search(r"ДЛЯ\s+ЦВ\.?\s+И\s+БЕЛ", compact)
        ):
            item.variant = "BABY"
            item.aroma = "BABY"
            return

        if (
            "SVO" in compact
            and re.search(r"ПОРОШ\.\s*СТИР\.\s*1,3\s*КГ\b", compact)
            and "РОМАШКА" in compact
            and "DAISY" in compact
            and re.search(r"ДЛЯ\s+ЦВ\.?\s+И\s+БЕЛ", compact)
            and re.search(r"/\s*12\b", compact)
        ):
            item.variant = "COLOR"
            item.aroma = "COLOR"
            return

        if (
            "SVO" in compact
            and re.search(r"ПОРОШ\.\s*СТИР\.\s*9\s*КГ\b", compact)
            and "ПОДСНЕЖНИК" in compact
            and re.search(r"ДЛЯ\s+ЦВ\.?\s+И\s+БЕЛ", compact)
        ):
            item.variant = "SNOWDROP"
            item.aroma = "SNOWDROP"
            return

        if (
            "GILAR" in compact
            and re.search(r"ШАМПУНЬ\s+600\s*МЛ\b", compact)
            and "MENTOL" in compact
        ):
            item.variant = "MINT"
            item.aroma = "MINT"
            return

        if (
            "SVO" in compact
            and re.search(r"ПОРОШ\.\s*СТИР\.\s*4\s*КГ\b", compact)
            and "РОМАШКА" in compact
            and "DAISY" in compact
            and re.search(r"ДЛЯ\s+ЦВ\.?\s+И\s+БЕЛ", compact)
        ):
            item.variant = "COLOR"
            item.aroma = "COLOR"
            return

        if (
            "SVO" in compact
            and re.search(r"ПОРОШ\.\s*СТИР\.\s*6\s*КГ\b", compact)
            and "РОМАШКА" in compact
            and re.search(r"ДЛЯ\s+ЦВЕТНЫХ", compact)
        ):
            item.variant = "COLOR"
            item.aroma = "COLOR"
            return

        if (
            "SVO" in compact
            and re.search(r"ПОРОШ\.\s*СТИР\.?\s*10\s*КГ\b", compact)
            and "РОМАШКА" in compact
            and re.search(r"Д[\\/]\s*ЦВЕТНОГО", compact)
        ):
            item.variant = "COLOR"
            item.aroma = "COLOR"
            return

    def _detect_product_type(self, text: str) -> Optional[str]:
        lower = text.lower()
        for product_type, patterns in self._product_type_rules:
            patterns_to_check = [product_type, *patterns]
            if any(re.search(rf"(?<!\w){re.escape(str(pattern).lower())}(?!\w)", lower) for pattern in patterns_to_check if str(pattern).strip()):
                return product_type
        return None

    @staticmethod
    def _coerce_rules(rules) -> list[tuple[str, list[str]]]:
        if isinstance(rules, dict):
            return [(key, list(value)) for key, value in rules.items()]
        return list(rules)

    @staticmethod
    def _merge_rules(*rule_sets: list[tuple[str, list[str]]]) -> list[tuple[str, list[str]]]:
        merged: dict[str, list[str]] = {}
        for rule_set in rule_sets:
            for canonical, aliases in rule_set:
                key = str(canonical)
                if key not in merged:
                    merged[key] = []
                existing = {alias.lower() for alias in merged[key]}
                for alias in [key, *aliases]:
                    alias_text = str(alias).strip()
                    if not alias_text:
                        continue
                    if alias_text.lower() not in existing:
                        merged[key].append(alias_text)
                        existing.add(alias_text.lower())
        return [(canonical, aliases) for canonical, aliases in merged.items()]

    @staticmethod
    def _merge_alias_dicts(*alias_dicts: dict[str, list[str]]) -> dict[str, list[str]]:
        merged: dict[str, list[str]] = {}
        for alias_dict in alias_dicts:
            if not isinstance(alias_dict, dict):
                continue
            for canonical, aliases in alias_dict.items():
                key = str(canonical).strip()
                if not key:
                    continue
                if key not in merged:
                    merged[key] = []
                existing = {value.lower() for value in merged[key]}
                for value in aliases:
                    alias = str(value).strip()
                    if alias and alias.lower() not in existing:
                        merged[key].append(alias)
                        existing.add(alias.lower())
        return merged

    def _clean_text(self, value: str) -> str:
        text = str(value)
        text = text.replace("\u00a0", " ")
        text = re.sub(r"[’`´']", "", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _detect_brand(self, text: str, upper_text: str) -> tuple[Optional[str], Optional[str]]:
        lower_text = text.lower()
        best_match: tuple[Optional[str], Optional[str], int, int] = (None, None, 10**9, -1)
        for brand, patterns in self._brand_rules:
            patterns_to_check = [brand, *patterns]
            for pattern in patterns_to_check:
                raw = pattern.lower().strip()
                if not raw:
                    continue
                regex = rf"(?<!\w){re.escape(raw)}(?!\w)"
                match = re.search(regex, lower_text)
                if match:
                    start = match.start()
                    pattern_len = len(raw)
                    # Prefer earliest mention in source text, then more specific (longer) alias.
                    if start < best_match[2] or (start == best_match[2] and pattern_len > best_match[3]):
                        best_match = (str(brand).upper(), pattern, start, pattern_len)
        if best_match[0]:
            return best_match[0], best_match[1]
        for brand in (brand for brand, _ in self._brand_rules):
            if brand in upper_text:
                return str(brand).upper(), brand
        return None, None

    def _detect_category(self, text: str) -> Optional[str]:
        lower = text.lower()
        if "подгуз" in lower:
            return "Подгузники"
        if "салфет" in lower and "влаж" in lower:
            return "Салфетки влажные"
        if "известков" in lower and "налет" in lower:
            return "Антинакипь"
        if "жирн" in lower and "пят" in lower:
            return "Антижир"
        if "блок" in lower and "туалет" in lower:
            return "Блок туалетный"
        if "пол" in lower and ("моющ" in lower or "мыть" in lower):
            return "Пол моющее средство"
        if "порош" in lower:
            return "Порошок стиральный"
        if "крем-мыл" in lower or "крем мыл" in lower:
            return "Крем-мыло"
        if "натураль" in lower and "мыл" in lower:
            return "Натуральное мыло"
        if "жидк" in lower and "мыл" in lower:
            return "Жидкое мыло"
        if "мыл" in lower:
            return "Мыло"
        if "посуд" in lower and ("мыть" in lower or "моющ" in lower):
            return "Посуда моющее ср-во"
        if "шампун" in lower or re.search(r"\bshamp(?:oo|un)\b", lower):
            if "sport" in lower:
                return "Шампунь sport"
            if re.search(r"\b(women|lady)\b", lower) or re.search(r"женск", lower):
                return "Шампунь women"
            if re.search(r"\bmen\b", lower) or re.search(r"мужск|мужчин", lower):
                return "Шампунь men"
            if any(token in lower for token in ("organic", "органич")):
                return "Шампунь органический"
            return "Шампунь"
        for category, patterns in self._category_rules:
            patterns_to_check = [category, *patterns]
            if any(re.search(rf"(?<!\w){re.escape(str(pattern).lower())}(?!\w)", lower) for pattern in patterns_to_check if str(pattern).strip()):
                return category
        return None

    def _detect_volume(self, text: str) -> Optional[str]:
        pack_match = re.search(
            r"(?<!\d)(\d+)\s*(?:шт|уп)\.?\s*[*xх×]?\s*(\d+)\s*(?:г|гр)(?!\d)",
            text.lower(),
        )
        if pack_match:
            pack_count = pack_match.group(1)
            grams = pack_match.group(2)
            return f"{pack_count}×{grams} Г"

        match = self._volume_re.search(text.lower())
        if not match:
            decimal_match = re.search(r"(?<!\d)(\d+[.,]\d+)(?!\d)", text.lower())
            if not decimal_match:
                return None

            lowered = text.lower()
            liquid_context = any(
                marker in lowered
                for marker in (
                    "кондиционер",
                    "жмс",
                    "жидкое",
                    "моющее",
                    "посуд",
                    "пол",
                    "гель",
                )
            )
            powder_context = "порош" in lowered

            guessed_value = Decimal(decimal_match.group(1).replace(",", "."))
            if liquid_context:
                return f"{self._format_decimal(guessed_value)} Л"
            if powder_context:
                return f"{self._format_decimal(guessed_value)} КГ"
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
            raw_amount = match.group(1)
            if (
                value < Decimal('10')
                and ("," in raw_amount or "." in raw_amount)
                and len(re.split(r"[.,]", raw_amount, maxsplit=1)[1]) == 3
            ):
                return f"{self._format_decimal(value)} Л"
            return f"{self._format_decimal(value / Decimal('1000'))} Л" if value >= Decimal('1000') else f"{self._format_decimal(value)} МЛ"
        if normalized_unit == "кг":
            return f"{self._format_decimal(value)} КГ"
        if normalized_unit == "г":
            return f"{self._format_decimal(value)} Г"
        return f"{self._format_decimal(value)} УП"

    def _cleanup_candidate(
        self,
        candidate: str,
        brand_match: Optional[str] = None,
        product_type: Optional[str] = None,
    ) -> Optional[str]:
        cleaned = self._volume_re.sub("", candidate)
        cleaned = re.sub(r"[()\[\]{}]", " ", cleaned)
        cleaned = re.sub(r"\bдля\s+мытья\s+посуды\b", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bмоющее\s+средство\b", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bсредство\s+для\s+мытья\s+посуды\b", " ", cleaned, flags=re.IGNORECASE)
        removal_terms = []
        if brand_match:
            removal_terms.append(brand_match)
        for _, patterns in self._brand_rules:
            removal_terms.extend(patterns)
        for _, patterns in self._category_rules:
            removal_terms.extend(patterns)
        if product_type:
            removal_terms.append(product_type)
            for canonical, patterns in self._product_type_rules:
                if canonical == product_type:
                    removal_terms.extend(patterns)
                    break
        removal_terms.extend(["shampoo", "shampun"])
        for term in sorted(set(removal_terms), key=len, reverse=True):
            cleaned = re.sub(
                rf"\b{re.escape(term)}\b",
                "",
                cleaned,
                flags=re.IGNORECASE,
            )
        for garbage_word in self._garbage_words:
            cleaned = re.sub(
                rf"\b{re.escape(garbage_word)}\b",
                "",
                cleaned,
                flags=re.IGNORECASE,
            )
        cleaned = " ".join(cleaned.replace(",", " ").split()).strip()
        cleaned = re.sub(r"\b\d+[.,]?\d*\b", " ", cleaned)
        cleaned = " ".join(cleaned.split()).strip()
        return cleaned if cleaned else None

    def _normalize_aroma(self, candidate: str) -> str:
        normalized = []
        seen = set()
        for token in re.split(r"\s+", candidate.strip()):
            lowered = token.lower().strip(".,;:-+/\\")
            if not lowered:
                continue
            if lowered in self._AROMA_STOP_TOKENS:
                continue
            if any(garbage in lowered for garbage in self._garbage_words):
                continue
            mapped = self._aroma_alias_lookup.get(lowered)
            normalized_token = mapped or self._canonical_aroma_token(lowered)
            if len(normalized_token) < 3:
                continue
            if normalized_token not in seen:
                normalized.append(normalized_token)
                seen.add(normalized_token)
        return " ".join(normalized).strip()

    def _refine_aroma_for_category(
        self,
        aroma: str,
        category: Optional[str],
        brand: Optional[str],
        source_text: str,
    ) -> str:
        source_lower = source_text.lower()

        if (
            not aroma
            and category == "Натуральное мыло"
            and brand == "GILAR"
            and "масл" in source_lower
        ):
            return "ARGAN OIL"

        if (
            not aroma
            and category == "ЖМС"
            and brand == "SVO ELEGANT"
            and "bossfix" in source_lower
        ):
            return "VELVET"

        if not aroma:
            return aroma
        tokens = [token for token in aroma.split() if token]
        token_set = set(tokens)

        if category == "Кондиционер":
            # ROMANTIK is a supplier shorthand that always means the
            # canonical variant ROMANTIK ROSE.  The volume remains
            # independent and must be resolved separately by the matcher.
            if "ROMANTIK" in token_set:
                return "ROMANTIK ROSE"
            return " ".join(tokens)

        if category != "Порошок стиральный":
            return aroma

        token_set = set(tokens)
        has_specific_variant = "BABY" in token_set or ("PASSION" in token_set and "FRUIT" in token_set)
        if "COLOR" in token_set and has_specific_variant:
            tokens = [token for token in tokens if token != "COLOR"]
        return " ".join(tokens)

    def _canonical_aroma_token(self, token: str) -> str:
        token = token.lower().translate(self._CYR_TO_LAT)
        token = re.sub(r"[^a-z0-9]", "", token)

        for suffix in (
            "ovogo", "evogo", "iyami", "yami", "ami", "ogo", "ego", "omu", "emu",
            "aya", "iya", "oe", "ee", "ye", "iy", "yy", "yi", "oi", "ai", "am", "yam",
            "ah", "yah", "ov", "ev", "om", "em", "iyu", "uyu", "yu", "ya", "yi", "ie",
            "ye", "oy", "iy", "yj", "yh", "y", "a", "e", "i", "o", "u",
        ):
            if len(token) > len(suffix) + 2 and token.endswith(suffix):
                token = token[: -len(suffix)]
                break

        for suffix in ("ings", "ing", "ness", "ment", "edly", "edly", "ed", "ies", "es", "s"):
            if len(token) > len(suffix) + 2 and token.endswith(suffix):
                token = token[: -len(suffix)]
                break

        return token.upper()

    @staticmethod
    def _format_decimal(value: Decimal) -> str:
        if value == value.to_integral_value():
            return str(int(value))
        text = format(value.normalize(), "f")
        text = text.rstrip("0").rstrip(".")
        return text.replace(".", ",")
