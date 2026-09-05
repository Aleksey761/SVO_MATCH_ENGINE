from pathlib import Path
import re

p = Path("svo/normalizer.py")
t = p.read_text(encoding="utf-8")

# 1. Remove packaging tails such as /12, \ 7, / 6
old = '''        cleaned = self._volume_re.sub("", candidate)
'''
new = '''        cleaned = self._volume_re.sub("", candidate)
        # Remove packaging/count tails from PRICE names.
        cleaned = re.sub(r"\\s*[/\\\\]\\s*\\d+\\s*$", "", cleaned).strip()
'''
if old in t and new not in t:
    t = t.replace(old, new, 1)

# 2. Add common PRICE aroma aliases before _normalize_aroma is called.
marker = '''    def _normalize_aroma(self, value: str) -> str:
'''
aliases = '''    _PRICE_REVIEW_ALIASES = {
        "": "MAGINA",
        "MEDINA": "MAGINA",
        "Т": "MINT",
        "MENTOL": "MINT",
        "Я ССТЬ": "MOUNTAIN BREEZE",
        "Ы ": "MOUNTAIN BREEZE",
        "": "ROSE",
        "С": "SNOWDROP",
        "ШХ": "SHEIKH",
        "Я": "PASSION FRUIT",
        "": "PASSION FRUIT",
        "ТЫ": "YELLOW",
        "ТЫ": "YELLOW",
        "СЫ": "RED",
        "Ы": "PINK",
        "С": "BLUE",
        "ТЫ": "PURPLE",
        "Ы": "BLACK",
        "Ы": "BLACK",
        "ЬС": "ORANGE",
        "Т": "GRAPEFRUIT",
        "Я": "APPLE",
    }

'''
if marker in t and "_PRICE_REVIEW_ALIASES" not in t:
    t = t.replace(marker, aliases + marker, 1)

# 3. Apply aliases inside _normalize_aroma.
old_call = '''        text = str(value).strip()
'''
new_call = '''        text = str(value).strip()
        upper_text = text.upper()
        for source, target in self._PRICE_REVIEW_ALIASES.items():
            upper_text = re.sub(
                rf"\\b{re.escape(source)}\\b",
                target,
                upper_text,
                flags=re.IGNORECASE,
            )
        text = upper_text
'''
# Restrict replacement to the first occurrence after _normalize_aroma.
pos = t.find(marker)
if pos >= 0:
    tail = t[pos:]
    if old_call in tail and "upper_text = text.upper()" not in tail[:tail.find("\\n", tail.find(old_call)+1)+1]:
        tail = tail.replace(old_call, new_call, 1)
        t = t[:pos] + tail

p.write_text(t, encoding="utf-8")
print("REVIEW NORMALIZATION PATCH CREATED")
