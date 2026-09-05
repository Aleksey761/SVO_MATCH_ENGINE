from pathlib import Path

p = Path("svo/sales_loader.py")
s = p.read_text(encoding="utf-8")

start = s.index("    def load(self, filename: str | Path) -> list[ArrivalItem]:")
end = len(s)

new_load = '''    def load(self, filename: str | Path) -> list[ArrivalItem]:
        wb = load_workbook(filename=filename, data_only=True)
        worksheet = wb.active
        name_column_index = self._find_name_column_index(worksheet)
        items: list[ArrivalItem] = []
        current_context = ""

        # Product block headers normally contain both a product type and
        # a volume. Short following rows (aromas/variants) inherit that
        # context until the next block header.
        import re

        volume_pattern = re.compile(
            r"\\\\b\\\\d+(?:[.,]\\\\d+)?\\\\s*(?:|||)\\\\b",
            re.IGNORECASE,
        )

        def is_block_header(text: str) -> bool:
            if not volume_pattern.search(text):
                return False

            upper = text.upper()
            block_words = (
                "Ш",
                "С",
                "",
                "Ш",
                "Ь",
                "Ы",
            )
            return any(word in upper for word in block_words)

        for excel_row, row in enumerate(
            worksheet.iter_rows(min_row=2, values_only=True),
            start=2,
        ):
            name = row[name_column_index] if name_column_index < len(row) else None
            if name is None:
                continue

            raw_text = str(name)
            text = raw_text.strip()
            if not text:
                continue

            if is_block_header(text):
                current_context = text
                match_name = text
            elif current_context and len(text) < 40:
                match_name = f"{current_context} {text}".strip()
            else:
                match_name = text
                if is_block_header(text):
                    current_context = text

            items.append(
                ArrivalItem(
                    row_number=excel_row,
                    source_name=text,
                    match_name=match_name,
                )
            )

        return items
'''

s = s[:start] + new_load + "\\n"
p.write_text(s, encoding="utf-8")
print("SALES CONTEXT PARSER APPLIED")
