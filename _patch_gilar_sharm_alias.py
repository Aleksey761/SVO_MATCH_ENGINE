from pathlib import Path

p = Path(r"svo\normalizer.py")
text = p.read_text(encoding="utf-8")

anchor = '"MAGINA": ["MEDINA"],'
assert anchor in text, "AROMA ALIAS ANCHOR NOT FOUND"

if '"CHARM": ["SHARM"]' in text:
    print("GILAR SHARM -> CHARM ALIAS ALREADY PRESENT")
else:
    text = text.replace(
        anchor,
        anchor + '\n        "CHARM": ["SHARM"],',
        1,
    )
    p.write_text(text, encoding="utf-8")
    print("GILAR SHARM -> CHARM ALIAS APPLIED")
