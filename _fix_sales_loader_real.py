from pathlib import Path

p = Path("svo/sales_loader.py")
s = p.read_text(encoding="utf-8")

start = s.index("    def _find_name_column_index(self, worksheet) -> int:")
end = s.index("\n    def load(self, filename: str | Path)", start)

new_method = '''    def _find_name_column_index(self, worksheet) -> int:
        # First identify the column containing actual product names.
        # The SALES template has a damaged/incorrect "аименование" header
        # in column A, while product names are stored in column B.
        for column_index in range(worksheet.max_column):
            product_name_count = 0

            for row in worksheet.iter_rows(
                min_row=2,
                max_row=worksheet.max_row,
                values_only=True,
            ):
                if column_index >= len(row):
                    continue

                value = row[column_index]
                if _looks_like_product_name(value):
                    product_name_count += 1

            if product_name_count >= 2:
                return column_index

        raise ValueError(
            "Could not determine SALES product-name column from worksheet"
        )
'''

s = s[:start] + new_method + s[end:]
p.write_text(s, encoding="utf-8")

print("SALES PRODUCT NAME COLUMN FIXED")
