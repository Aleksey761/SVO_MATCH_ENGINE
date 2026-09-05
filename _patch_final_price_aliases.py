from pathlib import Path

p = Path(r"svo\normalizer.py")
text = p.read_text(encoding="utf-8")

marker = "        # FINAL REVIEW NORMALIZATION\n"
assert marker in text, "FINAL REVIEW NORMALIZATION BLOCK NOT FOUND"

# Replace the existing final-review block through the next normalizer anchor.
start = text.index(marker)
end_marker = "        if item.brand:\n            candidate = self._cleanup_candidate(text, brand_match)\n"
end = text.index(end_marker, start)

block = '''        # FINAL PRICE ALIAS NORMALIZATION
        # Canonical mappings confirmed during the PRICE REVIEW pass.
        upper_text = str(text or "").upper()
        upper_volume = str(item.volume or "").strip().upper()

        if item.brand == "SVO":
            if upper_volume == "2,7 Л":
                item.category = "Кондиционер"
                if "ЖЁЛТ" in upper_text or "ЖЕЛТ" in upper_text:
                    item.variant = item.aroma = "PAPATYA"
                elif "КРАСН" in upper_text:
                    item.variant = item.aroma = "PION"
                elif "РОЗОВ" in upper_text:
                    item.variant = item.aroma = "ROSE"
                elif "СИН" in upper_text:
                    item.variant = item.aroma = "MIDNIGHT"
                elif "ФИОЛЕТ" in upper_text:
                    item.variant = item.aroma = "LAVENDER"
                elif "ЧЁРН" in upper_text or "ЧЕРН" in upper_text:
                    item.variant = item.aroma = "BLACK"
                elif "АРОМАТ СТРАСТИ" in upper_text:
                    item.variant = item.aroma = "DAHLIA"
                elif "РОМАНТИЧЕСКИЕ ЦВЕТЫ" in upper_text:
                    item.variant = item.aroma = "ROMANTIK ROSE"

            if upper_volume == "3 Л" and "ГОРНАЯ СВЕЖЕСТЬ" in upper_text:
                item.variant = item.aroma = "MOUNTAIN BREEZE"

            if upper_volume in {"6 КГ", "9 КГ"} and "СВЕЖЕСТЬ ГОР" in upper_text:
                item.variant = item.aroma = "MOUNTAIN BREEZE"

            if upper_volume == "5 КГ" and "ШЕЙХ" in upper_text:
                item.category = "Порошок стиральный"
                item.variant = item.aroma = "MAGINA"

            if "ПЯТНОВЫВОДИТЕЛ" in upper_text and "OXYGEN" in upper_text:
                item.category = "Отбеливатель"
                item.variant = item.aroma = "WHITE" if "БЕЛ" in upper_text else "COLOR"

            if "СРЕДСТВО Д/ПОСУДЫ" in upper_text or "СРЕДСТВО Д\\ПОСУДЫ" in upper_text:
                item.category = "Посуда моющее ср-во"
                if "АПЕЛЬСИН" in upper_text or "ORANGE" in upper_text:
                    item.variant = item.aroma = "ORANGE"
                elif "ГРЕЙПФРУТ" in upper_text or "GRAPEFRUIT" in upper_text:
                    item.variant = item.aroma = "GRAPEFRUIT"
                elif "ЯБЛОКО" in upper_text or "APPLE" in upper_text:
                    item.variant = item.aroma = "APPLE"

        if item.brand == "GILAR":
            if "SPORT" in upper_text and "ПЕРХ" in upper_text:
                item.category = "Шампунь sport"
                item.variant = item.aroma = "BLACK"

        # Do not let packaging tails leak into the canonical variant.
        if item.variant:
            item.variant = re.sub(
                r"\\s*(?:[/\\\\]\\s*\\d+|\\d+\\s*/\\s*\\d+|\\d+\\s*ШТ\\b).*$",
                "",
                str(item.variant),
                flags=re.IGNORECASE,
            ).strip(" /\\\\")
            item.aroma = item.variant

'''

text = text[:start] + block + text[end:]
p.write_text(text, encoding="utf-8")
print("FINAL PRICE ALIAS NORMALIZER PATCH APPLIED")
