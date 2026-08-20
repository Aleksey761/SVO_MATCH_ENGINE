from pathlib import Path

PATH = Path("svo/matcher.py")
text = PATH.read_text(encoding="utf-8")

MARKER = "    def _confirmed_price_alias(self, item: ArrivalItem) -> MasterItem | None:\n"
if MARKER not in text:
    insert_before = "    def match(self, item: ArrivalItem) -> ArrivalItem:\n"
    if insert_before not in text:
        raise SystemExit("MATCH METHOD MARKER NOT FOUND")

    method = '''    def _confirmed_price_alias(self, item: ArrivalItem) -> MasterItem | None:\n        \"\"\"Confirmed PRICE aliases from the reviewed MASTER mapping.\n\n        These aliases are deliberately narrow: they resolve only source\n        names that were manually confirmed against the current MASTER.\n        Packaging suffixes such as /6, /12, /2, /7 and 54/9 are ignored\n        only for the purpose of identifying the same product.\n        \"\"\"\n        source = str(getattr(item, "source_name", "") or "").upper()\n        article = str(getattr(item, "supplier_article", "") or getattr(item, "article", "") or "").strip().upper()\n\n        rules = (\n            ("SVO ГЕЛЬ Д\\\\СТИРКИ 2,7 Л ЖЁЛТЫЙ", "SKU-061"),\n            ("SVO ГЕЛЬ Д\\\\СТИРКИ 2,7 Л КРАСНЫЙ", "SKU-055"),\n            ("SVO ГЕЛЬ Д\\\\СТИРКИ 2,7 Л РОЗОВЫЙ", "SKU-060"),\n            ("SVO ГЕЛЬ Д\\\\СТИРКИ 2,7 Л ЧЁРНЫЙ", "SKU-057"),\n            ("SVO ГЕЛЬ Д\\\\СТИРКИ 3 Л ГОРНАЯ СВЕЖЕСТЬ", "SKU-101"),\n            ("SVO КОНДИЦ. Д/БЕЛЬЯ 2,700 МЛ АРОМАТ СТРАСТИ", "SKU-063"),\n            ("SVO ПОРОШ. СТИР. 5 КГ ШЕЙХ", "SKU-295"),\n            ("SVO ПОРОШ. СТИР. 6 КГ СВЕЖЕСТЬ ГОР", "SKU-218"),\n            ("SVO ПОРОШ. СТИР. 9 КГ СВЕЖЕСТЬ ГОР", "SKU-229"),\n            ("SVO ПЯТНОВЫВОДИТЕЛЬ 750 ГР OXYGEN ДЛЯ БЕЛЫХ", "SKU-143"),\n            ("SVO ПЯТНОВЫВОДИТЕЛЬ 750 ГР OXYGEN ДЛЯ ЦВЕТНЫХ", "SKU-144"),\n            ("SVO СРЕДСТВО Д/ПОСУДЫ 750 ГР АПЕЛЬСИН", "SKU-256"),\n            ("SVO СРЕДСТВО Д/ПОСУДЫ 750 ГР ГРЕЙПФРУТ", "SKU-257"),\n            ("SVO СРЕДСТВО Д/ПОСУДЫ 750 ГР ЯБЛОКО", "SKU-259"),\n            ("GILAR ШАМПУНЬ 400 МЛ МУЖС. SPORT ОТ ПЕРХ", "SKU-012"),\n            ("GILAR ШАМПУНЬ 400 МЛ МУЖС. SPORT Д/ПОВР. ВОЛ", "SKU-013"),\n        )\n\n        for source_prefix, sku in rules:\n            if source_prefix in source:\n                matches = [candidate for candidate in self.master_items if candidate.sku == sku]\n                if len(matches) == 1:\n                    return matches[0]\n\n        # Both SHAIK /7 and SHAIK 54/9 are confirmed as one product/SKU.\n        if article == "С-5174" and "SHAIK" in source and "1,440" in source:\n            matches = [candidate for candidate in self.master_items if candidate.sku == "SKU-045"]\n            if len(matches) == 1:\n                return matches[0]\n\n        return None\n\n'''
    text = text.replace(insert_before, method + insert_before, 1)

# Ensure confirmed aliases are consulted before normal fuzzy matching.
needle = "        master = self._find_exact_master(item)\n"
replacement = "        master = self._confirmed_price_alias(item) or self._find_exact_master(item)\n"
if needle not in text:
    raise SystemExit("MATCH EXACT LOOKUP MARKER NOT FOUND")
text = text.replace(needle, replacement, 1)

PATH.write_text(text, encoding="utf-8")
print("CONFIRMED PRICE ALIASES PATCH APPLIED")
