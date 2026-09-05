from pathlib import Path
from collections import Counter

from svo.loader import Loader
from svo.normalizer import Normalizer
from svo.matcher import Matcher


def main():
    loader = Loader()

    master_file, arrival_file, sales_file, arrival_date, sales_date = loader.discover_workbooks(
        Path("data"),
        require_sales=False,
    )

    master = loader.load_master(master_file)
    arrival = loader.load_arrival(arrival_file)

    normalizer = Normalizer()

    for item in arrival:
        normalizer.normalize(item)

    matcher = Matcher(master)

    match_count = 0
    review_count = 0
    reason_counter = Counter()

    print("=" * 70)
    print(f"MASTER FILE : {master_file.name}")
    print(f"ARRIVAL FILE: {arrival_file.name}")
    print(f"SALES FILE  : {sales_file.name if sales_file else None}")
    print(f"ARRIVAL DATE: {arrival_date}")
    print(f"SALES DATE  : {sales_date}")
    print(f"MASTER : {len(master)}")
    print(f"ARRIVAL: {len(arrival)}")
    print("=" * 70)

    for item in arrival:
        result = matcher.match(item)

        # сохраняем результат в объекте
        item.status = result.status
        item.review_reasons = result.review_reasons
        item.candidates = result.candidates
        item.confidence = result.confidence

        if result.status == "MATCH":
            match_count += 1
        else:
            review_count += 1

            for reason in result.review_reasons:
                reason_counter[reason] += 1

    print()
    print(f"MATCH : {match_count}")
    print(f"REVIEW: {review_count}")

    print()
    print("REVIEW REASONS")
    print("-" * 40)

    for reason, count in reason_counter.most_common():
        print(f"{reason:25} {count}")

    print()
    print("=" * 70)
    print("FIRST 20 MULTIPLE MATCHES")
    print("=" * 70)

    shown = 0

    for item in arrival:

        if item.status != "REVIEW":
            continue

        if "MULTIPLE_MATCH" not in item.review_reasons:
            continue

        print()
        print(item.source_name)
        print(f"category : {item.category}")
        print(f"brand    : {item.brand}")
        print(f"volume   : {item.volume}")
        print(f"aroma    : {item.aroma}")
        print(f"score    : {item.confidence}")

        print("Candidates:")

        for candidate in item.candidates:
            print(
                f"  {candidate.sku:10} | "
                f"{candidate.category:15} | "
                f"{candidate.brand:8} | "
                f"{candidate.volume:6} | "
                f"{candidate.aroma or candidate.variant}"
            )

        shown += 1

        if shown >= 20:
            break


if __name__ == "__main__":
    main()
