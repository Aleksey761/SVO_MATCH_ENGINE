from pathlib import Path

p = Path("svo/normalizer.py")
t = p.read_text(encoding="utf-8")

old = '''                variant = self._normalize_value(item.variant or item.aroma or "")
                if variant != "BABY":
                    item.brand = "SVO Elegant"
'''

new = '''                variant = str(item.variant or item.aroma or "").strip().upper()
                if variant != "BABY":
                    item.brand = "SVO Elegant"
'''

if old not in t:
    raise SystemExit("BABY ROUTING BLOCK NOT FOUND")

t = t.replace(old, new, 1)
p.write_text(t, encoding="utf-8")

print("BABY ROUTING FIXED")
