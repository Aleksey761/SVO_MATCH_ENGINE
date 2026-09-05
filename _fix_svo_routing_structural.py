from pathlib import Path
import re

p = Path("svo/normalizer.py")
t = p.read_text(encoding="utf-8")

pattern = re.compile(
    r'        if item\.brand == "SVO" and item\.category == "[^"]+":\r?\n'
    r'            if item\.volume in \{"1 [^"]+", "1,5 [^"]+"\}:\r?\n'
    r'                item\.brand = "SVO Elegant"\r?\n'
    r'            elif item\.volume == "2,7 [^"]+":\r?\n'
    r'                item\.category = "[^"]+"\r?\n'
)

replacement = '''        if item.brand == "SVO" and item.category == "\\u0416\\u041c\\u0421":
            # MASTER canonical routing:
            # 1 l -> SVO Elegant
            # 1.5 l -> SVO Elegant, except SVO Baby
            # 2.7 l intentionally remains unchanged here.
            if item.volume == "1 \\u041b":
                item.brand = "SVO Elegant"
            elif item.volume == "1,5 \\u041b":
                variant = self._normalize_value(item.variant or item.aroma or "")
                if variant != "BABY":
                    item.brand = "SVO Elegant"
'''

new_t, count = pattern.subn(replacement, t, count=1)

if count != 1:
    raise SystemExit(f"ROUTING BLOCK NOT FOUND, replacements={count}")

p.write_text(new_t, encoding="utf-8")
print("SVO ROUTING STRUCTURAL PATCH OK")
