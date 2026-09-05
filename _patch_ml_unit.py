from pathlib import Path

p = Path(r"svo\normalizer.py")
text = p.read_text(encoding="utf-8")

old = '''            return f"{self._format_decimal(value)} "

        if unit in {"кг", "kg", "килограмм", "килограмма", "килограммов"}:
'''
new = '''            return f"{self._format_decimal(value)} "

        if unit in {"кг", "kg", "килограмм", "килограмма", "килограммов"}:
'''

# Replace only the first occurrence after the ml branch.
pos = text.find('        if unit in {"мл", "ml"}:')
assert pos >= 0, "ML BRANCH NOT FOUND"
tail = text[pos:]
assert old in tail, "ML RETURN TARGET NOT FOUND"
tail = tail.replace(old, new, 1)
text = text[:pos] + tail

p.write_text(text, encoding="utf-8")
print("ML UNIT PATCH OK")
