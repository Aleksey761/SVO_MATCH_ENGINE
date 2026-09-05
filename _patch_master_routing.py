from pathlib import Path

p = Path(r"svo\normalizer.py")
text = p.read_text(encoding="utf-8")

needle = "        item.volume = self._detect_volume(text)\n"

patch = r'''
        # MASTER routing for SVO liquid detergents.
        # 1 L / 1.5 L non-BABY -> SVO Elegant.
        # 1.5 L BABY remains SVO.
        # 2.7 L is deliberately left unchanged here.
        if item.brand == "SVO" and item.category == "\u0416\u041c\u0421":
            variant_value = str(item.variant or item.aroma or "").strip().upper()
            is_baby = variant_value == "BABY"

            if item.volume in {"1 \u041b", "1,5 \u041b"} and not is_baby:
                item.brand = "SVO Elegant"
'''

assert needle in text, "ROUTING TARGET NOT FOUND"
assert "MASTER routing for SVO liquid detergents." not in text, "ROUTING PATCH ALREADY PRESENT"

text = text.replace(needle, needle + patch, 1)
p.write_text(text, encoding="utf-8")

print("MASTER ROUTING PATCH OK")
