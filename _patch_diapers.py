from pathlib import Path

p = Path(r"svo\normalizer.py")
text = p.read_text(encoding="utf-8")

start = text.find('            if item.category == "Подгузники":')
assert start >= 0, "DIAPER CATEGORY BLOCK NOT FOUND"

end = text.find('\n            elif item.category ==', start)
assert end >= 0, "NEXT CATEGORY BLOCK NOT FOUND"

new_block = """            if item.category == "Подгузники":
                # MASTER identifies BOSSFIX diapers by canonical Size 1..6.
                size_match = re.search(
                    r"(?:№\\s*|#\\s*)([1-6])\\b",
                    text,
                    flags=re.IGNORECASE,
                )
                if size_match:
                    candidate = f"Size {size_match.group(1)}"
"""

text = text[:start] + new_block + text[end:]
p.write_text(text, encoding="utf-8")
print("DIAPER SIZE PATCH APPLIED")
