from pathlib import Path

path = Path(r"svo\\matcher.py")
text = path.read_text(encoding="utf-8")

start = text.index("    _CYR_TO_LAT = str.maketrans(")
end = text.index("    def _canonical_aroma_tokens", start)

replacement = '''    _CYR_TO_LAT = str.maketrans({
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d",
        "е": "e", "ё": "e", "ж": "zh", "з": "z", "и": "i",
        "й": "i", "к": "k", "л": "l", "м": "m", "н": "n",
        "о": "o", "п": "p", "р": "r", "с": "s", "т": "t",
        "у": "u", "ф": "f", "х": "h", "ц": "c", "ч": "ch",
        "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "",
        "э": "e", "ю": "yu", "я": "ya",
    })

'''

path.write_text(text[:start] + replacement + text[end:], encoding="utf-8")
print("CYR_TO_LAT FIXED")
