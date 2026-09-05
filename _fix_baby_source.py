from pathlib import Path

p = Path("svo/normalizer.py")
t = p.read_text(encoding="utf-8")

old = '''            elif item.volume == "1,5 \\u041b":
                variant = str(item.variant or item.aroma or "").strip().upper()
                if variant != "BABY":
                    item.brand = "SVO Elegant"
'''

new = '''            elif item.volume == "1,5 \\u041b":
                # At this point variant/aroma are not populated yet.
                # Detect the dedicated SVO Baby position directly from source text.
                if "BABY" not in text.upper():
                    item.brand = "SVO Elegant"
'''

if old not in t:
    raise SystemExit("BABY ROUTING CONDITION NOT FOUND")

t = t.replace(old, new, 1)
p.write_text(t, encoding="utf-8")

print("BABY SOURCE ROUTING FIXED")
