from pathlib import Path

p = Path("svo/sales_loader.py")
s = p.read_text(encoding="utf-8")

old = '''            non_empty_indexes = [index for index, header in enumerate(normalized_headers) if header]
            if len(non_empty_indexes) == 1:
                return non_empty_indexes[0]

'''

if old not in s:
    raise SystemExit("OLD SALES HEADER FALLBACK NOT FOUND")

s = s.replace(old, "", 1)

p.write_text(s, encoding="utf-8")
print("SALES NAME COLUMN DETECTION FIXED")
