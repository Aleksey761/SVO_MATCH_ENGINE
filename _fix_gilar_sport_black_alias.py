from pathlib import Path

path = Path('svo/matcher.py')
text = path.read_text(encoding='utf-8')
needle = 'CONFIRMED_PRICE_ALIASES'
if needle not in text:
    raise SystemExit('CONFIRMED_PRICE_ALIASES not found in svo/matcher.py')
marker = '"GILAR Шампунь 400 мл мужс. SPORT от перх. \\12": "SKU-012",'
if marker in text:
    print('GILAR SPORT BLACK alias already present')
    raise SystemExit(0)
# Add the exact source alias beside the existing confirmed aliases.
insert_at = text.find(needle)
line_start = text.find('\n', insert_at) + 1
text = text[:line_start] + '    ' + marker + '\n' + text[line_start:]
path.write_text(text, encoding='utf-8')
print('GILAR SPORT BLACK ALIAS FIXED')
