from pathlib import Path

p = Path(r"svo\normalizer.py")
text = p.read_text(encoding="utf-8")

start = text.index("    def _detect_volume(self, text: str) -> Optional[str]:")
end = text.index("    def _cleanup_candidate(", start)

new_method = r'''    def _detect_volume(self, text: str) -> Optional[str]:
        match = self._volume_re.search(text.lower())
        if not match:
            return None

        raw_value = match.group(1)
        value = Decimal(raw_value.replace(",", "."))
        unit = match.group(2).lower()

        L = "\u041b"
        ML = "\u041c\u041b"
        KG = "\u041a\u0413"
        G = "\u0413"

        liter_units = {
            "\u043b", "liter", "liters", "l",
            "\u043b\u0438\u0442\u0440", "\u043b\u0438\u0442\u0440\u0430",
            "\u043b\u0438\u0442\u0440\u043e\u0432",
        }
        ml_units = {"\u043c\u043b", "ml"}
        kg_units = {
            "\u043a\u0433", "kg",
            "\u043a\u0438\u043b\u043e\u0433\u0440\u0430\u043c\u043c",
            "\u043a\u0438\u043b\u043e\u0433\u0440\u0430\u043c\u043c\u0430",
            "\u043a\u0438\u043b\u043e\u0433\u0440\u0430\u043c\u043c\u043e\u0432",
        }
        g_units = {
            "\u0433", "\u0433\u0440",
            "\u0433\u0440\u0430\u043c\u043c",
            "\u0433\u0440\u0430\u043c\u043c\u0430",
            "\u0433\u0440\u0430\u043c\u043c\u043e\u0432",
            "gram", "grams",
        }

        if unit in liter_units:
            return f"{self._format_decimal(value)} {L}"

        if unit in ml_units:
            # PRICE notation 1,440 ml means 1.44 l.
            if (
                Decimal("1") <= value < Decimal("10")
                and "," in raw_value
                and len(raw_value.split(",", 1)[1]) == 3
            ):
                return f"{self._format_decimal(value)} {L}"

            if value >= Decimal("1000"):
                return f"{self._format_decimal(value / Decimal('1000'))} {L}"

            return f"{self._format_decimal(value)} {ML}"

        if unit in kg_units:
            return f"{self._format_decimal(value)} {KG}"

        if unit in g_units:
            return f"{self._format_decimal(value)} {G}"

        return None

'''

p.write_text(text[:start] + new_method + text[end:], encoding="utf-8")
print("DETECT_VOLUME REPLACED CLEANLY")
