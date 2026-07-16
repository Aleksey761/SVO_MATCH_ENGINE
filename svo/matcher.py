
from .models import ArrivalItem, MasterItem


class Matcher:
    """Matches normalized arrival items against MASTER."""

    def __init__(self, master_items: list[MasterItem]):
        self.master_items = list(master_items)
        self.index = {item.normalized_key: item for item in self.master_items}
        self.master_index: dict[str, MasterItem | list[MasterItem]] = {}
        self._build_master_index()

    def _build_master_index(self) -> None:
        self.master_index = {}
        for master in self.master_items:
            for _, key in master.index_values():
                entry = self.master_index.get(key)
                if entry is None:
                    self.master_index[key] = master
                elif isinstance(entry, list):
                    if master not in entry:
                        entry.append(master)
                else:
                    self.master_index[key] = [entry, master]

    def _normalize_value(self, value: str | None) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        return " ".join(text.split()).upper()

    def _lookup_candidates(self, value: str | None) -> list[MasterItem]:
        normalized = self._normalize_value(value)
        if normalized is None:
            return []

        entry = self.master_index.get(normalized)
        if entry is None:
            return []
        if isinstance(entry, list):
            return entry
        return [entry]

    def _metadata_matches(self, arrival: ArrivalItem, master: MasterItem) -> bool:
        for field_name in ("category", "brand", "volume"):
            arrival_value = getattr(arrival, field_name, None)
            master_value = getattr(master, field_name, None)
            if arrival_value and master_value:
                if self._normalize_value(arrival_value) != self._normalize_value(master_value):
                    return False

        arrival_aroma = arrival.aroma or arrival.variant
        master_aroma = master.aroma or master.variant
        if arrival_aroma and master_aroma:
            if self._normalize_value(arrival_aroma) != self._normalize_value(master_aroma):
                return False

        return True

    def _find_exact_master(self, item: ArrivalItem) -> MasterItem | None:
        exact_matches: list[MasterItem] = []

        if item.sku:
            exact_matches.extend(
                candidate
                for candidate in self._lookup_candidates(item.sku)
                if self._metadata_matches(item, candidate)
            )

        for field_name in ("category", "brand", "volume", "aroma"):
            value = getattr(item, field_name, None)
            if value:
                exact_matches.extend(
                    candidate
                    for candidate in self._lookup_candidates(value)
                    if self._metadata_matches(item, candidate)
                )

        unique_matches: list[MasterItem] = []
        for candidate in exact_matches:
            if candidate not in unique_matches:
                unique_matches.append(candidate)
        if len(unique_matches) == 1:
            return unique_matches[0]

        return self.index.get(item.normalized_key)

    def _score(self, arrival: ArrivalItem, master: MasterItem) -> float:
        score = 0.0

        if arrival.volume and master.volume:
            if self._normalize_value(arrival.volume) == self._normalize_value(master.volume):
                score += 40.0

        if arrival.category and master.category:
            if self._normalize_value(arrival.category) == self._normalize_value(master.category):
                score += 25.0

        if arrival.brand and master.brand:
            if self._normalize_value(arrival.brand) == self._normalize_value(master.brand):
                score += 20.0

        arrival_aroma = arrival.aroma or arrival.variant
        master_aroma = master.aroma or master.variant
        if arrival_aroma and master_aroma:
            if self._normalize_value(arrival_aroma) == self._normalize_value(master_aroma):
                score += 15.0

        return score

    def _collect_candidates(self, item: ArrivalItem) -> list[MasterItem]:
        candidates: list[MasterItem] = []
        for value in [item.sku, item.category, item.brand, item.volume, item.aroma or item.variant]:
            for candidate in self._lookup_candidates(value):
                if candidate not in candidates:
                    candidates.append(candidate)
        return candidates

    def _review_reasons(self, item: ArrivalItem, candidates: list[MasterItem], best_score: float) -> list[str]:
        reasons: list[str] = []
        if len(candidates) > 1:
            reasons.append("MULTIPLE_MATCH")
        if best_score < 100.0:
            reasons.append("LOW_SCORE")
        if not item.brand or not any(
            self._normalize_value(item.brand) == self._normalize_value(candidate.brand)
            for candidate in candidates
        ):
            reasons.append("UNKNOWN_BRAND")
        if not item.volume:
            reasons.append("NO_VOLUME")

        return reasons

    def match(self, item: ArrivalItem) -> ArrivalItem:
        item.confidence = 0.0
        item.review_reasons = []
        item.candidates = []
        item.review_explanation = {}

        master = self._find_exact_master(item)
        if master is None:
            candidates = self._collect_candidates(item)
            scored_candidates = [
                (candidate, self._score(item, candidate))
                for candidate in candidates
            ]
            scored_candidates.sort(key=lambda entry: entry[1], reverse=True)

            if scored_candidates:
                best_candidate, best_score = scored_candidates[0]
                close_candidates = [
                    candidate for candidate, score in scored_candidates if score >= best_score - 5.0
                ]
                item.candidates = close_candidates
                item.confidence = round(best_score, 2)
                if len(close_candidates) > 1:
                    item.review_reasons = self._review_reasons(item, close_candidates, best_score)
                    item.review_explanation = {
                        "confidence": item.confidence,
                        "reasons": item.review_reasons,
                        "candidates": [candidate.sku for candidate in close_candidates],
                    }
                    item.status = "REVIEW"
                    return item
                if best_score >= 100.0:
                    master = best_candidate
            else:
                best_score = 0.0

        if master is None:
            item.review_reasons = self._review_reasons(item, item.candidates or [], item.confidence)
            item.review_explanation = {
                "confidence": item.confidence,
                "reasons": item.review_reasons,
                "candidates": [candidate.sku for candidate in item.candidates],
            }
            item.status = "REVIEW"
            return item

        item.sku = master.sku
        item.master_name = f"{master.category} {master.brand} {master.variant} {master.volume}"
        item.status = "MATCH"
        item.confidence = 100.0
        item.review_explanation = {"confidence": 100.0, "reasons": [], "candidates": []}
        return item

    def match_all(self, items: list[ArrivalItem]) -> list[ArrivalItem]:
        return [self.match(i) for i in items]
