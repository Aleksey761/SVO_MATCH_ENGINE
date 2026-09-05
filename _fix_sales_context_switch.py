from pathlib import Path

p = Path("svo/sales_loader.py")
s = p.read_text(encoding="utf-8")

s = s.replace(
    'size = powder_match.group(1).replace(",", ".")',
    'size_raw = powder_match.group(1).replace(",", ".")\n                size = str(float(size_raw)).rstrip("0").rstrip(".")',
    1,
)

old = '''            elif text.upper() == magina_header.upper():
                current_context = "\\u041a\\u043e\\u043d\\u0434\\u0438\\u0446\\u0438\\u043e\\u043d\\u0435\\u0440 SVO Magina 1,44 \\u043b"
                current_context_type = "magina"
                match_name = current_context

            elif text.upper() == elegant_header.upper():
                current_context = "\\u0416\\u041c\\u0421 SVO Elegant 1,5 \\u043b"
                current_context_type = "elegant_15"
                match_name = f"{current_context} White"
'''

new = '''            elif text.upper() == elegant_header.upper():
                current_context = "\\u0416\\u041c\\u0421 SVO Elegant 1,5 \\u043b"
                current_context_type = "elegant_15"
                match_name = f"{current_context} White"

            elif text.upper() == magina_header.upper():
                current_context = "\\u041a\\u043e\\u043d\\u0434\\u0438\\u0446\\u0438\\u043e\\u043d\\u0435\\u0440 SVO Magina 1,44 \\u043b"
                current_context_type = "magina"
                match_name = current_context
'''

if old not in s:
    raise SystemExit("MAGINA/ELEGANT BLOCK NOT FOUND")

s = s.replace(old, new, 1)

# Unknown standalone rows must not inherit the previous structured block.
old2 = '''            elif current_context_type == "magina" and len(text) < 40:
                match_name = f"{current_context} {text}"

            else:
                match_name = text

                if len(text) >= 15:
                    current_context = ""
                    current_context_type = ""
'''

new2 = '''            elif current_context_type == "magina" and len(text) < 40:
                match_name = f"{current_context} {text}"

            else:
                match_name = text
                current_context = ""
                current_context_type = ""
'''

if old2 not in s:
    raise SystemExit("CONTEXT FALLBACK BLOCK NOT FOUND")

s = s.replace(old2, new2, 1)

p.write_text(s, encoding="utf-8")
print("SALES CONTEXT SWITCH FIXED")
