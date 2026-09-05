from pathlib import Path

p = Path(r"svo\normalizer.py")
text = p.read_text(encoding="utf-8")

start_marker = '            if item.category == "'
category_marker = "РџРѕРґРіСѓР·РЅРёРєРё"

start = text.find(start_marker + category_marker + '":')
assert start >= 0, "DIAPER CATEGORY BLOCK NOT FOUND"

end = text.find("\n            elif item.category ==", start)
assert end >= 0, "NEXT CATEGORY BLOCK NOT FOUND"

new_block = (
    '            if item.category == "' + category_marker + '":\n'
    '                # MASTER: BOSSFIX diapers use canonical Size 1..6.\n'
    '                size_match = re.search(\n'
    '                    r"(?:в„–\\s*|#\\s*)([1-6])\\b",\n'
    '                    text,\n'
    '                    flags=re.IGNORECASE,\n'
    '                )\n'
    '                if size_match:\n'
    '                    candidate = f"Size {size_match.group(1)}"\n'
)

text = text[:start] + new_block + text[end:]
p.write_text(text, encoding="utf-8")
print("DIAPER SIZE PATCH APPLIED")
