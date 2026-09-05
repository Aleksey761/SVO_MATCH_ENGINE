import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import yaml

from .models import ArrivalItem


@dataclass
class CanonicalRevisionName:
    category: str | None
    brand: str | None
    variant: str | None
    volume: str | None

    @property
    def master_name(self) -> str:
        parts = [self.category, self.brand, self.variant, self.volume]
        return " ".join(str(part).strip() for part in parts if str(part or "").strip())


class RevisionNameCanonicalizer:
    """Converts REVISION product text into a canonical MASTER-like naming shape."""

    _CONFIG_DIR = Path(__file__).resolve().parent.parent / "config" / "canonicalization"

    def __init__(self) -> None:
        marketing_cfg = self._load_yaml("marketing_words.yaml")
        brand_cfg = self._load_yaml("brand_alias.yaml")
        category_cfg = self._load_yaml("category_alias.yaml")
        aroma_cfg = self._load_yaml("aroma_alias.yaml")
        color_cfg = self._load_yaml("color_alias.yaml")
        volume_cfg = self._load_yaml("volume_alias.yaml")

        self._marketing_words = self._normalize_word_list(marketing_cfg.get("words", []))
        self._title_case_lower_words = {
            str(token).strip().lower()
            for token in marketing_cfg.get("title_case_lower_words", [])
            if str(token).strip()
        }

        self._brand_aliases = self._normalize_alias_mapping(brand_cfg.get("aliases", {}))
        self._category_aliases = self._normalize_alias_mapping(category_cfg.get("aliases", {}))
        self._default_brand_categories = {
            str(value).strip()
            for value in brand_cfg.get("default_brand_by_category", [])
            if str(value).strip()
        }
        self._default_brand = str(brand_cfg.get("default_brand", "")).strip().upper()

        self._aroma_aliases = self._normalize_expansion_mapping(aroma_cfg.get("aliases", {}))
        self._color_aliases = self._normalize_expansion_mapping(color_cfg.get("aliases", {}))

        self._volume_units_by_alias, self._volume_re = self._build_volume_tools(volume_cfg)
        normalize_to = volume_cfg.get("normalize_to", {}) if isinstance(volume_cfg, dict) else {}
        self._liters_threshold = Decimal(str(normalize_to.get("liters_threshold")))
        self._liters_canonical = str(normalize_to.get("liters_canonical")).strip().upper()
        self._milliliters_canonical = str(normalize_to.get("milliliters_canonical")).strip().upper()

    @classmethod
    def _load_yaml(cls, filename: str) -> dict:
        path = cls._CONFIG_DIR / filename
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        if not isinstance(data, dict):
            raise ValueError(f"Canonicalization config must be a mapping: {path}")
        return data

    @staticmethod
    def _normalize_word_list(values) -> tuple[str, ...]:
        words = [str(value).strip().upper() for value in values if str(value).strip()]
        return tuple(sorted(words, key=len, reverse=True))

    @staticmethod
    def _normalize_alias_mapping(mapping) -> tuple[tuple[str, tuple[str, ...]], ...]:
        if not isinstance(mapping, dict):
            return tuple()

        pairs: list[tuple[str, tuple[str, ...]]] = []
        for canonical, aliases in mapping.items():
            canonical_text = str(canonical).strip()
            if not canonical_text:
                continue

            alias_values = [canonical_text]
            if isinstance(aliases, list):
                alias_values.extend(str(value).strip() for value in aliases if str(value).strip())

            alias_upper = tuple(sorted({value.upper() for value in alias_values}, key=len, reverse=True))
            pairs.append((canonical_text, alias_upper))

        return tuple(pairs)

    @staticmethod
    def _normalize_expansion_mapping(mapping) -> tuple[tuple[str, tuple[str, ...]], ...]:
        if not isinstance(mapping, dict):
            return tuple()

        pairs: list[tuple[str, tuple[str, ...]]] = []
        for source, targets in mapping.items():
            source_text = str(source).strip().upper()
            if not source_text:
                continue
            values: list[str] = []
            if isinstance(targets, list):
                values = [str(value).strip().upper() for value in targets if str(value).strip()]
            pairs.append((source_text, tuple(values)))

        pairs.sort(key=lambda item: len(item[0]), reverse=True)
        return tuple(pairs)

    @classmethod
    def _build_volume_tools(cls, volume_cfg: dict) -> tuple[dict[str, dict], re.Pattern]:
        units_by_alias: dict[str, dict] = {}
        aliases_for_pattern: list[str] = []

        for unit in volume_cfg.get("units", []) if isinstance(volume_cfg, dict) else []:
            if not isinstance(unit, dict):
                continue

            canonical = str(unit.get("canonical", "")).strip().upper()
            scale_to_liters = Decimal(str(unit.get("scale_to_liters", 1)))
            aliases = unit.get("aliases", [])
            if not canonical or not isinstance(aliases, list):
                continue

            for alias in aliases:
                alias_text = str(alias).strip().upper()
                if not alias_text:
                    continue
                units_by_alias[alias_text] = {
                    "canonical": canonical,
                    "scale_to_liters": scale_to_liters,
                }
                aliases_for_pattern.append(re.escape(alias_text))

        if not aliases_for_pattern:
            volume_re = re.compile(r"$^")
        else:
            aliases_for_pattern.sort(key=len, reverse=True)
            volume_re = re.compile(
                rf"(?<!\d)(\d+(?:[.,]\d+)?)\s*({'|'.join(aliases_for_pattern)})(?!\d)",
                re.IGNORECASE,
            )

        return units_by_alias, volume_re

    @staticmethod
    def _clean_text(value: str) -> str:
        text = str(value or "").replace("\u00a0", " ")
        text = re.sub(r"[’`´']", "", text)
        text = re.sub(r"[()\[\],.;:+*/\\-]", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip().upper()

    @staticmethod
    def _format_decimal(value: Decimal) -> str:
        text = format(value.normalize(), "f")
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return text

    def _extract_volume(self, text: str) -> tuple[str | None, str]:
        match = self._volume_re.search(text)
        if not match:
            return None, text

        value = Decimal(match.group(1).replace(",", "."))
        unit = match.group(2).upper().strip()
        unit_info = self._volume_units_by_alias.get(unit)
        if unit_info is None:
            volume = None
        else:
            canonical = str(unit_info["canonical"]).upper()
            scale_to_liters = Decimal(str(unit_info["scale_to_liters"]))
            value_in_liters = value * scale_to_liters

            if canonical == self._liters_canonical or scale_to_liters == Decimal("1"):
                volume = f"{self._format_decimal(value_in_liters)} {self._liters_canonical}"
            elif canonical == self._milliliters_canonical and value >= self._liters_threshold:
                volume = f"{self._format_decimal(value_in_liters)} {self._liters_canonical}"
            else:
                volume = f"{self._format_decimal(value)} {canonical}"

        text_wo_volume = (text[: match.start()] + " " + text[match.end() :]).strip()
        text_wo_volume = re.sub(r"\s+", " ", text_wo_volume)
        return volume, text_wo_volume

    def _extract_category(self, text: str) -> str | None:
        for canonical, aliases in self._category_aliases:
            if any(alias in text for alias in aliases):
                return canonical
        return None

    def _extract_brand(self, text: str, category: str | None) -> str | None:
        for canonical, aliases in self._brand_aliases:
            if any(alias in text for alias in aliases):
                return canonical.upper()

        if category in self._default_brand_categories:
            if self._default_brand:
                return self._default_brand

        return None

    def _strip_known_tokens(self, text: str, category: str | None, brand: str | None) -> str:
        result = f" {text} "

        for phrase in self._marketing_words:
            result = result.replace(f" {phrase} ", " ")

        if category:
            for canonical, aliases in self._category_aliases:
                if canonical == category:
                    for token in aliases:
                        result = result.replace(f" {token} ", " ")
                    break

        if brand:
            for canonical, aliases in self._brand_aliases:
                if canonical.upper() == brand.upper():
                    for token in aliases:
                        result = result.replace(f" {token} ", " ")
                    break

        for source, targets in self._aroma_aliases:
            if source in result:
                additions = " ".join(targets).strip()
                if additions:
                    result = result.replace(source, f"{source} {additions}")

        for source, targets in self._color_aliases:
            if source in result:
                additions = " ".join(targets).strip()
                if additions:
                    result = result.replace(source, f"{source} {additions}")

        result = re.sub(r"\b\d+\b", " ", result)
        result = re.sub(r"\s+", " ", result)
        return result.strip()

    def _apply_title_case(self, text: str | None) -> str | None:
        if not text:
            return None
        words = []
        for token in text.split():
            if token.lower() in self._title_case_lower_words:
                words.append(token.lower())
            elif token.isupper() and len(token) <= 4:
                words.append(token)
            else:
                words.append(token.capitalize())
        return " ".join(words)

    def canonicalize(self, source_name: str) -> CanonicalRevisionName:
        cleaned = self._clean_text(source_name)
        volume, text = self._extract_volume(cleaned)
        category = self._extract_category(text)
        brand = self._extract_brand(text, category)
        variant_raw = self._strip_known_tokens(text, category, brand)

        # Keep only alpha-numeric words after aggressive cleanup.
        variant_raw = re.sub(r"[^A-ZА-Я0-9 ]+", " ", variant_raw)
        variant_raw = re.sub(r"\s+", " ", variant_raw).strip()
        variant = self._apply_title_case(variant_raw) if variant_raw else None

        if brand:
            brand = brand.upper()

        return CanonicalRevisionName(
            category=category,
            brand=brand,
            variant=variant,
            volume=volume,
        )

    def apply(self, item: ArrivalItem) -> ArrivalItem:
        original_source_name = str(item.source_name or "").strip()
        canonical = self.canonicalize(item.source_name)
        item.ProductName = getattr(item, "ProductName", None) or original_source_name
        item.canonical_master_name = canonical.master_name

        if canonical.category and not getattr(item, "category", None):
            item.category = canonical.category
        if canonical.brand and not getattr(item, "brand", None):
            item.brand = canonical.brand
        if canonical.variant and not (getattr(item, "variant", None) or getattr(item, "aroma", None)):
            item.variant = canonical.variant.upper()
            item.aroma = canonical.variant.upper()
        if canonical.volume and not getattr(item, "volume", None):
            item.volume = canonical.volume

        if canonical.master_name:
            original_upper = original_source_name.upper()
            canonical_upper = canonical.master_name.upper()
            if original_source_name and canonical_upper not in original_upper:
                item.source_name = f"{original_source_name} {canonical.master_name}"
            elif not original_source_name:
                item.source_name = canonical.master_name

        return item

    def apply_all(self, items: list[ArrivalItem]) -> list[ArrivalItem]:
        return [self.apply(item) for item in items]
