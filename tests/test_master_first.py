import pytest

from svo.models import ArrivalItem, MasterItem, effective_product_type
from svo.matcher import Matcher
from svo.normalizer import Normalizer


def test_master_first_indexing_supports_sku_and_other_keys():
    master_items = [
        MasterItem(sku="SKU-1", category="Шампунь", brand="SVO", variant="AQUA", volume="1 л"),
        MasterItem(sku="SKU-2", category="Гель для душа", brand="GILAR", variant="LIME", volume="500 мл"),
    ]

    matcher = Matcher(master_items)

    assert matcher.master_index["SKU-1"] == master_items[0]
    assert matcher.master_index["SHAMPUN"].sku == "SKU-1"
    assert matcher.master_index["SVO"].sku == "SKU-1"
    assert matcher.master_index["1 Л"].sku == "SKU-1"
    assert matcher.master_index["AQUA"].sku == "SKU-1"


def test_match_prefers_master_catalog_matches_before_fuzzy_fallback():
    master_items = [
        MasterItem(sku="SKU-10", category="Шампунь", brand="SVO", variant="AQUA", volume="1 л"),
    ]
    matcher = Matcher(master_items)

    arrival = ArrivalItem(row_number=1, source_name="SVO SHAMPUN AQUA 1 л")
    arrival.category = "Шампунь"
    arrival.brand = "SVO"
    arrival.variant = "AQUA"
    arrival.volume = "1 л"

    matched = matcher.match(arrival)

    assert matched.status == "MATCH"
    assert matched.sku == "SKU-10"


def test_normalizer_supports_configurable_rules():
    normalizer = Normalizer(
        brand_rules=[("SVO", ["svo", "sv"]), ("GILAR", ["gilar"])],
        volume_rules=[("л", ["л", "liter"]), ("мл", ["ml"])],
        garbage_words=["parfume", "junk"],
        aroma_aliases={"ЛАЙМ": ["lime", "лайм"]},
    )
    item = ArrivalItem(row_number=1, source_name="SV GILAR SHAMPOO 500 ml JUNK LIME")

    result = normalizer.normalize(item)

    assert result.brand == "SVO"
    assert result.volume == "500 МЛ"
    assert result.variant == "LIME"
    assert result.aroma == "LIME"


def test_normalizer_converts_large_volumes_to_liters_and_removes_garbage_words():
    normalizer = Normalizer(
        category_rules=[("Шампунь", ["шампунь"])],
        brand_rules=[("SVO", ["svo"])],
        aroma_aliases={"АКВА": ["aqua", "аква"]},
    )
    item = ArrivalItem(row_number=2, source_name="SVO Shampun 1000 ml PARFUME AQUA")

    result = normalizer.normalize(item)

    assert result.category == "Шампунь"
    assert result.brand == "SVO"
    assert result.volume == "1 Л"
    assert result.variant == "AQUA"
    assert result.aroma == "AQUA"


def test_match_returns_multiple_candidates_when_confidence_is_close():
    master_items = [
        MasterItem(sku="SKU-20", category="Шампунь", brand="SVO", variant="AQUA", volume="1 л"),
        MasterItem(sku="SKU-21", category="Шампунь", brand="SVO", variant="LIME", volume="1 л"),
    ]
    matcher = Matcher(master_items)

    arrival = ArrivalItem(row_number=3, source_name="SVO SHAMPUN 1 л")
    arrival.category = "Шампунь"
    arrival.brand = "SVO"
    arrival.volume = "1 л"

    matched = matcher.match(arrival)

    assert matched.status == "REVIEW"
    assert matched.confidence > 100.0
    assert "MULTIPLE_MATCH" in matched.review_reasons
    assert "LOW_SCORE" not in matched.review_reasons
    assert len(matched.candidates) == 2
    assert matched.review_explanation["reasons"] == ["MULTIPLE_MATCH"]
    assert matched.review_explanation["threshold"] == 80.0
    assert matched.review_explanation["margin"] == 5.0
    assert matched.review_explanation["best_candidate_rejected_reason"]
    assert len(matched.review_explanation["candidates"]) == 2
    assert matched.review_explanation["candidates"][0]["sku"] == "SKU-20"
    assert set(matched.review_explanation["candidates"][0]["breakdown"]) == {
        "ProductType",
        "Brand",
        "Volume",
        "Aroma",
        "Color",
        "Keywords",
    }


