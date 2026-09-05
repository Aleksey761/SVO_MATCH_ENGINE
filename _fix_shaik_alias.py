from pathlib import Path

target = Path(r"svo\normalizer.py")
text = target.read_text(encoding="utf-8")

old = '"MAGINA": ["шейх", "shaik", "shaikh", "magina"],'
new = '"MAGINA": ["magina"],'

assert old in text, "SHAIK -> MAGINA ALIAS NOT FOUND"
text = text.replace(old, new, 1)

target.write_text(text, encoding="utf-8")
print("SHAIK -> MAGINA REMOVED")
print("MAGINA alias now contains only: magina")
