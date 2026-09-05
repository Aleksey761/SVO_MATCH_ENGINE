from pathlib import Path

p = Path(r"svo\normalizer.py")
text = p.read_text(encoding="utf-8")

anchor = "        if item.brand:\n            candidate = self._cleanup_candidate(text, brand_match)\n"
assert anchor in text, "NORMALIZER ANCHOR NOT FOUND"

if "FINAL REVIEW NORMALIZATION" in text:
    print("FINAL REVIEW NORMALIZATION ALREADY PRESENT")
else:
    insert = (
        "        # FINAL REVIEW NORMALIZATION\n"
        "        # Confirmed canonical mappings and removal of packaging tails.\n"
        '        upper_text = text.upper()\n'
        '        upper_volume = str(item.volume or "").upper()\n'
        '        if item.brand == "SVO":\n'
        '            if upper_volume == "2,7 Л":\n'
        '                item.category = "Кондиционер"\n'
        '                if "ЖЁЛТ" in upper_text or "ЖЕЛТ" in upper_text:\n'
        '                    item.variant = item.aroma = "PAPATYA"\n'
        '                elif "КРАСН" in upper_text:\n'
        '                    item.variant = item.aroma = "PION"\n'
        '                elif "РОЗОВ" in upper_text:\n'
        '                    item.variant = item.aroma = "ROSE"\n'
        '                elif "СИН" in upper_text:\n'
        '                    item.variant = item.aroma = "MIDNIGHT"\n'
        '                elif "ЧЁРН" in upper_text or "ЧЕРН" in upper_text:\n'
        '                    item.variant = item.aroma = "BLACK"\n'
        '                elif "АРОМАТ СТРАСТИ" in upper_text:\n'
        '                    item.variant = item.aroma = "DAHLIA"\n'
        '                elif "РОМАНТИЧЕСКИЕ ЦВЕТЫ" in upper_text:\n'
        '                    item.variant = item.aroma = "ROMANTIK ROSE"\n'
        '            if upper_volume == "3 Л" and "ГОРНАЯ СВЕЖЕСТЬ" in upper_text:\n'
        '                item.variant = item.aroma = "MOUNTAIN BREEZE"\n'
        '            if upper_volume in {"6 КГ", "9 КГ"} and "СВЕЖЕСТЬ ГОР" in upper_text:\n'
        '                item.variant = item.aroma = "MOUNTAIN BREEZE"\n'
        '            if upper_volume == "5 КГ" and "ШЕЙХ" in upper_text:\n'
        '                item.variant = item.aroma = "MAGINA"\n'
        '            if "ПЯТНОВЫВОДИТЕЛ" in upper_text and "OXYGEN" in upper_text:\n'
        '                item.category = "Отбеливатель"\n'
        '                item.variant = item.aroma = "WHITE" if "БЕЛ" in upper_text else "COLOR"\n'
        '            if "СРЕДСТВО Д/ПОСУДЫ" in upper_text or "СРЕДСТВО Д\\\\ПОСУДЫ" in upper_text:\n'
        '                item.category = "Посуда моющее ср-во"\n'
        '                if "АПЕЛЬСИН" in upper_text or "ORANGE" in upper_text:\n'
        '                    item.variant = item.aroma = "ORANGE"\n'
        '                elif "ГРЕЙПФРУТ" in upper_text or "GRAPEFRUIT" in upper_text:\n'
        '                    item.variant = item.aroma = "GRAPEFRUIT"\n'
        '                elif "ЯБЛОКО" in upper_text or "APPLE" in upper_text:\n'
        '                    item.variant = item.aroma = "APPLE"\n'
        '        if item.brand == "GILAR" and "SPORT" in upper_text and "ПЕРХ" in upper_text:\n'
        '            item.category = "Шампунь sport"\n'
        '            item.variant = item.aroma = "BLACK"\n'
        '        # Strip packaging tails after canonical mapping.\n'
        '        if item.variant:\n'
        '            item.variant = re.sub(r"\\s*(?:[/\\\\]\\s*\\d+|\\d+\\s*/\\s*\\d+|\\d+\\s*шт\\b).*$", "", item.variant, flags=re.IGNORECASE).strip(" /\\\\")\n'
        '            item.aroma = item.variant\n'
    )
    text = text.replace(anchor, insert + anchor, 1)
    p.write_text(text, encoding="utf-8")
    print("FINAL REVIEW NORMALIZATION APPLIED")
