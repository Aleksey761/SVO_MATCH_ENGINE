from pathlib import Path

p = Path(r"svo\normalizer.py")
text = p.read_text(encoding="utf-8")

old = '''            variant_value = str(item.variant or item.aroma or "").strip().upper()
            is_baby = variant_value == "BABY"
'''

new = '''            is_baby = bool(re.search(r"\\bbaby\\b", text, flags=re.IGNORECASE))
'''

assert old in text, "BABY ROUTING BLOCK NOT FOUND"
text = text.replace(old, new, 1)

p.write_text(text, encoding="utf-8")
print("BABY ROUTING FIX OK")
