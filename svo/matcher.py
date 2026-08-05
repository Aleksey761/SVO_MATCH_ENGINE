
import re
from difflib import SequenceMatcher

from .models import ArrivalItem, MasterItem, effective_product_type


class Matcher:
    """Matches normalized arrival items against MASTER."""

    _COLOR_TOKENS = {
        "BLACK",
        "WHITE",
        "RED",
        "BLUE",
        "GREEN",
        "YELLOW",
        "PINK",
        "PURPLE",
        "ORANGE",
        "BROWN",
        "BEIGE",
        "GRAY",
        "GREY",
        "SILVER",
        "GOLD",
        "CHERRY",
        "CHARCOAL",
        "NAVY",
        "ЧЕРНЫЙ",
        "БЕЛЫЙ",
        "КРАСНЫЙ",
        "СИНИЙ",
        "ЗЕЛЕНЫЙ",
        "ЖЕЛТЫЙ",
        "РОЗОВЫЙ",
        "ФИОЛЕТОВЫЙ",
        "ОРАНЖЕВЫЙ",
        "КОРИЧНЕВЫЙ",
        "БЕЖЕВЫЙ",
        "СЕРЫЙ",
        "СЕРЕБРИСТЫЙ",
        "ЗОЛОТОЙ",
    }

    _KEYWORD_HINTS = {"BABY", "BLACK", "WHITE", "SPRING", "FLORAL", "MIST"}

    def __init__(
        self,
        master_items: list[MasterItem],
        confidence_threshold: float = 80.0,
        confidence_margin: float = 5.0,
    ):
        self.master_items = list(master_items)
        self.confidence_threshold = confidence_threshold
        self.confidence_margin = confidence_margin
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

    def _product_type_matches(self, arrival: ArrivalItem, master: MasterItem) -> bool:
        arrival_product_type = effective_product_type(arrival)
        master_product_type = effective_product_type(master)
        if not arrival_product_type or not master_product_type:
            return True
        return arrival_product_type == master_product_type

    def _product_type_mismatch_reason(self, arrival: ArrivalItem, master: MasterItem) -> str | None:
        if self._product_type_matches(arrival, master):
            return None
        return "PRODUCT_TYPE_MISMATCH"

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

    def _text_tokens(self, value: str | None) -> set[str]:
        if not value:
            return set()
        return set(self._canonical_aroma_tokens(self._normalize_value(value) or value))

    def _master_search_text(self, master: MasterItem) -> str:
        return " ".join(
            [
                str(master.master_name or "").strip(),
                str(master.category or "").strip(),
                str(master.brand or "").strip(),
                str(master.variant or "").strip(),
                str(master.volume or "").strip(),
                str(master.sku or "").strip(),
            ]
        )

    def _score_components(self, arrival: ArrivalItem, master: MasterItem) -> dict[str, float]:
        if not self._product_type_matches(arrival, master):
            return {
                "ProductType": 0.0,
                "Brand": 0.0,
                "Volume": 0.0,
                "Aroma": 0.0,
                "Color": 0.0,
                "Keywords": 0.0,
            }

        product_type_score = 0.0
        brand_score = 0.0
        volume_score = 0.0
        aroma_score = 0.0
        color_score = 0.0
        keyword_score = 0.0

        arrival_product_type = effective_product_type(arrival)
        master_product_type = effective_product_type(master)
        if arrival_product_type and master_product_type:
            if arrival_product_type == master_product_type:
                product_type_score = 30.0

        if arrival.volume and master.volume:
            if self._normalize_value(arrival.volume) == self._normalize_value(master.volume):
                volume_score = 40.0

        if arrival.brand and master.brand:
            if self._normalize_value(arrival.brand) == self._normalize_value(master.brand):
                brand_score = 20.0

        arrival_aroma = arrival.aroma or arrival.variant
        master_aroma = master.aroma or master.variant
        aroma_similarity = 0.0
        if arrival_aroma and master_aroma:
            normalized_arrival_aroma = self._normalize_value(arrival_aroma)
            normalized_master_aroma = self._normalize_value(master_aroma)
            if normalized_arrival_aroma == normalized_master_aroma:
                aroma_score = 15.0
            else:
                aroma_similarity = self._aroma_similarity(arrival_aroma, master_aroma)
                aroma_score = 15.0 * aroma_similarity
                if aroma_similarity <= 0.25:
                    aroma_score -= 40.0

        arrival_tokens = self._text_tokens(arrival.source_name)
        master_tokens = self._text_tokens(self._master_search_text(master))

        color_matches = sorted(arrival_tokens & master_tokens & self._COLOR_TOKENS)
        if color_matches:
            color_score = 6.0 * len(color_matches)

        keyword_matches = sorted((arrival_tokens & master_tokens) & self._KEYWORD_HINTS)
        if keyword_matches:
            keyword_score += 4.0 * len(keyword_matches)

        if arrival.category and master.category:
            if self._normalize_value(arrival.category) == self._normalize_value(master.category):
                keyword_score += 25.0

        source_variant_similarity = self._source_variant_similarity(arrival.source_name, master.variant)
        if source_variant_similarity > 0.0:
            keyword_score += 8.0 * source_variant_similarity

        source_master_similarity = self._source_master_similarity(arrival.source_name, master)
        if source_master_similarity > 0.0:
            if arrival_aroma and master_aroma:
                if aroma_similarity >= 0.75:
                    keyword_score += 120.0 * source_master_similarity
                elif aroma_similarity >= 0.25:
                    keyword_score += 45.0 * source_master_similarity
            else:
                keyword_score += 120.0 * source_master_similarity

        return {
            "ProductType": round(product_type_score, 2),
            "Brand": round(brand_score, 2),
            "Volume": round(volume_score, 2),
            "Aroma": round(aroma_score, 2),
            "Color": round(color_score, 2),
            "Keywords": round(keyword_score, 2),
        }

    def _score_detail(self, arrival: ArrivalItem, master: MasterItem) -> dict[str, object]:
        breakdown = self._score_components(arrival, master)
        score = round(sum(breakdown.values()), 2)
        mismatch_reason = self._product_type_mismatch_reason(arrival, master)
        arrival_product_type = effective_product_type(arrival)
        master_product_type = effective_product_type(master)

        if mismatch_reason is not None:
            assert score == 0.0, "Invariant violated: ProductType mismatch must have score 0"
        else:
            assert breakdown["ProductType"] >= 0.0, "Invariant violated: ProductType match cannot have negative ProductType score"

        return {
            "sku": master.sku,
            "master_name": master.master_name,
            "score": score,
            "breakdown": breakdown,
            "effective_product_type": {
                "supplier": arrival_product_type,
                "master": master_product_type,
            },
            "rejection_reason": mismatch_reason,
        }

    def _metadata_matches(self, arrival: ArrivalItem, master: MasterItem) -> bool:
        arrival_product_type = effective_product_type(arrival)
        master_product_type = effective_product_type(master)
        if arrival_product_type and master_product_type:
            if arrival_product_type != master_product_type:
                return False

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

        for field_name in ("product_type", "category", "brand", "volume", "aroma"):
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
        return sum(self._score_components(arrival, master).values())

    _AROMA_STOPWORDS = {
        "DLYA", "S", "I", "V", "NA", "PO", "IZ", "MEN", "WOMEN", "MAN", "WOMAN",
        "SHAMPUN", "GEL", "DUSHA", "MYLO", "KREM", "AROMAT", "SREDSTVO", "MOYUSHEE",
        "ZHIDKOE", "STIRKI", "BELYA", "AVTOMAT", "BLOK", "TUALETNIY", "UNITAZA",
        "MASL", "MASLO", "MASLA", "OIL",
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

    def _canonical_aroma_tokens(self, value: str) -> list[str]:
        text = value.lower().replace("ё", "е")
        text = text.translate(self._CYR_TO_LAT)
        text = re.sub(r"[^a-z0-9]+", " ", text)

        tokens: list[str] = []
        for raw in text.split():
            token = raw

            for suffix in (
                "ovogo", "evogo", "iyami", "yami", "ami", "ogo", "ego", "omu", "emu",
                "aya", "iya", "oe", "ee", "ye", "iy", "yy", "yi", "oi", "ai", "am", "yam",
                "ah", "yah", "ov", "ev", "om", "em", "iyu", "uyu", "yu", "ya", "ie", "ye",
                "oy", "yj", "yh", "y", "a", "e", "i", "o", "u",
            ):
                if len(token) > len(suffix) + 2 and token.endswith(suffix):
                    token = token[: -len(suffix)]
                    break

            for suffix in ("ings", "ing", "ness", "ment", "edly", "ed", "ies", "es", "s"):
                if len(token) > len(suffix) + 2 and token.endswith(suffix):
                    token = token[: -len(suffix)]
                    break

            normalized = token.upper()
            if len(normalized) < 3:
                continue
            if normalized in self._AROMA_STOPWORDS:
                continue
            tokens.append(normalized)

        # Keep token order but remove duplicates.
        deduped: list[str] = []
        seen = set()
        for token in tokens:
            if token not in seen:
                deduped.append(token)
                seen.add(token)
        return deduped

    def _aroma_similarity(self, arrival_aroma: str, master_aroma: str) -> float:
        arrival_value = self._normalize_value(arrival_aroma)
        master_value = self._normalize_value(master_aroma)
        if not arrival_value or not master_value:
            return 0.0

        arrival_tokens_seq = self._canonical_aroma_tokens(arrival_value)
        master_tokens_seq = self._canonical_aroma_tokens(master_value)
        arrival_tokens = set(arrival_tokens_seq)
        master_tokens = set(master_tokens_seq)
        if not arrival_tokens or not master_tokens:
            return 0.0

        if master_tokens.issubset(arrival_tokens):
            return 1.0

        overlap = len(arrival_tokens & master_tokens)
        fuzzy_cover = self._fuzzy_token_cover(arrival_tokens_seq, master_tokens_seq)
        if overlap <= 0 and fuzzy_cover <= 0.0:
            return 0.0

        cover = overlap / len(master_tokens)
        jaccard = overlap / len(arrival_tokens | master_tokens)
        sequence = SequenceMatcher(
            None,
            " ".join(arrival_tokens_seq),
            " ".join(master_tokens_seq),
        ).ratio()
        blended = max(cover, fuzzy_cover)
        return max(blended, jaccard, 0.7 * blended + 0.3 * sequence)

    def _fuzzy_token_cover(self, arrival_tokens: list[str], master_tokens: list[str]) -> float:
        if not arrival_tokens or not master_tokens:
            return 0.0

        total = 0.0
        matched = 0
        for master_token in master_tokens:
            best = 0.0
            for arrival_token in arrival_tokens:
                similarity = self._token_similarity(arrival_token, master_token)
                if similarity > best:
                    best = similarity
            if best >= 0.45:
                total += best
                matched += 1

        if matched == 0:
            return 0.0
        return total / len(master_tokens)

    @staticmethod
    def _token_similarity(left: str, right: str) -> float:
        if left == right:
            return 1.0
        if left.startswith(right) or right.startswith(left):
            shorter = min(len(left), len(right))
            longer = max(len(left), len(right))
            if longer:
                return shorter / longer
        return SequenceMatcher(None, left, right).ratio()

    def _source_variant_similarity(self, source_name: str, master_variant: str) -> float:
        source_tokens = self._canonical_aroma_tokens(source_name)
        variant_tokens = self._canonical_aroma_tokens(master_variant)
        if not source_tokens or not variant_tokens:
            return 0.0

        # Slightly stricter threshold for raw source text to avoid noisy boosts.
        total = 0.0
        matched = 0
        for variant_token in variant_tokens:
            best = 0.0
            for source_token in source_tokens:
                sim = self._token_similarity(source_token, variant_token)
                if sim > best:
                    best = sim
            if best >= 0.45:
                total += best
                matched += 1

        if matched == 0:
            return 0.0
        return total / len(variant_tokens)

    def _source_master_similarity(self, source_name: str, master: MasterItem) -> float:
        source_tokens = self._canonical_aroma_tokens(source_name)
        if not source_tokens:
            return 0.0

        master_text = " ".join(
            [
                str(master.master_name or "").strip(),
                str(master.category or "").strip(),
                str(master.brand or "").strip(),
                str(master.variant or "").strip(),
                str(master.volume or "").strip(),
                str(master.sku or "").strip(),
            ]
        )
        master_tokens = self._canonical_aroma_tokens(master_text)
        if not master_tokens:
            return 0.0

        source_set = set(source_tokens)
        master_set = set(master_tokens)
        overlap = len(source_set & master_set)
        if overlap == 0:
            return 0.0

        cover = overlap / len(master_set)
        jaccard = overlap / len(source_set | master_set)
        sequence = SequenceMatcher(
            None,
            " ".join(source_tokens),
            " ".join(master_tokens),
        ).ratio()
        return max(cover, jaccard, sequence)

    def _collect_candidates(self, item: ArrivalItem) -> list[MasterItem]:
        def candidate_key(candidate: MasterItem) -> str:
            return f"{candidate.sku}|{candidate.normalized_key}"

        def intersect_by_key(candidate_groups: list[list[MasterItem]]) -> list[MasterItem]:
            keyed_groups = [
                {candidate_key(candidate): candidate for candidate in group}
                for group in candidate_groups if group
            ]
            if len(keyed_groups) < 2:
                return []
            common_keys = set(keyed_groups[0].keys())
            for keyed_group in keyed_groups[1:]:
                common_keys &= set(keyed_group.keys())
            if not common_keys:
                return []
            # Preserve deterministic order based on the first keyed group.
            ordered = []
            for key, candidate in keyed_groups[0].items():
                if key in common_keys:
                    ordered.append(candidate)
            return ordered

        category_candidates = self._lookup_candidates(item.category)
        brand_candidates = self._lookup_candidates(item.brand)
        volume_candidates = self._lookup_candidates(item.volume)

        # If core metadata exists, intersect it first to reduce noisy candidate pools.
        narrowed = intersect_by_key([category_candidates, brand_candidates, volume_candidates])
        if narrowed:
            candidates = narrowed
            aroma_candidates = self._lookup_candidates(item.aroma or item.variant)
            if aroma_candidates:
                aroma_keys = {candidate_key(candidate) for candidate in aroma_candidates}
                aroma_narrowed = [candidate for candidate in candidates if candidate_key(candidate) in aroma_keys]
                if aroma_narrowed:
                    return aroma_narrowed
            return candidates

        # If all three are not available, still intersect any two available core groups.
        available_groups = [group for group in (category_candidates, brand_candidates, volume_candidates) if group]
        if len(available_groups) >= 2:
            pair_narrowed = intersect_by_key(available_groups)
            if pair_narrowed:
                candidates = pair_narrowed
                aroma_candidates = self._lookup_candidates(item.aroma or item.variant)
                if aroma_candidates:
                    aroma_keys = {candidate_key(candidate) for candidate in aroma_candidates}
                    aroma_narrowed = [candidate for candidate in candidates if candidate_key(candidate) in aroma_keys]
                    if aroma_narrowed:
                        return aroma_narrowed
                return candidates

        candidates: list[MasterItem] = []
        for value in [item.sku, effective_product_type(item), item.category, item.brand, item.volume, item.aroma or item.variant]:
            for candidate in self._lookup_candidates(value):
                if candidate not in candidates:
                    candidates.append(candidate)

        if candidates:
            return candidates

        # Fallback for sparse metadata rows: search MASTER by source text overlap.
        scored_fallback: list[tuple[MasterItem, float]] = []
        for candidate in self.master_items:
            similarity = self._source_master_similarity(item.source_name, candidate)
            if similarity >= 0.18:
                scored_fallback.append((candidate, similarity))

        scored_fallback.sort(key=lambda entry: entry[1], reverse=True)
        return [candidate for candidate, _ in scored_fallback[:12]]

    def _build_review_reasons(
        self,
        candidate_scores: list[dict[str, object]],
    ) -> list[str]:
        if candidate_scores and all(candidate.get("rejection_reason") == "PRODUCT_TYPE_MISMATCH" for candidate in candidate_scores):
            return ["PRODUCT_TYPE_MISMATCH"]

        reasons: list[str] = []
        if len(candidate_scores) > 1:
            reasons.append("MULTIPLE_MATCH")
        if candidate_scores and float(candidate_scores[0]["score"]) < self.confidence_threshold:
            reasons.append("LOW_SCORE")
        return reasons

    def _rejection_summary(
        self,
        candidate_scores: list[dict[str, object]],
    ) -> list[str]:
        if not candidate_scores:
            return ["NO_CANDIDATES"]

        if all(candidate.get("rejection_reason") == "PRODUCT_TYPE_MISMATCH" for candidate in candidate_scores):
            for candidate in candidate_scores:
                assert float(candidate["score"]) == 0.0, "Invariant violated: ProductType mismatch candidate must have score 0"
            return ["PRODUCT_TYPE_MISMATCH"]

        best_score = float(candidate_scores[0]["score"])
        second_score = float(candidate_scores[1]["score"]) if len(candidate_scores) > 1 else 0.0
        above_threshold = [candidate for candidate in candidate_scores if float(candidate["score"]) >= self.confidence_threshold]

        reasons: list[str] = []
        if best_score < self.confidence_threshold:
            reasons.append(
                f"best candidate score {best_score:.2f} is below threshold {self.confidence_threshold:.2f}"
            )
        if len(above_threshold) != 1:
            reasons.append(
                f"{len(above_threshold)} candidates meet threshold {self.confidence_threshold:.2f}"
            )
        if len(candidate_scores) > 1:
            gap = best_score - second_score
            if gap < self.confidence_margin:
                reasons.append(
                    f"best candidate leads second by {gap:.2f}, below margin {self.confidence_margin:.2f}"
                )
        return reasons

    def _candidate_explanations(self, candidate_scores: list[dict[str, object]]) -> list[dict[str, object]]:
        explanations: list[dict[str, object]] = []
        for candidate in candidate_scores:
            explanations.append(
                {
                    "sku": candidate["sku"],
                    "master_name": candidate["master_name"],
                    "score": candidate["score"],
                    "breakdown": candidate["breakdown"],
                    "effective_product_type": candidate["effective_product_type"],
                    "rejection_reason": candidate["rejection_reason"],
                }
            )
        return explanations

    def _review_reasons(self, item: ArrivalItem, candidates: list[MasterItem], best_score: float) -> list[str]:
        reasons: list[str] = []
        if candidates and all(not self._product_type_matches(item, candidate) for candidate in candidates):
            return ["PRODUCT_TYPE_MISMATCH"]
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
        if master is not None and not self._product_type_matches(item, master):
            master = None
        if master is None:
            candidates = self._collect_candidates(item)
            scored_candidates = [
                {
                    **self._score_detail(item, candidate),
                    "candidate": candidate,
                }
                for candidate in candidates
            ]
            scored_candidates.sort(key=lambda entry: float(entry["score"]), reverse=True)

            if scored_candidates:
                best_candidate = scored_candidates[0]["candidate"]
                best_score = float(scored_candidates[0]["score"])
                second_score = float(scored_candidates[1]["score"]) if len(scored_candidates) > 1 else 0.0
                above_threshold = [candidate for candidate in scored_candidates if float(candidate["score"]) >= self.confidence_threshold]

                item.confidence = round(best_score, 2)
                item.candidates = [candidate["candidate"] for candidate in scored_candidates]

                if len(above_threshold) == 1 and (len(scored_candidates) == 1 or (best_score - second_score) >= self.confidence_margin):
                    master = best_candidate
                else:
                    item.review_reasons = self._build_review_reasons(scored_candidates)
                    item.review_explanation = {
                        "confidence": item.confidence,
                        "threshold": self.confidence_threshold,
                        "margin": self.confidence_margin,
                        "best_candidate": self._candidate_explanations([scored_candidates[0]])[0],
                        "best_candidate_rejected_reason": self._rejection_summary(scored_candidates),
                        "reasons": item.review_reasons,
                        "candidates": self._candidate_explanations(scored_candidates),
                    }
                    item.status = "REVIEW"
                    return item
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
        item.master_name = master.master_name
        item.status = "MATCH"
        item.confidence = 100.0
        item.review_explanation = {"confidence": 100.0, "reasons": [], "candidates": []}
        return item

    def match_all(self, items: list[ArrivalItem]) -> list[ArrivalItem]:
        return [self.match(i) for i in items]
