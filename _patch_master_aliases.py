from pathlib import Path
import re

TARGET = Path(r"svo\normalizer.py")
text = TARGET.read_text(encoding="utf-8")

anchor = '    _DEFAULT_AROMA_ALIASES = {'
assert anchor in text, "AROMA ALIAS BLOCK NOT FOUND"

aliases = [
    '"BABY": ["детский", "детские", "baby"],',
    '"SPRING FRESH": ["весенний бриз", "spring fresh"],',
    '"MOUNTAIN BREEZE": ["горный бриз", "mountain breeze"],',
    '"ROSE": ["роза", "rose"],',
    '"PAPATYE": ["ромашка", "daisy", "papatye"],',
    '"MAGINA": ["шейх", "shaik", "shaikh", "magina"],',
    '"ORANGE": ["апельсин", "orange"],',
    '"GRAPEFRUIT": ["грейпфрут", "grapefruit"],',
    '"APPLE": ["яблоко", "apple"],',
    '"OXYGEN": ["oxygen"],',
]
insert_lines = []
for line in aliases:
    canonical = line.split(":", 1)[0].strip().strip('"')
    if f'"{canonical}":' not in text:
        insert_lines.append("        " + line)

if insert_lines:
    pos = text.index(anchor) + len(anchor)
    text = text[:pos] + "\n" + "\n".join(insert_lines) + text[pos:]

start = text.find("    def _normalize_aroma(self, candidate: str) -> str:\n")
assert start >= 0, "_normalize_aroma METHOD NOT FOUND"
end = text.find("\n    @staticmethod\n    def _format_decimal", start)
assert end >= 0, "_format_decimal METHOD NOT FOUND"

new_method_lines = [
    "    def _normalize_aroma(self, candidate: str) -> str:",
    "        result = \" \".join(str(candidate or \"\").strip().split())",
    "        phrase_aliases: list[tuple[str, str]] = []",
    "        for canonical, aliases in self._aroma_aliases.items():",
    "            for alias in aliases:",
    "                alias_text = \" \".join(str(alias).strip().split())",
    "                if alias_text:",
    "                    phrase_aliases.append((alias_text, canonical))",
    "        phrase_aliases.sort(key=lambda pair: len(pair[0]), reverse=True)",
    "        for alias, canonical in phrase_aliases:",
    "            result = re.sub(rf\"(?<!\\w){re.escape(alias)}(?!\\w)\", canonical, result, flags=re.IGNORECASE)",
    "        normalized = []",
    "        for token in re.split(r\"\\s+\", result.strip()):",
    "            lowered = token.lower()",
    "            mapped = None",
    "            for canonical, aliases in self._aroma_aliases.items():",
    "                if lowered in {str(alias).lower() for alias in aliases}:",
    "                    mapped = canonical",
    "                    break",
    "            normalized.append(mapped or token)",
    "        return \" \".join(normalized).strip()",
]
new_method = "\n".join(new_method_lines) + "\n"
text = text[:start] + new_method + text[end:]

backup = TARGET.with_name(TARGET.name + ".before_master_alias_patch")
if not backup.exists():
    backup.write_text(TARGET.read_text(encoding="utf-8"), encoding="utf-8")

TARGET.write_text(text, encoding="utf-8")
print("MASTER ALIAS PATCH APPLIED")
