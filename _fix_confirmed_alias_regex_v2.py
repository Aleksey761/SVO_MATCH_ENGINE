from pathlib import Path

path = Path(r"svo\\matcher.py")
text = path.read_text(encoding="utf-8")

anchor = "def _confirmed_review_alias(self, item: ArrivalItem) -> MasterItem | None:"
start = text.index(anchor)
regex_start = text.index("        stripped = re.sub(", start)
regex_end = text.index("        return matches[0] if len(matches) == 1 else None", regex_start)

block = '''        stripped = re.sub(
            r"\\s*(?:[/\\\\]\\s*\\d+|\\d+\\s*/\\s*\\d+|\\d+\\s*ШТ\\b).*$",
            "",
            aroma,
            flags=re.IGNORECASE,
        ).strip(" /\\\\")

'''

text = text[:regex_start] + block + text[regex_end:]
path.write_text(text, encoding="utf-8")
print("CONFIRMED ALIAS REGEX FIXED")
