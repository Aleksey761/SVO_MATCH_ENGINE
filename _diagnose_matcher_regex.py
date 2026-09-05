from pathlib import Path
import re

path = Path(r"svo\\matcher.py")
text = path.read_text(encoding="utf-8")

bad = []
for lineno, line in enumerate(text.splitlines(), 1):
    if "re." not in line:
        continue
    # Check simple quoted regex literals on each line.
    for quote in ('"', "'"):
        marker = "r" + quote
        pos = 0
        while True:
            start = line.find(marker, pos)
            if start < 0:
                break
            end = line.find(quote, start + 2)
            if end < 0:
                break
            pattern = line[start + 2:end]
            try:
                re.compile(pattern)
            except re.error as exc:
                bad.append((lineno, pattern, str(exc), line))
            pos = end + 1

if bad:
    print("INVALID REGEX FOUND:")
    for row in bad:
        print(row)
else:
    print("No invalid single-line regex literals found.")

# Inspect the most recently added packaging-tail regex directly.
target = r'''r"\s*(?:[/\\]\s*\d+|\d+\s*/\s*\d+|\d+\s*ШТ\b).*$"'''
if target in text:
    print("PACKAGING REGEX FOUND")
    try:
        re.compile(r"\s*(?:[/\\]\s*\d+|\d+\s*/\s*\d+|\d+\s*ШТ\b).*$")
        print("PACKAGING REGEX VALID")
    except re.error as exc:
        print("PACKAGING REGEX INVALID:", exc)
else:
    print("PACKAGING REGEX TARGET NOT FOUND")

print("DIAGNOSTIC COMPLETE")
