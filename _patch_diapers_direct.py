from pathlib import Path

p = Path(r"svo\normalizer.py")
text = p.read_text(encoding="utf-8")

category = "РџРѕРґРіСѓР·РЅРёРєРё"
start_marker = '            if item.category == "' + category + '":'
start = text.find(start_marker)
assert start >= 0, "DIAPER BLOCK NOT FOUND"

next_branch = text.find("\n            elif item.category ==", start)
assert next_branch >= 0, "NEXT CATEGORY BLOCK NOT FOUND"

new_block = (
    '            if item.category == "' + category + '":\n'
    '                # MASTER: BOSSFIX diapers use canonical Size 1..6.\n'
    '                # Assign directly and bypass generic aroma normalization.\n'
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

text = text[:start] + new_block + text[next_branch:]
p.write_text(text, encoding="utf-8")
print("DIAPER DIRECT SIZE PATCH APPLIED")
