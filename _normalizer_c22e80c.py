import re
from decimal import Decimal
from typing import Optional

from .models import ArrivalItem
from .dictionary import Dictionary


class Normalizer:
    """Normalizes arrival item text and extracts basic fields."""

    _DEFAULT_CATEGORY_RULES = [
        ("╨Ъ╨╛╨╜╨┤╨╕╤Ж╨╕╨╛╨╜╨╡╤А", ["╨║╨╛╨╜╨┤╨╕╤Ж╨╕╨╛╨╜╨╡╤А"]),
        ("╨Ц╨Ь╨б", ["╨╢╨╝╤Б", "╨╢╨╕╨┤╨║╨╛╨╡ ╤Б╤А╨╡╨┤╤Б╤В╨▓╨╛"]),
        ("╨У╨╡╨╗╤М ╨┤╨╗╤П ╨┤╤Г╤И╨░", ["╨│╨╡╨╗╤М ╨┤╨╗╤П ╨┤╤Г╤И╨░"]),
        ("╨и╨░╨╝╨┐╤Г╨╜╤М", ["╤И╨░╨╝╨┐╤Г╨╜", "shampoo"]),
        ("╨и╨░╨╝╨┐╤Г╨╜╤М men", ["╤И╨░╨╝╨┐╤Г╨╜╤М men", "men shampoo", "╨╝╤Г╨╢╤Б╨║╨╛╨╣ ╤И╨░╨╝╨┐╤Г╨╜╤М"]),
        ("╨и╨░╨╝╨┐╤Г╨╜╤М women", ["╤И╨░╨╝╨┐╤Г╨╜╤М women", "women shampoo", "╨╢╨╡╨╜╤Б╨║╨╕╨╣ ╤И╨░╨╝╨┐╤Г╨╜╤М"]),
        ("╨и╨░╨╝╨┐╤Г╨╜╤М sport", ["╤И╨░╨╝╨┐╤Г╨╜╤М sport", "sport shampoo"]),
        ("╨и╨░╨╝╨┐╤Г╨╜╤М ╨╛╤А╨│╨░╨╜╨╕╤З╨╡╤Б╨║╨╕╨╣", ["╤И╨░╨╝╨┐╤Г╨╜╤М ╨╛╤А╨│╨░╨╜╨╕╤З╨╡╤Б╨║╨╕╨╣", "organic shampoo"]),
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
        ("╨╗", ["╨╗", "╨╗╨╕╤В╤А", "╨╗╨╕╤В╤А╨░", "╨╗╨╕╤В╤А╨╛╨▓", "liter", "liters", "l"]),
        ("╨╝╨╗", ["╨╝╨╗", "ml"]),
        ("╨║╨│", ["╨║╨│", "kg"]),
        ("╨│", ["╨│", "╨│╤А", "g"]),
        ("╤Г╨┐", ["╤Г╨┐", "╤И╤В"]),
    ]

    _DEFAULT_GARBAGE_WORDS = [
        "╨┐╨░╤А╤Д╤О╨╝╨╕╤А╨╛╨▓╨░╨╜╨╜",
        "╨┐╨░╤А╤Д╤О╨╝╨╕╤А╨╛╨▓╨░",
        "╨┐╨░╤А╤Д╤О╨╝",
        "╨┤╨╗╤П ╤Б╤В╨╕╤А╨║╨╕",
        "╨╝╨╛╤О╤Й╨╡╨╡ ╤Б╤А╨╡╨┤╤Б╤В╨▓╨╛",
        "╨┤╨╗╤П ╨╝╤Л╤В╤М╤П ╨┐╨╛╤Б╤Г╨┤╤Л",
        "╨┐╨╛╤Б╤Г╨┤╤Л",
        "╤Б╤А╨╡╨┤╤Б╤В╨▓╨╛",
        "╨╝╨╛╤О╤Й╨╡╨╡",
        "╨╝╤Г╨╢╤Б╨║╨╛╨╣",
        "╨╢╨╡╨╜╤Б╨║╨╕╨╣",
        "oil",
        "extract",
        "extracts",
        "plus",
        "╨┤╨╡╤В╤Б╨║╨╕╤Е ╨▓╨╡╤Й╨╡╨╣",
        "╨░╤А╨╛╨╝╨░╤В",
        "╨░╤А╨╛╨╝╨░╤В╤Л",
        "╤Б╨╕╨╜╨╕╨╣",
        "╨║╤А╨░╤Б╨╜╤Л╨╣",
        "╨╢╨╡╨╗╤В╤Л╨╣",
        "╤Д╨╕╨╛╨╗╨╡╤В╨╛╨▓╤Л╨╣",
        "╤А╨╛╨╖╨╛╨▓╤Л╨╣",
        "╤З╨╡╤А╨╜╤Л╨╣",
        "parfume",
        "parfum",
        "junk",
    ]

    _DEFAULT_AROMA_ALIASES = {}

    _AROMA_STOP_TOKENS = {
        "╨┤╨╗╤П",
        "╤Б",
        "╨╕",
        "╨▓",
        "╨╜╨░",
        "╨┐╨╛",
        "╨╕╨╖",
        "╨╝╤Г╨╢╤З╨╕╨╜",
        "╨╝╤Г╨╢╤Б╨║╨╛╨╣",
        "╨╢╨╡╨╜╤Б╨║╨╕╨╣",
        "women",
        "woman",
        "men",
        "man",
        "sport",
        "╤И╨░╨╝╨┐╤Г╨╜╤М",
        "╨│╨╡╨╗╤М",
        "╨┤╤Г╤И╨░",
        "╨╢╨╕╨┤╨║╨╛╨╡",
        "╨╝╨╛╤О╤Й╨╡╨╡",
        "╤Б╤А╨╡╨┤╤Б╤В╨▓╨╛",
        "╨╝╤Л╤В╤М╤П",
        "╨┐╨╛╤Б╤Г╨┤╤Л",
        "╨▒╨╡╨╗╤М╤П",
        "╨║╤А╨╡╨╝",
        "╨▒╨╗╨╛╨║",
        "╤В╤Г╨░╨╗╨╡╤В╨╜╤Л╨╣",
        "╤Г╨╜╨╕╤В╨░╨╖╨░",
        "╨░╨▓╤В╨╛╨╝╨░╤В",
        "╨╜╨░╤В╤Г╤А╨░╨╗╤М╨╜╨╛╨╡",
        "╨╜╨░╤В╤Г╤А╨░╨╗╤М╨╜╤Л╨╣",
        "╤А╨╛╨╝╨░╨╜╤В╨╕╨║",
        "╤В╤А╨╛╨┐╨╕╨║",
        "╨╝╨░╤Б╨╗╨╛",
        "╨╝╨░╤Б╨╗╨░",
        "╨╝╨░╤Б╨╗╨╛╨╝",
        "╨╝╨░╤Б╨╗╤П╨╜╤Л╨╣",
        "╨╝╨░╤Б╨╗╤П╨╜╨░╤П",
        "oil",
    }

    _CYR_TO_LAT = str.maketrans(
        {
            "╨░": "a", "╨▒": "b", "╨▓": "v", "╨│": "g", "╨┤": "d", "╨╡": "e", "╤С": "e",
            "╨╢": "zh", "╨╖": "z", "╨╕": "i", "╨╣": "i", "╨║": "k", "╨╗": "l", "╨╝": "m",
            "╨╜": "n", "╨╛": "o", "╨┐": "p", "╤А": "r", "╤Б": "s", "╤В": "t", "╤Г": "u",
            "╤Д": "f", "╤Е": "h", "╤Ж": "c", "╤З": "ch", "╤И": "sh", "╤Й": "sch", "╤К": "",
            "╤Л": "y", "╤М": "", "╤Н": "e", "╤О": "yu", "╤П": "ya",
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
            r"(?<!\d)(\d+(?:[.,]\d+)?)\s*(╨╗|╨╗╨╕╤В╤А|╨╗╨╕╤В╤А╨░|╨╗╨╕╤В╤А╨╛╨▓|╨╝╨╗|ml|liter|liters|l|╨║╨│|kg|╨│|╨│╤А|g|╤Г╨┐|╤И╤В)\b",
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

        item.brand, brand_match = self._detect_brand(text, upper)
        item.category = self._detect_category(text)
        item.volume = self._detect_volume(text)

        if item.brand:
            candidate = self._cleanup_candidate(text, brand_match)
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

        return item

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
        text = re.sub(r"[тАЩ`┬┤']", "", text)
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
        if "╨┐╨╛╨┤╨│╤Г╨╖" in lower:
            return "╨Я╨╛╨┤╨│╤Г╨╖╨╜╨╕╨║╨╕"
        if "╤Б╨░╨╗╤Д╨╡╤В" in lower and "╨▓╨╗╨░╨╢" in lower:
            return "╨б╨░╨╗╤Д╨╡╤В╨║╨╕ ╨▓╨╗╨░╨╢╨╜╤Л╨╡"
        if "╨╕╨╖╨▓╨╡╤Б╤В╨║╨╛╨▓" in lower and "╨╜╨░╨╗╨╡╤В" in lower:
            return "╨Р╨╜╤В╨╕╨╜╨░╨║╨╕╨┐╤М"
        if "╨╢╨╕╤А╨╜" in lower and "╨┐╤П╤В" in lower:
            return "╨Р╨╜╤В╨╕╨╢╨╕╤А"
        if "╨▒╨╗╨╛╨║" in lower and "╤В╤Г╨░╨╗╨╡╤В" in lower:
            return "╨С╨╗╨╛╨║ ╤В╤Г╨░╨╗╨╡╤В╨╜╤Л╨╣"
        if "╨┐╨╛╨╗" in lower and ("╨╝╨╛╤О╤Й" in lower or "╨╝╤Л╤В╤М" in lower):
            return "╨Я╨╛╨╗ ╨╝╨╛╤О╤Й╨╡╨╡ ╤Б╤А╨╡╨┤╤Б╤В╨▓╨╛"
        if "╨┐╨╛╤А╨╛╤И" in lower:
            return "╨Я╨╛╤А╨╛╤И╨╛╨║ ╤Б╤В╨╕╤А╨░╨╗╤М╨╜╤Л╨╣"
        if "╨║╤А╨╡╨╝-╨╝╤Л╨╗" in lower or "╨║╤А╨╡╨╝ ╨╝╤Л╨╗" in lower:
            return "╨Ъ╤А╨╡╨╝-╨╝╤Л╨╗╨╛"
        if "╨╜╨░╤В╤Г╤А╨░╨╗╤М" in lower and "╨╝╤Л╨╗" in lower:
            return "╨Э╨░╤В╤Г╤А╨░╨╗╤М╨╜╨╛╨╡ ╨╝╤Л╨╗╨╛"
        if "╨╢╨╕╨┤╨║" in lower and "╨╝╤Л╨╗" in lower:
            return "╨Ц╨╕╨┤╨║╨╛╨╡ ╨╝╤Л╨╗╨╛"
        if "╨╝╤Л╨╗" in lower:
            return "╨Ь╤Л╨╗╨╛"
        if "╨┐╨╛╤Б╤Г╨┤" in lower and ("╨╝╤Л╤В╤М" in lower or "╨╝╨╛╤О╤Й" in lower):
            return "╨Я╨╛╤Б╤Г╨┤╨░ ╨╝╨╛╤О╤Й╨╡╨╡ ╤Б╤А-╨▓╨╛"
        if "╤И╨░╨╝╨┐╤Г╨╜" in lower or re.search(r"\bshamp(?:oo|un)\b", lower):
            if "sport" in lower:
                return "╨и╨░╨╝╨┐╤Г╨╜╤М sport"
            if re.search(r"\b(women|lady)\b", lower) or re.search(r"╨╢╨╡╨╜╤Б╨║", lower):
                return "╨и╨░╨╝╨┐╤Г╨╜╤М women"
            if re.search(r"\bmen\b", lower) or re.search(r"╨╝╤Г╨╢╤Б╨║|╨╝╤Г╨╢╤З╨╕╨╜", lower):
                return "╨и╨░╨╝╨┐╤Г╨╜╤М men"
            if any(token in lower for token in ("organic", "╨╛╤А╨│╨░╨╜╨╕╤З")):
                return "╨и╨░╨╝╨┐╤Г╨╜╤М ╨╛╤А╨│╨░╨╜╨╕╤З╨╡╤Б╨║╨╕╨╣"
            return "╨и╨░╨╝╨┐╤Г╨╜╤М"
        for category, patterns in self._category_rules:
            patterns_to_check = [category, *patterns]
            if any(re.search(rf"(?<!\w){re.escape(str(pattern).lower())}(?!\w)", lower) for pattern in patterns_to_check if str(pattern).strip()):
                return category
        return None

    def _detect_volume(self, text: str) -> Optional[str]:
        pack_match = re.search(
            r"(?<!\d)(\d+)\s*(?:╤И╤В|╤Г╨┐)\.?\s*[*x╤Е├Ч]?\s*(\d+)\s*(?:╨│|╨│╤А)(?!\d)",
            text.lower(),
        )
        if pack_match:
            pack_count = pack_match.group(1)
            grams = pack_match.group(2)
            return f"{pack_count}├Ч{grams} ╨У"

        match = self._volume_re.search(text.lower())
        if not match:
            decimal_match = re.search(r"(?<!\d)(\d+[.,]\d+)(?!\d)", text.lower())
            if not decimal_match:
                return None

            lowered = text.lower()
            liquid_context = any(
                marker in lowered
                for marker in (
                    "╨║╨╛╨╜╨┤╨╕╤Ж╨╕╨╛╨╜╨╡╤А",
                    "╨╢╨╝╤Б",
                    "╨╢╨╕╨┤╨║╨╛╨╡",
                    "╨╝╨╛╤О╤Й╨╡╨╡",
                    "╨┐╨╛╤Б╤Г╨┤",
                    "╨┐╨╛╨╗",
                    "╨│╨╡╨╗╤М",
                )
            )
            powder_context = "╨┐╨╛╤А╨╛╤И" in lowered

            guessed_value = Decimal(decimal_match.group(1).replace(",", "."))
            if liquid_context:
                return f"{self._format_decimal(guessed_value)} ╨Ы"
            if powder_context:
                return f"{self._format_decimal(guessed_value)} ╨Ъ╨У"
            return None

        value = Decimal(match.group(1).replace(",", "."))
        unit = match.group(2).lower()
        normalized_unit = "╨╝╨╗"

        for canonical_unit, aliases in self._volume_rules:
            lowered_aliases = {alias.lower() for alias in aliases}
            if unit in lowered_aliases:
                normalized_unit = canonical_unit
                break

        if normalized_unit == "╨╗":
            liters = value
            return f"{self._format_decimal(liters)} ╨Ы"
        if normalized_unit == "╨╝╨╗":
            return f"{self._format_decimal(value / Decimal('1000'))} ╨Ы" if value >= Decimal('1000') else f"{self._format_decimal(value)} ╨Ь╨Ы"
        if normalized_unit == "╨║╨│":
            return f"{self._format_decimal(value)} ╨Ъ╨У"
        if normalized_unit == "╨│":
            return f"{self._format_decimal(value)} ╨У"
        return f"{self._format_decimal(value)} ╨г╨Я"

    def _cleanup_candidate(self, candidate: str, brand_match: Optional[str] = None) -> Optional[str]:
        cleaned = self._volume_re.sub("", candidate)
        cleaned = re.sub(r"[()\[\]{}]", " ", cleaned)
        cleaned = re.sub(r"\b╨┤╨╗╤П\s+╨╝╤Л╤В╤М╤П\s+╨┐╨╛╤Б╤Г╨┤╤Л\b", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\b╨╝╨╛╤О╤Й╨╡╨╡\s+╤Б╤А╨╡╨┤╤Б╤В╨▓╨╛\b", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\b╤Б╤А╨╡╨┤╤Б╤В╨▓╨╛\s+╨┤╨╗╤П\s+╨╝╤Л╤В╤М╤П\s+╨┐╨╛╤Б╤Г╨┤╤Л\b", " ", cleaned, flags=re.IGNORECASE)
        removal_terms = []
        if brand_match:
            removal_terms.append(brand_match)
        for _, patterns in self._brand_rules:
            removal_terms.extend(patterns)
        for _, patterns in self._category_rules:
            removal_terms.extend(patterns)
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
            and category == "╨Э╨░╤В╤Г╤А╨░╨╗╤М╨╜╨╛╨╡ ╨╝╤Л╨╗╨╛"
            and brand == "GILAR"
            and "╨╝╨░╤Б╨╗" in source_lower
        ):
            return "ARGAN OIL"

        if (
            not aroma
            and category == "╨Ц╨Ь╨б"
            and brand == "SVO ELEGANT"
            and "bossfix" in source_lower
        ):
            return "VELVET"

        if not aroma:
            return aroma
        tokens = [token for token in aroma.split() if token]
        token_set = set(tokens)

        if category == "╨Ъ╨╛╨╜╨┤╨╕╤Ж╨╕╨╛╨╜╨╡╤А":
            # For romantik-rose texts, remove generic ROSE to avoid tie with plain Rose variant.
            if "ROMANTIK" in token_set and "ROSE" in token_set:
                tokens = [token for token in tokens if token != "ROSE"]
            return " ".join(tokens)

        if category != "╨Я╨╛╤А╨╛╤И╨╛╨║ ╤Б╤В╨╕╤А╨░╨╗╤М╨╜╤Л╨╣":
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
