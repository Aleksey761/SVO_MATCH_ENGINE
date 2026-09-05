from pathlib import Path

p = Path("svo/normalizer.py")
t = p.read_text(encoding="utf-8")

old = '''        if item.brand == "SVO" and item.category == "–њЎ":
            if item.volume in {"1 ›", "1,5 ›"}:
                item.brand = "SVO Elegant"
            elif item.volume == "2,7 ›":
                item.category = "–њЎ 3І1"
'''

new = '''        if item.brand == "SVO" and item.category == "\\u0416\\u041c\\u0421":
            # MASTER canonical routing:
            # 1 l -> SVO Elegant
            # 1.5 l -> SVO Elegant, except SVO Baby
            # 2.7 l is intentionally left unchanged here.
            if item.volume == "1 \\u041b":
                item.brand = "SVO Elegant"
            elif item.volume == "1,5 \\u041b":
                variant = self._normalize_value(item.variant or item.aroma or "")
                if variant != "BABY":
                    item.brand = "SVO Elegant"
'''

if old not in t:
    raise SystemExit("EXACT SVO ROUTING BLOCK NOT FOUND")

t = t.replace(old, new, 1)
p.write_text(t, encoding="utf-8")
print("SVO ROUTING FIXED")
