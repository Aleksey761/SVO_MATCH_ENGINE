from pathlib import Path

p = Path(r"svo\matcher.py")
text = p.read_text(encoding="utf-8")
anchor = "    def _find_exact_master(self, item: ArrivalItem) -> MasterItem | None:\n"
assert anchor in text, "MATCHER EXACT-MASTER ANCHOR NOT FOUND"

if "_confirmed_review_alias" in text:
    print("CONFIRMED REVIEW ALIASES ALREADY PRESENT")
else:
    helper_lines = [
        "    def _confirmed_review_alias(self, item: ArrivalItem) -> MasterItem | None:\n",
        '        category = str(getattr(item, "category", "") or "").strip().upper()\n',
        '        brand = str(getattr(item, "brand", "") or "").strip().upper()\n',
        '        volume = str(getattr(item, "volume", "") or "").strip().upper()\n',
        '        aroma = str(getattr(item, "aroma", "") or getattr(item, "variant", "") or "").strip().upper()\n',
        "        aliases = {\n",
        '            ("КОНДИЦИОНЕР", "SVO", "2,7 Л", "PAPATYA"),\n',
        '            ("КОНДИЦИОНЕР", "SVO", "2,7 Л", "PION"),\n',
        '            ("КОНДИЦИОНЕР", "SVO", "2,7 Л", "ROSE"),\n',
        '            ("КОНДИЦИОНЕР", "SVO", "2,7 Л", "MIDNIGHT"),\n',
        '            ("КОНДИЦИОНЕР", "SVO", "2,7 Л", "BLACK"),\n',
        '            ("КОНДИЦИОНЕР", "SVO", "2,7 Л", "DAHLIA"),\n',
        '            ("КОНДИЦИОНЕР", "SVO", "2,7 Л", "ROMANTIK ROSE"),\n',
        '            ("ПОРОШОК СТИРАЛЬНЫЙ", "SVO", "5 КГ", "MAGINA"),\n',
        '            ("ПОРОШОК СТИРАЛЬНЫЙ", "SVO", "6 КГ", "MOUNTAIN BREEZE"),\n',
        '            ("ПОРОШОК СТИРАЛЬНЫЙ", "SVO", "9 КГ", "MOUNTAIN BREEZE"),\n',
        '            ("ОТБЕЛИВАТЕЛЬ", "SVO", "750 Г", "WHITE"),\n',
        '            ("ОТБЕЛИВАТЕЛЬ", "SVO", "750 Г", "COLOR"),\n',
        '            ("ПОСУДА МОЮЩЕЕ СР-ВО", "SVO", "750 Г", "ORANGE"),\n',
        '            ("ПОСУДА МОЮЩЕЕ СР-ВО", "SVO", "750 Г", "GRAPEFRUIT"),\n',
        '            ("ПОСУДА МОЮЩЕЕ СР-ВО", "SVO", "750 Г", "APPLE"),\n',
        '            ("ШАМПУНЬ SPORT", "GILAR", "400 МЛ", "BLACK"),\n',
        "        }\n",
        "        if (category, brand, volume, aroma) not in aliases:\n",
        "            return None\n",
        "        matches = [\n",
        "            candidate for candidate in self.master_items\n",
        '            if str(getattr(candidate, "brand", "") or "").strip().upper() == brand\n',
        '            and str(getattr(candidate, "volume", "") or "").strip().upper() == volume\n',
        '            and str(getattr(candidate, "variant", "") or getattr(candidate, "aroma", "") or "").strip().upper() == aroma\n',
        "        ]\n",
        "        return matches[0] if len(matches) == 1 else None\n",
        "\n",
    ]
    helper = "".join(helper_lines)
    text = text.replace(anchor, helper + anchor, 1)
    marker = "        # MASTER-aware exact metadata match.\n"
    replacement = "        confirmed = self._confirmed_review_alias(item)\n        if confirmed is not None:\n            return confirmed\n\n        # MASTER-aware exact metadata match.\n"
    assert marker in text, "MASTER EXACT MATCH MARKER NOT FOUND"
    text = text.replace(marker, replacement, 1)
    p.write_text(text, encoding="utf-8")
    print("CONFIRMED REVIEW MATCHER PATCH APPLIED")
