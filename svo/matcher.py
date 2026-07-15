
from difflib import SequenceMatcher
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
        if item.sku:
            for candidate in self._lookup_candidates(item.sku):
                if self._metadata_matches(item, candidate):
                    return candidate

        for field_name in ("category", "brand", "volume", "aroma"):
            value = getattr(item, field_name, None)
            if value:
                for candidate in self._lookup_candidates(value):
                    if self._metadata_matches(item, candidate):
                        return candidate

        return self.index.get(item.normalized_key)

    def _score(self, arrival: ArrivalItem, master: MasterItem) -> int:
        score = 0
        if arrival.brand and arrival.brand == master.brand:
            score += 100
        if arrival.category and arrival.category == master.category:
            score += 60
        if arrival.volume and arrival.volume.upper() == master.volume.upper():
            score += 100
        ratio = SequenceMatcher(
            None,
            (arrival.variant or "").upper(),
            (master.variant or "").upper()
        ).ratio()
        score += int(ratio * 200)
        return score

    def match(self, item: ArrivalItem) -> ArrivalItem:
        master = self._find_exact_master(item)
        if master is None:
            candidates = []
            for value in [item.sku, item.category, item.brand, item.volume, item.aroma or item.variant]:
                for candidate in self._lookup_candidates(value):
                    if candidate not in candidates:
                        candidates.append(candidate)

            best = None
            best_score = -1
            for candidate in candidates:
                score = self._score(item, candidate)
                if score > best_score:
                    best_score = score
                    best = candidate
            if best and best_score >= 220:
                master = best

        if master is None:
            item.status = "REVIEW"
            return item

        item.sku = master.sku
        item.master_name = f"{master.category} {master.brand} {master.variant} {master.volume}"
        item.status = "MATCH"
        return item

    def match_all(self, items: list[ArrivalItem]) -> list[ArrivalItem]:
        return [self.match(i) for i in items]
