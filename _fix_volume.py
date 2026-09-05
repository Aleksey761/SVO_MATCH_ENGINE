from pathlib import Path
import re

p = Path("svo/normalizer.py")
t = p.read_text(encoding="utf-8")

start = t.index("        self._volume_re = re.compile(")
end = t.index("        )", start) + len("        )")

new = '''        self._volume_re = re.compile(
            r"(\\d+(?:[.,]\\d+)?)\\s*(л|литр|литра|литров|мл|ml|liter|liters|l|кг|kg|килограмм|килограмма|килограммов|г|гр|грамм|грамма|граммов|gram|grams)",
            re.IGNORECASE,
        )'''

t = t[:start] + new + t[end:]
p.write_text(t, encoding="utf-8")

print("VOLUME REGEX FIXED")
