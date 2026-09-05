from __future__ import annotations

from pathlib import Path
from openpyxl import Workbook

from svo.engine import Engine
from svo.normalizer import Normalizer


def _normalized_name(value: object) -> str:
    text = str(value or "").strip()
    return " ".join(text.upper().split())


def _format_best_candidate(item) -> str:
    if not item.candidates:
        return ""
    candidate = item.candidates[0]
    return (
        f"{candidate.sku} | {candidate.category} | {candidate.brand} | "
        f"{candidate.variant} | {candidate.volume}"
    )


def _build_fail_reason(item) -> str:
    reasons: list[str] = []
    review_reasons = [str(value) for value in (item.review_reasons or [])]
    if review_reasons:
        reasons.append("review_reasons=" + ",".join(review_reasons))

    best_candidate = item.candidates[0] if item.candidates else None
    if best_candidate is None:
        reasons.append("no candidates found by matcher index")
    else:
        if not getattr(item, "brand", None):
            reasons.append("brand not extracted from source name")
        if not getattr(item, "volume", None):
            reasons.append("volume not extracted from source name")
        if not getattr(item, "category", None):
            reasons.append("category not extracted from source name")

        arrival_aroma = getattr(item, "aroma", None) or getattr(item, "variant", None)
        best_aroma = getattr(best_candidate, "aroma", None) or getattr(best_candidate, "variant", None)

        if getattr(item, "brand", None) and getattr(best_candidate, "brand", None):
            if _normalized_name(item.brand) != _normalized_name(best_candidate.brand):
                reasons.append(f"brand mismatch: {item.brand} != {best_candidate.brand}")

        if getattr(item, "category", None) and getattr(best_candidate, "category", None):
            if _normalized_name(item.category) != _normalized_name(best_candidate.category):
                reasons.append(f"category mismatch: {item.category} != {best_candidate.category}")

        if getattr(item, "volume", None) and getattr(best_candidate, "volume", None):
            if _normalized_name(item.volume) != _normalized_name(best_candidate.volume):
                reasons.append(f"volume mismatch: {item.volume} != {best_candidate.volume}")

        if arrival_aroma and best_aroma:
            if _normalized_name(arrival_aroma) != _normalized_name(best_aroma):
                reasons.append(f"aroma/variant mismatch: {arrival_aroma} != {best_aroma}")

    score = float(getattr(item, "confidence", 0) or 0)
    if score < 100.0:
        reasons.append(f"score below exact threshold: {score:.2f}")

    if not reasons:
        reasons.append("exact match not found by _find_exact_master; best candidate is fuzzy only")

    return "; ".join(reasons)


def main() -> None:
    base = Path(__file__).parent
    revision_root = Path("F:/SVO/Склад")
    revision_file = sorted(
        [p for p in revision_root.glob("*.xlsx") if "10.07.24" in p.name and not p.name.startswith("~$")]
    )[0]

    result_file = base / "output" / "RESULT 10.07.24.xlsx"
    diagnostics_file = base / "output" / "REVISION_MATCH_DIAGNOSTICS_10.07.24.xlsx"

    engine = Engine()
    result = engine.run(
        master_file=None,
        arrival_file=revision_file,
        output_file=result_file,
        input_dir=base,
    )

    normalizer = Normalizer()
    review_items = [item for item in engine.items if str(item.status).upper() == "REVIEW"]

    wb = Workbook()
    ws = wb.active
    ws.title = "REVISION_DIAGNOSTICS"
    ws.append(
        [
            "ROW_NUMBER",
            "ORIGINAL_PRODUCT_NAME",
            "NORMALIZED_PRODUCT_NAME",
            "BEST_MASTER_CANDIDATE",
            "MATCHING_SCORE",
            "EXACT_MATCH_FAIL_REASON",
        ]
    )

    for item in review_items:
        original = getattr(item, "ProductName", None) or item.source_name
        normalized = _normalized_name(normalizer._clean_text(original))
        ws.append(
            [
                item.row_number,
                original,
                normalized,
                _format_best_candidate(item),
                float(getattr(item, "confidence", 0) or 0),
                _build_fail_reason(item),
            ]
        )

    ws.freeze_panes = "A2"
    widths = {
        "A": 12,
        "B": 70,
        "C": 70,
        "D": 70,
        "E": 16,
        "F": 120,
    }
    for col, width in widths.items():
        ws.column_dimensions[col].width = width

    diagnostics_file.parent.mkdir(parents=True, exist_ok=True)
    wb.save(diagnostics_file)

    print(f"DIAGNOSTICS_PATH={diagnostics_file.resolve()}")
    print(f"REVISION_FILE={revision_file.resolve()}")
    print(f"RESULT_FILE={result_file.resolve()}")
    print(f"MATCH={result.get('match')}")
    print(f"REVIEW={result.get('review')}")
    print(f"REVIEW_ROWS_WRITTEN={len(review_items)}")


if __name__ == "__main__":
    main()
