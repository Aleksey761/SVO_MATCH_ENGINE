from pathlib import Path

p = Path("svo/matcher.py")
s = p.read_text(encoding="utf-8")

old = '''        if (
            "GILAR" in source
            and "SPORT" in source
            and "Х" in source
            and "Ш" in source
            and volume == "400 "
        ):
'''

new = '''        if (
            "GILAR" in source
            and "SPORT" in source
            and "Х" in source
            and "Ш" in source
            and "400 " in source
        ):
'''

if old not in s:
    raise SystemExit("OLD GILAR RULE NOT FOUND")

s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("GILAR SPORT BLACK RULE CORRECTED")
