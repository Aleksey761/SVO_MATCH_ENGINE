from collections import Counter

from svo.loader import Loader
from svo.matcher import Matcher
from svo.normalizer import Normalizer

loader = Loader()
master = loader.load_master("data/MASTER.xlsx")
arrival = loader.load_arrival("data/ARRIVAL.xlsx")

normalizer = Normalizer()
for item in arrival:
    normalizer.normalize(item)

matcher = Matcher(master)
status = Counter()
reasons = Counter()

for item in arrival:
    result = matcher.match(item)
    status[result.status] += 1
    for reason in result.review_reasons:
        reasons[reason] += 1

print("MATCH", status["MATCH"])
print("REVIEW", status["REVIEW"])
print("REASONS", dict(reasons))