def test_match_auto_assigns_when_one_candidate_crosses_threshold_and_margin():
    master_items = [
        MasterItem(sku="SKU-50", category="Шампунь", brand="SVO", variant="AQUA", volume="1 л"),
        MasterItem(sku="SKU-51", category="Шампунь", brand="OTHER", variant="LIME", volume="1 л"),
    ]
    matcher = Matcher(master_items, confidence_threshold=80.0, confidence_margin=5.0)

    arrival = ArrivalItem(row_number=6, source_name="SVO SHAMPUN AQUA 1 л")
    arrival.category = "Шампунь"
    arrival.brand = "SVO"
    arrival.variant = "AQUA"
    arrival.volume = "1 л"

    matched = matcher.match(arrival)

    assert matched.status == "MATCH"
    assert matched.sku == "SKU-50"
    assert matched.master_name is None or isinstance(matched.master_name, str)
    assert matched.review_explanation == {"confidence": 100.0, "reasons": [], "candidates": []}


def test_match_prefers_unique_exact_triple_candidate_within_tie_range():
    master_items = [
        MasterItem(sku="SKU-60", category="Шампунь", brand="SVO", variant="AQUA", volume="1 л"),
        MasterItem(sku="SKU-61", category="Шампунь", brand="OTHER", variant="LIME", volume="1 л"),
    ]
    matcher = Matcher(master_items, confidence_threshold=80.0, confidence_margin=5.0)

    arrival = ArrivalItem(row_number=7, source_name="SVO SHAMPUN LIME 1 л")
    arrival.category = "Шампунь"
    arrival.brand = "SVO"
    arrival.variant = "LIME"
    arrival.volume = "1 л"

    def fake_score_detail(_, candidate):
        if candidate.sku == "SKU-61":
            return {
                "sku": candidate.sku,
                "master_name": candidate.master_name,
                "score": 84.0,
                "breakdown": {
                    "ProductType": 30.0,
                    "Brand": 0.0,
                    "Volume": 40.0,
                    "Aroma": 10.0,
                    "Color": 0.0,
                    "Keywords": 4.0,
                },
                "effective_product_type": {"supplier": "ШАМПУНЬ", "master": "ШАМПУНЬ"},
                "rejection_reason": None,
            }
        return {
            "sku": candidate.sku,
            "master_name": candidate.master_name,
            "score": 81.0,
            "breakdown": {
                "ProductType": 30.0,
                "Brand": 20.0,
                "Volume": 40.0,
                "Aroma": 0.0,
                "Color": 0.0,
                "Keywords": -9.0,
            },
            "effective_product_type": {"supplier": "ШАМПУНЬ", "master": "ШАМПУНЬ"},
            "rejection_reason": None,
        }

    matcher._collect_candidates = lambda _: master_items
    matcher._score_detail = fake_score_detail

    scored = [
        {**matcher._score_detail(arrival, master_items[1]), "candidate": master_items[1]},
        {**matcher._score_detail(arrival, master_items[0]), "candidate": master_items[0]},
    ]
    scored.sort(key=lambda entry: float(entry["score"]), reverse=True)

    preferred = matcher._preferred_exact_triple_candidate(arrival, scored)

    assert preferred is not None
    assert preferred["candidate"].sku == "SKU-60"
    assert float(scored[0]["score"]) - float(preferred["score"]) <= matcher.confidence_margin

    matched = matcher.match(arrival)

    assert matched.status == "MATCH"
    assert matched.sku == "SKU-60"


