from pathlib import Path

p = Path("svo/sales_loader.py")
s = p.read_text(encoding="utf-8")

start = s.index("    def load(self, filename: str | Path)")

new_load = r'''    def load(self, filename: str | Path) -> list[ArrivalItem]:
        wb = load_workbook(filename=filename, data_only=True)
        worksheet = wb.active
        name_column_index = self._find_name_column_index(worksheet)

        items: list[ArrivalItem] = []
        current_context = ""
        current_context_type = ""

        import re

        powder_pattern = re.compile(
            r"^\u041f\u043e\u0440\u043e\u0448\u043e\u043a\s+(\d+(?:[.,]\d+)?)\s+(.+)$",
            re.IGNORECASE,
        )

        magina_pattern = re.compile(
            r"^\u0413\u0435\u043b\u044c\s+\u043a\u043e\u043d\u0434\u0438\u0446\u0438\u043e\u043d\u0435\u0440\s+1400\s+MAGINA$",
            re.IGNORECASE,
        )

        elegant_pattern = re.compile(
            r"^SVO\s+1500\s+ELEGANT\s+WHITE$",
            re.IGNORECASE,
        )

        powder_aromas = {
            "\u041b\u0410\u0412\u0410\u041d\u0414\u0410": "Lavender",
            "\u0427\u0415\u0420\u041d\u042b\u0419": "Black",
            "\u0420\u041e\u0417\u0410": "Rose",
            "\u041f\u041e\u0414\u0421\u041d\u0415\u0416\u041d\u0418\u041a": "Snowdrop",
            "\u041f\u041e\u0414\u0421\u041d\u0415\u0416\u041d\u041c\u041a": "Snowdrop",
            "\u0413\u041e\u0420\u041d\u042b\u0419": "Mountain Breeze",
            "\u0413\u041e\u0420\u041d\u0412\u0419": "Mountain Breeze",
            "\u0413\u041e\u0420\u0413\u042b\u0419": "Mountain Breeze",
            "\u041b\u0415\u041c\u041e\u041d": "Lemon",
            "\u0414\u0415\u0422\u0421\u041a\u0418\u0419": "Baby",
        }

        elegant_aromas = {
            "WHITE": "White",
            "MANGO": "Mango",
            "FLORIAL MIST": "Floral Mist",
            "MIDNIGHT": "Midnight",
            "SPRING": "Spring",
            "SWEET TROPIK": "Sweet Tropic",
            "VELVET": "Velvet",
            "DREAM": "Dream",
            "BLACK": "Black",
        }

        for excel_row, row in enumerate(
            worksheet.iter_rows(min_row=2, values_only=True),
            start=2,
        ):
            name = row[name_column_index] if name_column_index < len(row) else None
            if name is None:
                continue

            text = str(name).strip()
            if not text:
                continue

            powder_match = powder_pattern.match(text)

            if powder_match:
                size_raw = powder_match.group(1).replace(",", ".")
                size = str(float(size_raw)).rstrip("0").rstrip(".")
                source_aroma = powder_match.group(2).strip()
                aroma = powder_aromas.get(
                    source_aroma.upper(),
                    source_aroma,
                )

                current_context = (
                    f"\u041f\u043e\u0440\u043e\u0448\u043e\u043a \u0441\u0442\u0438\u0440\u0430\u043b\u044c\u043d\u044b\u0439 SVO {size} \u043a\u0433"
                )
                current_context_type = "powder"
                match_name = f"{current_context} {aroma}"

            elif magina_pattern.match(text):
                current_context = (
                    "\u041a\u043e\u043d\u0434\u0438\u0446\u0438\u043e\u043d\u0435\u0440 SVO Magina 1,44 \u043b"
                )
                current_context_type = "magina"
                match_name = current_context

            elif elegant_pattern.match(text):
                current_context = (
                    "\u0416\u041c\u0421 SVO Elegant 1,5 \u043b"
                )
                current_context_type = "elegant_15"
                match_name = f"{current_context} White"

            elif current_context_type == "powder":
                if text.upper().startswith("OXGEEN"):
                    current_context = ""
                    current_context_type = ""
                    match_name = text
                elif len(text) < 40:
                    aroma = powder_aromas.get(text.upper(), text)
                    match_name = f"{current_context} {aroma}"
                else:
                    current_context = ""
                    current_context_type = ""
                    match_name = text

            elif current_context_type == "elegant_15" and len(text) < 40:
                aroma = elegant_aromas.get(text.upper(), text)
                match_name = f"{current_context} {aroma}"

            elif current_context_type == "magina" and len(text) < 40:
                match_name = f"{current_context} {text}"

            else:
                match_name = text
                current_context = ""
                current_context_type = ""

            items.append(
                ArrivalItem(
                    row_number=excel_row,
                    source_name=text,
                    match_name=match_name,
                )
            )

        return items
'''

p.write_text(s[:start] + new_load, encoding="utf-8")
print("SALES LOAD REPLACED CLEANLY")
