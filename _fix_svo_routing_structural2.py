from pathlib import Path

p = Path("svo/normalizer.py")
t = p.read_text(encoding="utf-8")

start_marker = '        # Canonical MASTER routing for PRICE:'
end_marker = '        if item.brand:\n'

start = t.find(start_marker)
end = t.find(end_marker, start)

if start < 0:
    raise SystemExit("START MARKER NOT FOUND")

if end < 0:
    raise SystemExit("END MARKER NOT FOUND")

new_block = '''        # Canonical MASTER routing for PRICE.
        # 1 l SVO liquid detergents -> SVO Elegant.
        # 1.5 l SVO liquid detergents -> SVO Elegant,
        # except the dedicated SVO Baby position.
        # 2.7 l is intentionally left unchanged here because
        # MASTER contains separate Conditioner and С 3в1 blocks.
        if item.brand == "SVO" and item.category == "С":
            if item.volume == "1 ":
                item.brand = "SVO Elegant"
            elif item.volume == "1,5 ":
                variant = self._normalize_value(item.variant or item.aroma or "")
                if variant != "BABY":
                    item.brand = "SVO Elegant"

'''

t = t[:start] + new_block + t[end:]
p.write_text(t, encoding="utf-8")

print("STRUCTURAL SVO ROUTING PATCH OK")
