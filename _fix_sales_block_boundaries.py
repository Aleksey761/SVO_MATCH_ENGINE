from pathlib import Path

p = Path("svo/sales_loader.py")
s = p.read_text(encoding="utf-8")

old = '''            elif text.upper() == elegant_header.upper():
                current_context = "\\u0416\\u041c\\u0421 SVO Elegant 1,5 \\u043b"
                current_context_type = "elegant_15"
                match_name = f"{current_context} White"

            elif text.upper() == magina_header.upper():
'''

new = '''            elif re.match(
                r"^SVO\\s+1500\\s+ELEGANT\\s+WHITE$",
                text,
                re.IGNORECASE,
            ):
                current_context = "\\u0416\\u041c\\u0421 SVO Elegant 1,5 \\u043b"
                current_context_type = "elegant_15"
                match_name = f"{current_context} White"

            elif text.upper() == magina_header.upper():
'''

if old not in s:
    raise SystemExit("ELEGANT CONTEXT BLOCK NOT FOUND")

s = s.replace(old, new, 1)

# Oxgeen starts a new independent block and must terminate powder context.
needle = '''            elif current_context_type == "powder" and len(text) < 40:
                aroma = powder_aromas.get(
                    text.upper(),
                    text,
                )
                match_name = f"{current_context} {aroma}"
'''

replacement = '''            elif current_context_type == "powder" and len(text) < 40:
                if text.upper().startswith("OXGEEN"):
                    current_context = ""
                    current_context_type = ""
                    match_name = text
                else:
                    aroma = powder_aromas.get(
                        text.upper(),
                        text,
                    )
                    match_name = f"{current_context} {aroma}"
'''

if needle not in s:
    raise SystemExit("POWDER CONTEXT BLOCK NOT FOUND")

s = s.replace(needle, replacement, 1)

p.write_text(s, encoding="utf-8")
print("SALES BLOCK BOUNDARIES FIXED")
