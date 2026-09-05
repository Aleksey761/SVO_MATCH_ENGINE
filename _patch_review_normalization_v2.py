from pathlib import Path

p = Path("svo/normalizer.py")
t = p.read_text(encoding="utf-8")

# ------------------------------------------------------------
# 1. Extend category detection with PRICE-specific categories.
# ------------------------------------------------------------
old = '''        if re.search(r"\\bshamp(?:oo|un)\\b", lower):
            for category, patterns in self._category_rules:
                haystack = " ".join([category, *patterns]).upper()
                if "\\u0428\\u0410\\u041c\\u041f\\u0423\\u041d" in haystack:
                    return category
        return None
'''

new = '''        if re.search(r"\\bshamp(?:oo|un)\\b", lower):
            for category, patterns in self._category_rules:
                haystack = " ".join([category, *patterns]).upper()
                if "\\u0428\\u0410\\u041c\\u041f\\u0423\\u041d" in haystack:
                    return category

        # PRICE-specific categories.
        if re.search(r"\\b(?:пятновыводитель|пятновыводит)", lower):
            return "ятновыводитель"

        if re.search(r"средств[оа]\\s+(?:д/|для\\s+)?посуд", lower):
            return "осуда моющее ср-во"

        return None
'''

if old not in t:
    raise SystemExit("CATEGORY PATCH TARGET NOT FOUND")
t = t.replace(old, new, 1)

# ------------------------------------------------------------
# 2. Replace packaging tails before aroma normalization.
# ------------------------------------------------------------
old = '''        # Remove packaging/count tails from PRICE names.
        cleaned = re.sub(r"\\s*[/\\\\]\\s*\\d+\\s*$", "", cleaned).strip()
'''

new = '''        # Remove PRICE packaging/count tails:
        #   /12, \\\\ 7, / 6, 90/12, 54/9, 30/6, etc.
        cleaned = re.sub(r"\\s*\\d+\\s*[/\\\\]\\s*\\d+\\s*$", "", cleaned)
        cleaned = re.sub(r"\\s*[/\\\\]\\s*\\d+\\s*$", "", cleaned)
        cleaned = cleaned.strip(" /\\\\-")
'''

if old not in t:
    raise SystemExit("PACKAGING PATCH TARGET NOT FOUND")
t = t.replace(old, new, 1)

# ------------------------------------------------------------
# 3. Add PRICE aliases immediately before _normalize_aroma().
# ------------------------------------------------------------
marker = '''            if candidate:
                normalized_aroma = self._normalize_aroma(candidate)
'''

replacement = '''            if candidate:
                # PRICE aliases / Cyrillic-to-MASTER aroma normalization.
                aliases = {
                    "MEDINA": "MAGINA",
                    "": "MAGINA",
                    "MENTOL": "MINT",
                    "Т": "MINT",
                    "Я ССТЬ": "MOUNTAIN BREEZE",
                    "Ы ": "MOUNTAIN BREEZE",
                    "": "ROSE",
                    "С": "SNOWDROP",
                    "ШХ": "SHEIKH",
                    "Я": "PASSION FRUIT",
                    "": "PASSION FRUIT",
                    "ЬС": "ORANGE",
                    "Т": "GRAPEFRUIT",
                    "Я": "APPLE",
                    "ТЫ": "YELLOW",
                    "ТЫ": "YELLOW",
                    "СЫ": "RED",
                    "Ы": "PINK",
                    "С": "BLUE",
                    "ТЫ": "PURPLE",
                    "Ы": "BLACK",
                    "Ы": "BLACK",
                }

                normalized_candidate = candidate.strip()
                upper_candidate = normalized_candidate.upper()
                for source, target in aliases.items():
                    upper_candidate = re.sub(
                        rf"\\b{re.escape(source)}\\b",
                        target,
                        upper_candidate,
                        flags=re.IGNORECASE,
                    )
                candidate = upper_candidate

                normalized_aroma = self._normalize_aroma(candidate)
'''

if marker not in t:
    raise SystemExit("AROMA PATCH TARGET NOT FOUND")
t = t.replace(marker, replacement, 1)

# ------------------------------------------------------------
# 4. Explicit shampoo fallback.
# ------------------------------------------------------------
old = '''        if re.search(r"\\bshamp(?:oo|un)\\b", lower):
'''

new = '''        if re.search(r"\\b(?:shamp(?:oo|un)|шампун)", lower):
'''

if old not in t:
    raise SystemExit("SHAMPOO PATCH TARGET NOT FOUND")
t = t.replace(old, new, 1)

p.write_text(t, encoding="utf-8")
print("REVIEW NORMALIZATION PATCH V2 OK")
