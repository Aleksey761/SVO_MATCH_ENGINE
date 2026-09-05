from pathlib import Path

p = Path("svo/sales_loader.py")
s = p.read_text(encoding="utf-8")

old = '''            if is_block_header(text):
                current_context = text
                match_name = text
            elif current_context and len(text) < 40:
                match_name = f"{current_context} {text}".strip()
            else:
                match_name = text
                if is_block_header(text):
                    current_context = text
'''

new = '''            # Powder blocks in SALES are hierarchical:
            # "орошок 1.3 омашка" starts the 1.3 kg block,
            # while following rows contain only the aroma.
            powder_match = re.match(
                r"^орошок\\\\s+(\\\\d+(?:[.,]\\\\d+)?)\\\\s+(.+)$",
                text,
                re.IGNORECASE,
            )

            if powder_match:
                size = powder_match.group(1).replace(",", ".")
                current_context = f"орошок стиральный SVO {size} кг"
                match_name = f"{current_context} {powder_match.group(2).strip()}"
            elif current_context and len(text) < 40:
                match_name = f"{current_context} {text}".strip()
            else:
                match_name = text
                if is_block_header(text):
                    current_context = text
'''

if old not in s:
    raise SystemExit("CURRENT SALES CONTEXT BLOCK NOT FOUND")

s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
print("POWDER BLOCK CONTEXT FIX APPLIED")
