from pathlib import Path

p = Path("svo/normalizer.py")
t = p.read_text(encoding="utf-8")

start = t.index("    def _detect_volume(")
end = t.index("    def _cleanup_candidate(", start)

new = r'''    def _detect_volume(self, text: str) -> Optional[str]:
        match = self._volume_re.search(text.lower())
        if not match:
            return None

        raw = match.group(1)
        unit = match.group(2).lower()
        value = Decimal(raw.replace(",", "."))

        if unit in {"л", "литр", "литра", "литров", "l", "liter", "liters"}:
            return f"{self._format_decimal(value)} "

        if unit in {"мл", "ml"}:
            if (
                Decimal("1") <= value < Decimal("10")
                and "," in raw
                and len(raw.split(",", 1)[1]) == 3
            ):
                return f"{self._format_decimal(value)} "
            if value >= Decimal("1000"):
                return f"{self._format_decimal(value / Decimal('1000'))} "
            return f"{self._format_decimal(value)} "

        if unit in {"кг", "kg", "килограмм", "килограмма", "килограммов"}:
            return f"{self._format_decimal(value)} "

        if unit in {"г", "гр", "грамм", "грамма", "граммов", "gram", "grams"}:
            return f"{self._format_decimal(value)} "

        return None

'''

p.write_text(t[:start] + new + t[end:], encoding="utf-8")
print("VOLUME DETECTOR FIXED")
