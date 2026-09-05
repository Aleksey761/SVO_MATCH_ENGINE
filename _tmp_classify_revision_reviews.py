from collections import defaultdict
from pathlib import Path

from openpyxl import load_workbook


def classify_many(reason: str, best: str) -> list[str]:
    r = reason.lower()
    b = best.strip()
    categories: list[str] = []

    if ("volume mismatch" in r) or ("no_volume" in r) or ("volume not extracted" in r):
        categories.append("A")

    if (
        "extra words" in r
        or "multiple_match" in r
        or "low_score" in r
        or "score below exact threshold" in r
    ):
        categories.append("B")

    if "aroma/variant mismatch" in r:
        categories.append("C")

    if ("brand mismatch" in r) or ("unknown_brand" in r) or ("brand not extracted" in r):
        categories.append("D")

    if (not b) or ("no candidates found by matcher index" in r):
        categories.append("E")

    if (
        "not extracted from source name" in r
        or "category not extracted" in r
        or "volume not extracted" in r
        or "brand not extracted" in r
    ):
        categories.append("F")

    if not categories:
        categories.append("B")

    # Preserve first-seen order and remove duplicates.
    deduped = []
    seen = set()
    for code in categories:
        if code not in seen:
            deduped.append(code)
            seen.add(code)
    return deduped


def main() -> None:
    diag_path = Path("output/REVISION_MATCH_DIAGNOSTICS_10.07.24.xlsx")
    wb = load_workbook(diag_path, data_only=True)
    ws = wb.active

    headers = [str(c.value or "").strip() for c in ws[1]]
    idx = {h: i for i, h in enumerate(headers)}

    rows = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        original = str(r[idx["ORIGINAL_PRODUCT_NAME"]] or "").strip()
        normalized = str(r[idx["NORMALIZED_PRODUCT_NAME"]] or "").strip()
        best = str(r[idx["BEST_MASTER_CANDIDATE"]] or "").strip()
        score = float(r[idx["MATCHING_SCORE"]] or 0)
        reason = str(r[idx["EXACT_MATCH_FAIL_REASON"]] or "").strip()
        if not original:
            continue
        rows.append(
            {
                "original": original,
                "normalized": normalized,
                "best": best,
                "score": score,
                "reason": reason,
            }
        )

    labels = {
        "A": "Volume formatting",
        "B": "Extra words",
        "C": "Word order",
        "D": "Brand normalization",
        "E": "Missing in MASTER",
        "F": "Possible parser issue",
    }

    bucket = defaultdict(list)
    for row in rows:
        for code in classify_many(row["reason"], row["best"]):
            bucket[code].append(row)

    print(f"TOTAL_REVIEW_ROWS={len(rows)}")
    for code in ["A", "B", "C", "D", "E", "F"]:
        group = bucket.get(code, [])
        print(f"CAT|{code}|{labels[code]}|COUNT={len(group)}")
        for ex in group[:3]:
            short_reason = ex["reason"]
            if len(short_reason) > 220:
                short_reason = short_reason[:220] + "..."
            print("EX|" + code + "|" + ex["original"].replace("|", "/"))
            print("RS|" + code + "|" + short_reason.replace("|", "/"))
            print("BC|" + code + "|" + (ex["best"] or "<none>").replace("|", "/"))


if __name__ == "__main__":
    main()
