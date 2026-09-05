from pathlib import Path

p = Path(r"svo\normalizer.py")
text = p.read_text(encoding="utf-8")

anchor = "        if item.brand:\n            candidate = self._cleanup_candidate(text, brand_match)\n"
assert anchor in text, "NORMALIZATION ANCHOR NOT FOUND"

if "GILAR 400/500 CATEGORY RULES" in text:
    print("GILAR 400/500 CATEGORY RULES ALREADY PRESENT")
else:
    insert = (
        "        # GILAR 400/500 CATEGORY RULES.\n"
        "        # MASTER distinguishes women, men and organic shampoo blocks.\n"
        '        if item.brand == "GILAR" and item.volume:\n'
        '            upper_text = text.upper()\n'
        '            upper_volume = item.volume.upper()\n'
        '            if upper_volume == "400 МЛ":\n'
        '                if "МУЖС" in upper_text:\n'
        '                    item.category = "Шампунь men"\n'
        '                elif "SHARM" in upper_text or "CHARM" in upper_text:\n'
        '                    item.category = "Шампунь women"\n'
        '            elif upper_volume == "500 МЛ" and "ДОЗАТ" in upper_text:\n'
        '                item.category = "Шампунь органический"\n'
    )
    text = text.replace(anchor, insert + anchor, 1)
    p.write_text(text, encoding="utf-8")
    print("GILAR 400/500 CATEGORY RULES APPLIED")
