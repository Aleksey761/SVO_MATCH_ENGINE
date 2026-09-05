from pathlib import Path
import re

p = Path(r"svo\matcher.py")
text = p.read_text(encoding="utf-8")

start = text.index("    def _confirmed_review_alias(self, item: ArrivalItem) -> MasterItem | None:")
end = text.index("    def _find_exact_master(self, item: ArrivalItem) -> MasterItem | None:", start)

new_block = """    def _confirmed_review_alias(self, item: ArrivalItem) -> MasterItem | None:
        category = str(getattr(item, "category", "") or "").strip().upper()
        brand = str(getattr(item, "brand", "") or "").strip().upper()
        volume = str(getattr(item, "volume", "") or "").strip().upper()
        aroma = str(getattr(item, "aroma", "") or getattr(item, "variant", "") or "").strip().upper()

        source_aliases = {
            ("КОНДИЦИОНЕР", "SVO", "2,7 Л", "ЖЁЛТЫЙ"): "PAPATYA",
            ("КОНДИЦИОНЕР", "SVO", "2,7 Л", "ЖЕЛТЫЙ"): "PAPATYA",
            ("КОНДИЦИОНЕР", "SVO", "2,7 Л", "КРАСНЫЙ"): "PION",
            ("КОНДИЦИОНЕР", "SVO", "2,7 Л", "РОЗОВЫЙ"): "ROSE",
            ("КОНДИЦИОНЕР", "SVO", "2,7 Л", "СИНИЙ"): "MIDNIGHT",
            ("КОНДИЦИОНЕР", "SVO", "2,7 Л", "ФИОЛЕТОВЫЙ"): "LAVENDER",
            ("КОНДИЦИОНЕР", "SVO", "2,7 Л", "ЧЁРНЫЙ"): "BLACK",
            ("КОНДИЦИОНЕР", "SVO", "2,7 Л", "ЧЕРНЫЙ"): "BLACK",
            ("КОНДИЦИОНЕР", "SVO", "2,7 Л", "АРОМАТ СТРАСТИ"): "DAHLIA",
            ("КОНДИЦИОНЕР", "SVO", "2,7 Л", "РОМАНТИЧЕСКИЕ ЦВЕТЫ"): "ROMANTIK ROSE",
            ("ПОРОШОК СТИРАЛЬНЫЙ", "SVO", "5 КГ", "ШЕЙХ"): "MAGINA",
            ("ПОРОШОК СТИРАЛЬНЫЙ", "SVO", "6 КГ", "СВЕЖЕСТЬ ГОР"): "MOUNTAIN BREEZE",
            ("ПОРОШОК СТИРАЛЬНЫЙ", "SVO", "9 КГ", "СВЕЖЕСТЬ ГОР"): "MOUNTAIN BREEZE",
            ("ОТБЕЛИВАТЕЛЬ", "SVO", "750 Г", "OXYGEN ДЛЯ БЕЛЫХ"): "WHITE",
            ("ОТБЕЛИВАТЕЛЬ", "SVO", "750 Г", "OXYGEN ДЛЯ ЦВЕТНЫХ"): "COLOR",
            ("ПОСУДА МОЮЩЕЕ СР-ВО", "SVO", "750 Г", "АПЕЛЬСИН ORANGE"): "ORANGE",
            ("ПОСУДА МОЮЩЕЕ СР-ВО", "SVO", "750 Г", "ГРЕЙПФРУТ GRAPEFRUIT"): "GRAPEFRUIT",
            ("ПОСУДА МОЮЩЕЕ СР-ВО", "SVO", "750 Г", "ЯБЛОКО APPLE"): "APPLE",
            ("ШАМПУНЬ SPORT", "GILAR", "400 МЛ", "МУЖС. SPORT ОТ ПЕРХ."): "BLACK",
        }

        canonical_aroma = source_aliases.get((category, brand, volume, aroma))
        if canonical_aroma is None:
            stripped = re.sub(
                r"\s*(?:[/\\]\s*\d+|\d+\s*/\s*\d+|\d+\s*ШТ\b).*$",
                "",
                aroma,
                flags=re.IGNORECASE,
            ).strip(" /\\")
            canonical_aroma = source_aliases.get((category, brand, volume, stripped))

        if canonical_aroma is None:
            return None

        matches = [
            candidate for candidate in self.master_items
            if str(getattr(candidate, "brand", "") or "").strip().upper() == brand
            and str(getattr(candidate, "volume", "") or "").strip().upper() == volume
            and str(getattr(candidate, "variant", "") or getattr(candidate, "aroma", "") or "").strip().upper() == canonical_aroma
        ]
        return matches[0] if len(matches) == 1 else None

"""
text = text[:start] + new_block + text[end:]
p.write_text(text, encoding="utf-8")
print("PRICE SOURCE ALIAS MATCHER PATCH APPLIED")
