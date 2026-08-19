from pathlib import Path

path = Path("svo/matcher.py")
text = path.read_text(encoding="utf-8")

needle = "    def _confirmed_review_alias(self, item: ArrivalItem) -> MasterItem | None:\n"
if needle not in text:
    raise SystemExit("_confirmed_review_alias method not found")

start = text.index(needle)
end = text.index("\n    def _find_exact_master", start)
method = text[start:end]

if "return matches[0] if len(matches) == 1 else None" not in method:
    raise SystemExit("Expected confirmed-alias return statement not found")

# The local patch introduced a return using `matches` without creating it.
# Keep the confirmed-alias hook safe: if no explicit alias candidates are
# produced by the method, return None and let the normal MASTER matcher run.
method = method.replace(
    "    return matches[0] if len(matches) == 1 else None",
    "    matches = locals().get(\"matches\", [])\n    return matches[0] if len(matches) == 1 else None",
    1,
)

text = text[:start] + method + text[end:]
path.write_text(text, encoding="utf-8")
print("CONFIRMED ALIAS NameError PATCH APPLIED")
