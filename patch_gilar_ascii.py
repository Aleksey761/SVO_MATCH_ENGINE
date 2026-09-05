from pathlib import Path

p = Path(r"svo\matcher.py")
s = p.read_text(encoding="utf-8")

start = s.index("        gilar_shampoo_rules = (")
end = s.index("        # SALES: Magina 1.44 L aliases confirmed by MASTER.", start)

new_block = (
    '        gilar_shampoo_rules = (\n'
    '            (("GILAR", "400", "WOMEN", "CHARM"), "SKU-006"),\n'
    '            (("GILAR", "400", "WOMEN", "INTENSE"), "SKU-005"),\n'
    '            (("GILAR", "400", "MEN", "ARGAN OIL"), "SKU-008"),\n'
    '            (("GILAR", "400", "WOMEN", "LOVELY MOMENTS"), "SKU-007"),\n'
    '            (("GILAR", "400", "MEN", "KERATIN EXTRACTS"), "SKU-009"),\n'
    '            (("GILAR", "400", "MEN", "LEMON OIL"), "SKU-010"),\n'
    '            (("GILAR", "400", "MEN", "OLIVE OIL"), "SKU-011"),\n'
    '            (("GILAR", "SPORT", "BLUE", "400"), "SKU-013"),\n'
    '        )\n'
    '\n'
    '        for required_tokens, sku in gilar_shampoo_rules:\n'
    '            if all(token in compact for token in required_tokens):\n'
    '                matches = [\n'
    '                    candidate\n'
    '                    for candidate in self.master_items\n'
    '                    if candidate.sku == sku\n'
    '                ]\n'
    '                if len(matches) == 1:\n'
    '                    return matches[0]\n'
    '\n'
)

backup = Path(r"svo\matcher.py.before_gilar_ascii_fix")
backup.write_text(s, encoding="utf-8")

p.write_text(s[:start] + new_block + s[end:], encoding="utf-8")

print("GILAR ASCII PATCH OK")
print("FILE:", p)
print("BACKUP:", backup)
