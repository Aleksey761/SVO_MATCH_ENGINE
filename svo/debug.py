from pathlib import Path

from svo.loader import Loader
from svo.normalizer import Normalizer
from svo.matcher import Matcher


loader = Loader()

master = loader.load_master(Path("data/MASTER.xlsx"))
arrival = loader.load_arrival(Path("data/ARRIVAL.xlsx"))

normalizer = Normalizer()

for item in arrival:
    normalizer.normalize(item)

matcher = Matcher(master)

print("=" * 70)
print("MASTER:", len(master))
print("ARRIVAL:", len(arrival))
print("=" * 70)

review_count = 0

for i, item in enumerate(arrival):
    result = matcher.match(item)

    if result.status == "REVIEW":
        review_count += 1

        print("\n" + "=" * 70)
        print("INDEX:", i)
        print("SOURCE :", result.source_name)
        print("CATEGORY:", result.category)
        print("BRAND   :", result.brand)
        print("VOLUME  :", result.volume)
        print("AROMA   :", result.aroma)
        print("STATUS  :", result.status)
        print("CONF    :", result.confidence)
        print("REASONS :", result.review_reasons)
        print("CANDIDATES:")
        for c in result.candidates:
            print("   ", c)

        break

print("\nREVIEW FOUND:", review_count)