from pathlib import Path

p = Path(r"svo\normalizer.py")
text = p.read_text(encoding="utf-8")

old_mojibake = '            if item.category == "РџРѕРґРіСѓР·РЅРёРєРё":'
old_russian = '            if item.category == "Подгузники":'

if old_mojibake in text:
    old = old_mojibake
elif old_russian in text:
    old = old_russian
else:
    raise AssertionError("DIAPER CATEGORY CONDITION NOT FOUND")

new = (
    '            if str(item.category or "").strip().upper() == "ПОДГУЗНИКИ":\n'
    '                # MASTER: BOSSFIX diapers use canonical Size 1..6.\n'
    '                # Extract the first standalone size number and assign it directly.\n'
    '                size_match = re.search(\n'
    '                    r"\\b([1-6])\\b",\n'
    '                    text,\n'
    '                    flags=re.IGNORECASE,\n'
    '                )\n'
    '                if size_match:\n'
    '                    size_value = f"Size {size_match.group(1)}"\n'
    '                    item.variant = size_value.upper()\n'
    '                    item.aroma = size_value.upper()\n'
    '                candidate = None\n'
)

text = text.replace(old, new, 1)
p.write_text(text, encoding="utf-8")
print("DIAPER CATEGORY CONDITION FIXED")
