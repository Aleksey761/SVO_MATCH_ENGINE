from pathlib import Path

from svo.engine import Engine

print("SCRIPT_START", flush=True)

base = Path("F:/SVO/AI/SVO_MATCH_ENGINE")
rev = sorted(
    [
        p
        for p in Path("F:/SVO/Склад").glob("*.xlsx")
        if "10.07.24" in p.name and not p.name.startswith("~$")
    ]
)[0]

try:
    res = Engine().run(
        master_file=None,
        arrival_file=rev,
        output_file=base / "output" / "RESULT 10.07.24.xlsx",
        input_dir=base,
    )
    items = res.get("items", [])
    empty = sum(1 for item in items if not str(getattr(item, "sku", None) or "").strip())

    print("MATCH", res.get("match"), flush=True)
    print("REVIEW", res.get("review"), flush=True)
    print("EMPTY_SKU", empty, flush=True)
except Exception as exc:
    print("SCRIPT_ERROR", type(exc).__name__, str(exc), flush=True)
    raise
