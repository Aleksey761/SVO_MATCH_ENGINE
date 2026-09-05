from collections import Counter
from pathlib import Path

from svo.engine import Engine

base = Path("F:/SVO/AI/SVO_MATCH_ENGINE")
rev_candidates = [
    p
    for p in Path("F:/SVO/Склад").glob("*.xlsx")
    if "10.07.24" in p.name and not p.name.startswith("~$")
]
rev = sorted(rev_candidates)[0]

result = Engine().run(
    master_file=None,
    arrival_file=rev,
    output_file=base / "output" / "RESULT 10.07.24.xlsx",
    input_dir=base,
)

reviews = [item for item in result["items"] if item.status == "REVIEW"]
print("REVIEWS", len(reviews))

categories = Counter((item.category or "None") for item in reviews)
brands = Counter((item.brand or "None") for item in reviews)
volumes = Counter((item.volume or "None") for item in reviews)
print("TOP_CATS", categories.most_common(12))
print("TOP_BRANDS", brands.most_common(12))
print("TOP_VOLUMES", volumes.most_common(12))

for item in reviews[:30]:
    print("---")
    print(item.source_name)
    print(
        "cat=", item.category,
        "brand=", item.brand,
        "vol=", item.volume,
        "aroma=", item.aroma,
        "variant=", item.variant,
        "sku=", item.sku,
    )
