from pathlib import Path

p = Path("svo/normalizer.py")
t = p.read_text(encoding="utf-8")

old = '''        if item.brand == "SVO" and item.category == "С":
            if item.volume in {"1 ", "1,5 "}:
                item.brand = "SVO Elegant"
            elif item.volume == "2,7 ":
                item.category = "С 3в1"
'''

new = '''        if item.brand == "SVO" and item.category == "С":
            # MASTER canonical routing:
            # 1 l SVO liquid detergents -> SVO Elegant.
            # 1.5 l SVO liquid detergents -> SVO Elegant,
            # except the dedicated SVO Baby position.
            # 2.7 l is intentionally NOT routed here:
            # MASTER contains both Conditioner and С 3в1 blocks.
            if item.volume == "1 ":
                item.brand = "SVO Elegant"
            elif item.volume == "1,5 ":
                variant = self._normalize_value(item.variant or item.aroma or "")
                if variant != "BABY":
                    item.brand = "SVO Elegant"
'''

if old not in t:
    raise SystemExit("SVO ROUTING BLOCK NOT FOUND")

t = t.replace(old, new, 1)
p.write_text(t, encoding="utf-8")
print("SVO ELEGANT ROUTING PATCH OK")
