from pathlib import Path

p = Path(r"svo\normalizer.py")
text = p.read_text(encoding="utf-8")

needle = '"MINT": ["MENTOL"],'

if needle in text:
    print("MENTOL -> MINT ALIAS ALREADY PRESENT")
else:
    anchor = '    _DEFAULT_AROMA_ALIASES = {'
    assert anchor in text, "AROMA DICTIONARY NOT FOUND"

    pos = text.index(anchor) + len(anchor)
    text = text[:pos] + '\n        "MINT": ["MENTOL"],' + text[pos:]

    p.write_text(text, encoding="utf-8")
    print("MENTOL -> MINT ALIAS ADDED")
