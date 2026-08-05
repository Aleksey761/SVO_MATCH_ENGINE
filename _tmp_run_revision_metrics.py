from pathlib import Path

from svo.engine import Engine


def main() -> None:
    base = Path("F:/SVO/AI/SVO_MATCH_ENGINE")
    revision_file = sorted(
        [p for p in Path("F:/SVO/Склад").glob("*.xlsx") if "10.07.24" in p.name and not p.name.startswith("~$")]
    )[0]

    result = Engine().run(
        master_file=None,
        arrival_file=revision_file,
        output_file=base / "output" / "RESULT 10.07.24.xlsx",
        input_dir=base,
    )

    items = result.get("items", [])
    empty_sku = sum(1 for item in items if not str(getattr(item, "sku", None) or "").strip())

    print(f"MATCH={result.get('match')}")
    print(f"REVIEW={result.get('review')}")
    print(f"EMPTY_SKU={empty_sku}")


if __name__ == "__main__":
    main()
