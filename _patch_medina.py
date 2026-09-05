from pathlib import Path

p = Path(r"svo\normalizer.py")
text = p.read_text(encoding="utf-8")

needle = '"MEDINA": "MAGINA",'
if needle in text:
    print("MEDINA ALIAS ALREADY PRESENT")
else:
    marker = 'self._aroma_aliases = aroma_aliases or self._DEFAULT_AROMA_ALIASES'
    assert marker in text, "AROMA ALIAS TARGET NOT FOUND"

    # обавляем supplier alias в DEFAULT_AROMA_ALIASES
    anchor = '    _DEFAULT_AROMA_ALIASES = {'
    assert anchor in text, "AROMA DICTIONARY NOT FOUND"

    pos = text.index(anchor) + len(anchor)
    text = text[:pos] + '\n        "MAGINA": ["MEDINA"],' + text[pos:]

    p.write_text(text, encoding="utf-8")
    print("MEDINA -> MAGINA ALIAS ADDED")