def test_match_reports_missing_volume_and_unknown_brand():
    master_items = [
        MasterItem(sku="SKU-30", category="Шампунь", brand="SVO", variant="AQUA", volume="1 л"),
    ]
    matcher = Matcher(master_items)

    arrival = ArrivalItem(row_number=4, source_name="UNKNOWN BRAND SHAMPUN AQUA")
    arrival.category = "Шампунь"
    arrival.brand = "UNKNOWN"
    arrival.variant = "AQUA"

    matched = matcher.match(arrival)

    assert matched.status == "REVIEW"
    assert matched.sku is None
    assert matched.confidence == 78.0
    assert matched.review_reasons == ["LOW_SCORE"]
    assert matched.review_explanation["best_candidate"]["sku"] == "SKU-30"
    assert matched.review_explanation["best_candidate_rejected_reason"] == [
        "best candidate score 78.00 is below threshold 80.00",
        "0 candidates meet threshold 80.00",
    ]


def test_matcher_v04_contract_preserves_public_api_and_result_shape():
    master_items = [
        MasterItem(sku="SKU-40", category="Шампунь", brand="SVO", variant="AQUA", volume="1 л"),
    ]
    matcher = Matcher(master_items)

    arrival = ArrivalItem(row_number=5, source_name="SVO SHAMPUN AQUA")
    arrival.category = "Шампунь"
    arrival.brand = "SVO"
    arrival.variant = "AQUA"
    arrival.volume = "1 л"

    matched = matcher.match(arrival)
    batch_result = matcher.match_all([arrival])

    assert isinstance(matched, ArrivalItem)
    assert matched.status == "MATCH"
    assert matched.sku == "SKU-40"
    assert matched.confidence == 100.0
    assert matched.review_reasons == []
    assert matched.candidates == []
    assert matched.review_explanation == {"confidence": 100.0, "reasons": [], "candidates": []}
    assert len(batch_result) == 1
    assert isinstance(batch_result[0], ArrivalItem)


def test_canonical_key_differs_for_laundry_gel_and_conditioner():
    normalizer = Normalizer(brand_rules=[("SVO", ["svo"])])

    gel = ArrivalItem(row_number=1, source_name="Гель для стирки SVO Floral Mist 1 л")
    conditioner = ArrivalItem(row_number=2, source_name="Кондиционер SVO Floral Mist 1 л")

    gel = normalizer.normalize(gel)
    conditioner = normalizer.normalize(conditioner)

    assert gel.product_type == "Гель для стирки"
    assert conditioner.product_type == "Кондиционер"
    assert gel.normalized_key != conditioner.normalized_key


def test_canonical_key_differs_for_shampoo_and_shower_gel():
    normalizer = Normalizer(brand_rules=[("GILAR", ["gilar"])])

    shampoo = ArrivalItem(row_number=1, source_name="Шампунь GILAR Cherry 400 мл")
    shower_gel = ArrivalItem(row_number=2, source_name="Гель для душа GILAR Cherry 400 мл")

    shampoo = normalizer.normalize(shampoo)
    shower_gel = normalizer.normalize(shower_gel)

    assert shampoo.product_type == "Шампунь"
    assert shower_gel.product_type == "Гель для душа"
    assert shampoo.normalized_key != shower_gel.normalized_key


def test_same_product_type_same_aroma_same_volume_keeps_same_canonical_key():
    normalizer = Normalizer(brand_rules=[("SVO", ["svo"])])

    first = ArrivalItem(row_number=1, source_name="Шампунь SVO Floral Mist 1 л")
    second = ArrivalItem(row_number=2, source_name="Шампунь SVO Floral Mist 1 л")

    first = normalizer.normalize(first)
    second = normalizer.normalize(second)

    assert first.product_type == "Шампунь"
    assert second.product_type == "Шампунь"
    assert first.normalized_key == second.normalized_key


def test_matcher_does_not_cross_match_different_product_types():
    master_items = [
        MasterItem(sku="SKU-GEL", category="Гель для стирки", brand="SVO", variant="FLORAL MIST", volume="1 Л"),
        MasterItem(sku="SKU-COND", category="Кондиционер", brand="SVO", variant="FLORAL MIST", volume="1 Л"),
    ]
    matcher = Matcher(master_items)

    arrival = ArrivalItem(row_number=1, source_name="Гель для стирки SVO Floral Mist 1 л")
    normalizer = Normalizer(brand_rules=[("SVO", ["svo"])])
    arrival = normalizer.normalize(arrival)

    matched = matcher.match(arrival)

    assert matched.status == "MATCH"
    assert matched.sku == "SKU-GEL"


