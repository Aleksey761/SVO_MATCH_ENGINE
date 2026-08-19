from pathlib import Path
import re

path = Path("svo/matcher.py")
text = path.read_text(encoding="utf-8")

needle = "    def _confirmed_review_alias(self, item: ArrivalItem) -> MasterItem | None:\n"
if needle not in text:
    raise SystemExit("_confirmed_review_alias method not found")

start = text.index(needle)
end = text.index("\n    def _find_exact_master", start)
method = text[start:end]

# The previous patch left a bare `matches` return even when no matches list
# exists. This is the exact runtime failure seen in PRICE matching.
if "return matches[0] if len(matches) == 1 else None" in method:
    method = method.replace(
        "return matches[0] if len(matches) == 1 else None",
        "return None",
    )
else:
    # Also handle variants with whitespace/line wrapping around the return.
    method, count = re.subn(
        r"(?m)^\s*return\s+matches\[0\]\s+if\s+len\(matches\)\s*==\s*1\s+else\s+None\s*$",
        "        return None",
        method,
        count=1,
    )
    if count == 0:
        raise SystemExit("Broken confirmed-alias return statement not found")

text = text[:start] + method + text[end:]
path.write_text(text, encoding="utf-8")
print("CONFIRMED ALIAS NameError PATCH APPLIED — undefined matches return removed")
