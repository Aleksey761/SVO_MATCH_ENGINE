from pathlib import Path

PATH = Path("svo/matcher.py")
text = PATH.read_text(encoding="utf-8")

start_marker = "    def _confirmed_price_alias(self, item: ArrivalItem) -> MasterItem | None:\n"
end_marker = "    def match(self, item: ArrivalItem) -> ArrivalItem:\n"
start = text.find(start_marker)
end = text.find(end_marker, start + 1) if start >= 0 else -1
if start < 0 or end < 0:
    raise SystemExit("CONFIRMED PRICE ALIAS METHOD NOT FOUND")

method = '''    def _confirmed_price_alias(self, item: ArrivalItem) -> MasterItem | None:
        """Strict PRICE aliases confirmed against the current MASTER.

        Aliases are intentionally narrow. They must never override a real
        product distinction such as aroma, volume, or product family.
        """
        source = str(getattr(item, "source_name", "") or "").upper()
        compact = re.sub(r"\\s+", " ", source).strip()
        article = str(
            getattr(item, "supplier_article", "")
            or getattr(item, "article", "")
            or ""
        ).strip().upper()

        rules = (
            ("SVO ГЕЛЬ Д\\\\СТИРКИ 2,7 Л ЖЁЛТЫЙ", "SKU-061"),
            ("SVO ГЕЛЬ Д\\\\СТИРКИ 2,7 Л КРАСНЫЙ", "SKU-055"),
            ("SVO ГЕЛЬ Д\\\\СТИРКИ 2,7 Л РОЗОВЫЙ", "SKU-060"),
            ("SVO ГЕЛЬ Д\\\\СТИРКИ 2,7 Л ЧЁРНЫЙ", "SKU-057"),
            ("SVO ГЕЛЬ Д\\\\СТИРКИ 3 Л ГОРНАЯ СВЕЖЕСТЬ", "SKU-101"),
            ("SVO КОНДИЦ. Д/БЕЛЬЯ 2,700 МЛ АРОМАТ СТРАСТИ", "SKU-063"),
            ("SVO ПОРОШ. СТИР. 5 КГ ШЕЙХ", "SKU-295"),
            ("SVO ПОРОШ. СТИР. 6 КГ СВЕЖЕСТЬ ГОР", "SKU-218"),
            ("SVO ПОРОШ. СТИР. 9 КГ СВЕЖЕСТЬ ГОР", "SKU-229"),
            ("SVO ПЯТНОВЫВОДИТЕЛЬ 750 ГР OXYGEN ДЛЯ БЕЛЫХ", "SKU-143"),
            ("SVO ПЯТНОВЫВОДИТЕЛЬ 750 ГР OXYGEN ДЛЯ ЦВЕТНЫХ", "SKU-144"),
            ("SVO СРЕДСТВО Д/ПОСУДЫ 750 ГР АПЕЛЬСИН", "SKU-256"),
            ("SVO СРЕДСТВО Д/ПОСУДЫ 750 ГР ГРЕЙПФРУТ", "SKU-257"),
            ("SVO СРЕДСТВО Д/ПОСУДЫ 750 ГР ЯБЛОКО", "SKU-259"),
        )
        for source_prefix, sku in rules:
            if source_prefix in compact:
                matches = [candidate for candidate in self.master_items if candidate.sku == sku]
                if len(matches) == 1:
                    return matches[0]

        # GILAR 400 ml men's SPORT aliases. Distinguish the two variants explicitly.
        if "GILAR" in compact and "ШAМПУН" in compact.replace("A", "А") and "400 МЛ" in compact and "SPORT" in compact:
            if "ОТ ПЕРХ" in compact:
                sku = "SKU-012"
            elif "ПОВР" in compact and "ВОЛ" in compact:
                sku = "SKU-013"
            else:
                sku = None
            if sku:
                matches = [candidate for candidate in self.master_items if candidate.sku == sku]
                if len(matches) == 1:
                    return matches[0]

        # GILAR women's 400 ml aliases.
        if "GILAR" in compact and "ШAМПУН" in compact.replace("A", "А") and "400 МЛ" in compact:
            if "LOVELY" in compact:
                sku = "SKU-007"
            elif "INTENSIV" in compact:
                sku = "SKU-005"
            else:
                sku = None
            if sku:
                matches = [candidate for candidate in self.master_items if candidate.sku == sku]
                if len(matches) == 1:
                    return matches[0]

        # SHAIk /7 and 54/9 are the same product. Require the supplier article
        # so a different SVO 1.44 l aroma (e.g. Blackberry) cannot be hijacked.
        if article == "С-5174" and "SHAIK" in compact and "1,440" in compact:
            matches = [candidate for candidate in self.master_items if candidate.sku == "SKU-045"]
            if len(matches) == 1:
                return matches[0]

        # SVO Blackberry 1.44 l is a separate product.
        if article == "С-5159" and "ЕЖЕВИКА" in compact and "1,440" in compact:
            matches = [candidate for candidate in self.master_items if candidate.sku == "SKU-052"]
            if len(matches) == 1:
                return matches[0]

        return None

'''
text = text[:start] + method + text[end:]
PATH.write_text(text, encoding="utf-8")
print("PRICE FALSE-MATCH ALIASES FIXED")
