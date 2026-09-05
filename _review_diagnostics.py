import openpyxl
from svo.loader import Loader
from svo.normalizer import Normalizer
from svo.matcher import Matcher
from svo.models import ArrivalItem

review_file = "output/price_review.xlsx"

wb = openpyxl.load_workbook(review_file, data_only=True)
ws = wb["PRICE_REVIEW"]

masters = Loader().load_master("output/MASTER_DATASET.xlsx")
normalizer = Normalizer()
matcher = Matcher(masters)

print("=" * 100)
print("REVIEW DIAGNOSTICS")
print("=" * 100)

for row_num, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
    article = row[0]
    source_name = row[1]

    if not source_name:
        continue

    item = ArrivalItem(
        row_number=row_num,
        source_name=str(source_name),
    )

    normalized = normalizer.normalize(item)

    # Собираем кандидатов и их оценки, не меняя результат MATCH.
    candidates = matcher._collect_candidates(normalized)
    scored = []

    for candidate in candidates:
        detail = matcher._score_detail(normalized, candidate)
        scored.append((float(detail["score"]), candidate, detail))

    scored.sort(key=lambda x: x[0], reverse=True)

    print()
    print("-" * 100)
    print(f"ROW={row_num} ARTICLE={article}")
    print(f"SOURCE   : {source_name}")
    print(f"CATEGORY : {normalized.category!r}")
    print(f"BRAND    : {normalized.brand!r}")
    print(f"VOLUME   : {normalized.volume!r}")
    print(f"VARIANT  : {normalized.variant!r}")
    print(f"AROMA    : {normalized.aroma!r}")
    print()

    if not scored:
        print("CANDIDATES: NONE")
        continue

    print("TOP CANDIDATES:")

    for rank, (score, candidate, detail) in enumerate(scored[:5], start=1):
        print(
            f"{rank}. SCORE={score:.2f} "
            f"SKU={candidate.sku} "
            f"MASTER={candidate.master_name!r}"
        )
        print(
            f"   CATEGORY={candidate.category!r} "
            f"BRAND={candidate.brand!r} "
            f"VARIANT={candidate.variant!r} "
            f"VOLUME={candidate.volume!r} "
            f"AROMA={candidate.aroma!r}"
        )
        print(f"   BREAKDOWN={detail['breakdown']}")
        print(f"   REJECTION={detail['rejection_reason']}")

print()
print("=" * 100)
print("END")
print("=" * 100)