@pytest.mark.parametrize(
    "arrival_text, master_text, master_sku, expected_product_type",
    [
        (
            "Гель для стирки SVO Floral Mist 1 л",
            "Кондиционер SVO Floral Mist 1 л",
            "SKU-COND",
            "Гель для стирки",
        ),
        (
            "Кондиционер SVO Floral Mist 1 л",
            "Гель для стирки SVO Floral Mist 1 л",
            "SKU-GEL",
            "Кондиционер",
        ),
        (
            "Гель для душа GILAR Cherry 400 мл",
            "Шампунь GILAR Cherry 400 мл",
            "SKU-SHAMPOO",
            "Гель для душа",
        ),
    ],
)
def test_product_type_mismatch_never_autoselects(
    arrival_text: str,
    master_text: str,
    master_sku: str,
    expected_product_type: str,
):
    master_normalizer = Normalizer(brand_rules=[("SVO", ["svo"]), ("GILAR", ["gilar"])])

    arrival = master_normalizer.normalize(ArrivalItem(row_number=1, source_name=arrival_text))
    master = master_normalizer.normalize(ArrivalItem(row_number=2, source_name=master_text))

    master_item = MasterItem(
        sku=master_sku,
        category=master.product_type or master.category or "",
        brand=master.brand or "",
        variant=master.variant or "",
        volume=master.volume or "",
        master_name=master_text,
        aroma=master.aroma,
    )
    matcher = Matcher([master_item])

    matched = matcher.match(arrival)

    assert arrival.product_type == expected_product_type
    assert matched.status == "REVIEW"
    assert matched.sku is None
    assert matched.confidence == 0.0
    assert matched.review_reasons == ["PRODUCT_TYPE_MISMATCH"]
    assert matched.candidates[0].sku == master_sku
    assert matched.review_explanation["candidates"][0]["score"] == 0.0
    assert matched.review_explanation["best_candidate_rejected_reason"] == ["PRODUCT_TYPE_MISMATCH"]


def test_effective_product_type_is_unified_in_scoring_filtering_and_review_diagnostics():
    normalizer = Normalizer(brand_rules=[("SVO", ["svo"])])

    supplier = normalizer.normalize(
        ArrivalItem(row_number=10, source_name="SVO Гель д/Стирки 1 л Floral Mist")
    )
    # Keep the original supplier text but pin canonical supplier ProductType for this regression.
    supplier.product_type = "Гель для стирки"

    master_item = MasterItem(
        sku="SKU-074",
        category="ЖМС",
        brand="SVO",
        variant="FLORAL MIST",
        volume="1 Л",
        master_name="ЖМС SVO Floral Mist 1 л",
        aroma="FLORAL MIST",
    )

    matcher = Matcher([master_item])
    matched = matcher.match(supplier)

    supplier_effective = effective_product_type(supplier)
    master_effective = effective_product_type(master_item)

    assert supplier_effective is not None
    assert master_effective is not None
    assert supplier_effective != master_effective

    assert matched.status == "REVIEW"
    assert matched.sku is None
    assert matched.confidence == 0.0
    assert matched.review_reasons == ["PRODUCT_TYPE_MISMATCH"]

    candidate_diag = matched.review_explanation["candidates"][0]
    assert candidate_diag["effective_product_type"]["supplier"] == supplier_effective
    assert candidate_diag["effective_product_type"]["master"] == master_effective
    assert candidate_diag["score"] == 0.0
    assert candidate_diag["rejection_reason"] == "PRODUCT_TYPE_MISMATCH"
    assert candidate_diag["breakdown"]["ProductType"] == 0.0

    # Invariant: ProductType mismatch must always produce score zero and a mismatch reason.
    assert matched.review_explanation["best_candidate_rejected_reason"] == ["PRODUCT_TYPE_MISMATCH"]
