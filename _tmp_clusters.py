from collections import Counter, defaultdict

from svo.loader import Loader
from svo.matcher import Matcher
from svo.normalizer import Normalizer


def esc(value):
    if value is None:
        return "None"
    return str(value).encode("unicode_escape").decode("ascii")

loader = Loader()
master = loader.load_master("data/MASTER.xlsx")
arrival = loader.load_arrival("data/ARRIVAL.xlsx")
normalizer = Normalizer()
for item in arrival:
    normalizer.normalize(item)

matcher = Matcher(master)
status = Counter()
reasons = Counter()
score_buckets = Counter()
groups = Counter()
examples = defaultdict(list)

for item in arrival:
    result = matcher.match(item)
    status[result.status] += 1
    for reason in result.review_reasons:
        reasons[reason] += 1

    if result.status != "REVIEW":
        continue

    score_buckets[result.confidence] += 1
    key = (item.category, item.brand, item.volume, len(result.candidates))
    groups[key] += 1
    if len(examples[key]) < 2:
        examples[key].append((item.source_name, item.aroma, result.confidence, [c.sku for c in result.candidates[:5]]))

print("STATUS", status)
print("REASONS", reasons)
print("SCORES", score_buckets.most_common(12))
for key, count in groups.most_common(16):
    category, brand, volume, candidate_count = key
    print("GROUP", count, esc(category), esc(brand), esc(volume), candidate_count)
    for source_name, aroma, confidence, skus in examples[key]:
        print(" ", esc(source_name), "|", esc(aroma), "|", confidence, "|", skus)
