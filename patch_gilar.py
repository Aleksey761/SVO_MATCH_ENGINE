from pathlib import Path

p = Path(r"svo\matcher.py")
s = p.read_text(encoding="utf-8")

start = s.index("        gilar_shampoo_rules = (")
end_marker = "                    return matches[0]\n"
end = s.index(end_marker, start) + len(end_marker)

old_block = s[start:end]

new_block = '''        gilar_shampoo_rules = (
            (("ШЬ", "400 ", "GILAR", "WOMEN", "CHARM"), "SKU-006"),
            (("ШЬ", "400 ", "GILAR", "WOMEN", "INTENSE"), "SKU-005"),
            (("ШЬ", "400 ", "GILAR", "MEN", "ARGAN OIL"), "SKU-008"),
            (("ШЬ", "400 ", "GILAR", "WOMEN", "LOVELY MOMENTS"), "SKU-007"),
            (("ШЬ", "400 ", "GILAR", "MEN", "KERATIN EXTRACTS"), "SKU-009"),
            (("ШЬ", "400 ", "GILAR", "MEN", "LEMON OIL"), "SKU-010"),
            (("ШЬ", "400 ", "GILAR", "MEN", "OLIVE OIL"), "SKU-011"),
            (("ШЬ", "400 ", "GILAR", "SPORT BLUE"), "SKU-013"),
        )
        for required_tokens, sku in gilar_shampoo_rules:
            if all(token in compact for token in required_tokens):
                matches = [
                    candidate
                    for candidate in self.master_items
                    if candidate.sku == sku
                ]
                if len(matches) == 1:
                    return matches[0]
'''

if "gilar_shampoo_rules" not in old_block:
    raise RuntimeError("е найден ожидаемый GILAR-блок")

backup = p.with_suffix(".py.before_gilar_fix")
backup.write_text(s, encoding="utf-8")

p.write_text(s[:start] + new_block + s[end:], encoding="utf-8")

print("PATCH OK")
print("FILE:", p)
print("BACKUP:", backup)
