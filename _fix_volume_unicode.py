from pathlib import Path

p = Path("svo/normalizer.py")
t = p.read_text(encoding="utf-8")

start = t.index("    def _detect_volume(")
end = t.index("    def _cleanup_candidate(", start)

new = '''    def _detect_volume(self, text: str) -> Optional[str]:
        match = self._volume_re.search(text.lower())
        if not match:
            return None

        raw = match.group(1)
        unit = match.group(2).lower()
        value = Decimal(raw.replace(",", "."))

        L = chr(0x041B)
        ML = chr(0x041C) + chr(0x041B)
        KG = chr(0x041A) + chr(0x0413)
        G = chr(0x0413)

        if unit in {"l", "liter", "liters"} or unit in {
            chr(0x043B), chr(0x043B)+chr(0x0438)+chr(0x0442)+chr(0x0440),
            chr(0x043B)+chr(0x0438)+chr(0x0442)+chr(0x0440)+chr(0x0430),
            chr(0x043B)+chr(0x0438)+chr(0x0442)+chr(0x0440)+chr(0x043E)+chr(0x0432),
        }:
            return f"{self._format_decimal(value)} {L}"

        if unit in {"ml"} or unit == chr(0x043C) + chr(0x043B):
            if (
                Decimal("1") <= value < Decimal("10")
                and "," in raw
                and len(raw.split(",", 1)[1]) == 3
            ):
                return f"{self._format_decimal(value)} {L}"
            if value >= Decimal("1000"):
                return f"{self._format_decimal(value / Decimal('1000'))} {L}"
            return f"{self._format_decimal(value)} {ML}"

        if unit in {"kg"} or unit in {
            chr(0x043A) + chr(0x0433),
            chr(0x043A)+chr(0x0438)+chr(0x043B)+chr(0x043E)+chr(0x0433)+chr(0x0440)+chr(0x0430)+chr(0x043C)+chr(0x043C),
            chr(0x043A)+chr(0x0438)+chr(0x043B)+chr(0x043E)+chr(0x0433)+chr(0x0440)+chr(0x0430)+chr(0x043C)+chr(0x043C)+chr(0x0430),
            chr(0x043A)+chr(0x0438)+chr(0x043B)+chr(0x043E)+chr(0x0433)+chr(0x0440)+chr(0x0430)+chr(0x043C)+chr(0x043C)+chr(0x043E)+chr(0x0432),
        }:
            return f"{self._format_decimal(value)} {KG}"

        if unit in {"gram", "grams"} or unit in {
            chr(0x0433),
            chr(0x0433)+chr(0x0440),
            chr(0x0433)+chr(0x0440)+chr(0x0430)+chr(0x043C)+chr(0x043C),
            chr(0x0433)+chr(0x0440)+chr(0x0430)+chr(0x043C)+chr(0x043C)+chr(0x0430),
            chr(0x0433)+chr(0x0440)+chr(0x0430)+chr(0x043C)+chr(0x043C)+chr(0x043E)+chr(0x0432),
        }:
            return f"{self._format_decimal(value)} {G}"

        return None

'''

p.write_text(t[:start] + new + t[end:], encoding="utf-8")
print("VOLUME UNICODE FIXED")
