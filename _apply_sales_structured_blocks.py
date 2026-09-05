from pathlib import Path

p = Path("svo/sales_loader.py")
s = p.read_text(encoding="utf-8")

marker = '        current_context = ""\n'
if marker not in s:
    raise SystemExit("CURRENT_CONTEXT_MARKER_NOT_FOUND")

insert = '''        current_context = ""
        current_context_type = ""

        powder_aromas = {
            "Ш": "Rose",
            "": "Lavender",
            "Ы": "Black",
            "": "Rose",
            "С": "Snowdrop",
            "С": "Snowdrop",
            "Ы": "Mountain Breeze",
            "": "Mountain Breeze",
            "Ы": "Mountain Breeze",
            "": "Lemon",
            "ТС": "Baby",
        }

        elegant_aromas = {
            "WHITE": "White",
            "MANGO": "Mango",
            "FLORIAL MIST": "Floral Mist",
            "MIDNIGHT": "Midnight",
            "SPRING": "Spring",
            "SWEET TROPIK": "Sweet Tropic",
            "VELVET": "Velvet",
            "DREAM": "Dream",
            "BLACK": "Black",
        }

'''
s = s.replace(marker, insert, 1)

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

new = '''            powder = re.match(
                r"^орошок\\\\s+(\\\\d+(?:[.,]\\\\d+)?)\\\\s+(.+)$",
                text,
                re.IGNORECASE,
            )

            if powder:
                size = powder.group(1).replace(",", ".")
                aroma_raw = powder.group(2).strip().upper()
                aroma = powder_aromas.get(aroma_raw, powder.group(2).strip())
                current_context = f"орошок стиральный SVO {size} кг"
                current_context_type = "powder"
                match_name = f"{current_context} {aroma}"

            elif re.match(r"^ель кондиционер\\\\s+1400\\\\s+MAGINA$", text, re.IGNORECASE):
                current_context = "ондиционер SVO Magina 1,44 л"
                current_context_type = "magina"
                match_name = current_context

            elif re.match(r"^SVO\\\\s+1500\\\\s+ELEGANT\\\\s+WHITE$", text, re.IGNORECASE):
                current_context = "С SVO Elegant 1,5 л"
                current_context_type = "elegant_15"
                match_name = f"{current_context} White"

            elif current_context_type == "powder" and len(text) < 40:
                aroma = powder_aromas.get(text.strip().upper(), text.strip())
                match_name = f"{current_context} {aroma}"

            elif current_context_type == "elegant_15" and len(text) < 40:
                aroma = elegant_aromas.get(text.strip().upper(), text.strip())
                match_name = f"{current_context} {aroma}"

            elif current_context_type == "magina" and len(text) < 40:
                match_name = f"{current_context} {text.strip()}"

            else:
                match_name = text
                if is_block_header(text):
                    current_context = text
                    current_context_type = "generic"
'''

if old not in s:
    raise SystemExit("CURRENT_CONTEXT_LOGIC_NOT_FOUND")

s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
print("SALES STRUCTURED BLOCK PARSER APPLIED")
