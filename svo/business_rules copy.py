from __future__ import annotations

from dataclasses import dataclass
import re

from .models import ArrivalItem, MasterItem


@dataclass
class BusinessRules:
    master_items: list[MasterItem]

    def apply(self, items: list[ArrivalItem]) -> None:
        for item in items:
            if item.status != "REVIEW":
                continue

            if self._is_bundle_product(item):
                # Explicitly keep bundle-like products in REVIEW.
                continue

            if self._apply_lotos_rule(item):
                continue

            if self._apply_botanic_rule(item):
                continue

            self._apply_bossfix_diapers_rule(item)

    @staticmethod
    def _normalize(value: object) -> str:
        return str(value or "").strip().upper()

    @staticmethod
    def _has_no_volume_reason(item: ArrivalItem) -> bool:
        return any(str(reason).strip().upper() == "NO_VOLUME" for reason in item.review_reasons)

    def _is_bundle_product(self, item: ArrivalItem) -> bool:
        text = self._normalize(item.source_name)
        return any(keyword in text for keyword in ("СБОРКА", "КОМПЛЕКТ", "НАБОР"))

    def _apply_lotos_rule(self, item: ArrivalItem) -> bool:
        if not self._has_no_volume_reason(item):
            return False

        text = self._normalize(item.source_name)
        if "LOTOS" not in text and "ЛОТОС" not in text:
            return False

        candidate_skus = {self._normalize(candidate.sku) for candidate in item.candidates}
        if candidate_skus != {"SKU-035", "SKU-064"}:
            return False

        target = self._master_by_sku("SKU-064")
        if target is None:
            return False

        self._promote_match(item, target)
        return True

    def _apply_botanic_rule(self, item: ArrivalItem) -> bool:
        if not self._has_no_volume_reason(item):
            return False

        text = " ".join(
            [
                self._normalize(item.source_name),
                self._normalize(item.variant),
            ]
        )
        if "BOTANIC" not in text:
            return False

        target = self._find_botanic_144(item)
        if target is None:
            return False

        self._promote_match(item, target)
        return True

    def _apply_bossfix_diapers_rule(self, item: ArrivalItem) -> bool:
        if not self._has_no_volume_reason(item):
            return False

        category = self._normalize(item.category)
        brand = self._normalize(item.brand)
        if "ПОДГУЗНИК" not in category or brand != "BOSSFIX":
            return False

        variant_text = " ".join(
            [
                self._normalize(item.source_name),
                self._normalize(item.variant),
                self._normalize(item.volume),
            ]
        )
        has_explicit_size = bool(re.search(r"(SIZE|РАЗМЕР)\s*\d+", variant_text))
        if has_explicit_size:
            return False

        target = self._find_bossfix_size1()
        if target is None:
            return False

        self._promote_match(item, target)
        return True

    def _master_by_sku(self, sku: str) -> MasterItem | None:
        expected = self._normalize(sku)
        for item in self.master_items:
            if self._normalize(item.sku) == expected:
                return item
        return None

    def _find_botanic_144(self, source_item: ArrivalItem) -> MasterItem | None:
        source_category = self._normalize(source_item.category)

        filtered: list[MasterItem] = []
        for item in self.master_items:
            variant = self._normalize(item.variant)
            volume = self._normalize(item.volume).replace(".", ",")
            category = self._normalize(item.category)
            if "BOTANIC" not in variant:
                continue
            if "1,44" not in volume:
                continue
            if source_category and category and source_category != category:
                continue
            filtered.append(item)

        if not filtered:
            return None
        return sorted(filtered, key=lambda value: value.sku)[0]

    def _find_bossfix_size1(self) -> MasterItem | None:
        for item in self.master_items:
            category = self._normalize(item.category)
            brand = self._normalize(item.brand)
            variant = self._normalize(item.variant)
            if "ПОДГУЗНИК" not in category:
                continue
            if brand != "BOSSFIX":
                continue
            if "SIZE 1" in variant or "РАЗМЕР 1" in variant:
                return item
        return None

    @staticmethod
    def _promote_match(item: ArrivalItem, master_item: MasterItem) -> None:
        item.status = "MATCH"
        item.sku = master_item.sku
        item.master_name = master_item.master_name or item.master_name or item.source_name
        item.review_reasons = []
        item.confidence = 100.0
        item.review_explanation = {
            "confidence": 100.0,
            "reasons": [],
            "candidates": [candidate.sku for candidate in item.candidates],
            "business_rule": True,
        }
