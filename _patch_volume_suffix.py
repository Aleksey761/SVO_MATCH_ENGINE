from pathlib import Path

p = Path(r"svo\normalizer.py")
text = p.read_text(encoding="utf-8")

replacements = [
    ('return f"{self._format_decimal(value)} "', 'return f"{self._format_decimal(value)} \\u041b"'),
    ('return f"{self._format_decimal(value / Decimal(\'1000\'))} "', 'return f"{self._format_decimal(value / Decimal(\'1000\'))} \\u041b"'),
]

for old, new in replacements:
    text = text.replace(old, new)

# Remaining three unit returns, in order: ML, KG, G.
text = text.replace(
    'return f"{self._format_decimal(value)} "',
    'return f"{self._format_decimal(value)} \\u041c\\u041b"',
    1,
)
text = text.replace(
    'return f"{self._format_decimal(value)} "',
    'return f"{self._format_decimal(value)} \\u041a\\u0413"',
    1,
)
text = text.replace(
    'return f"{self._format_decimal(value)} "',
    'return f"{self._format_decimal(value)} \\u0413"',
    1,
)

p.write_text(text, encoding="utf-8")
print("VOLUME SUFFIX PATCH OK")
