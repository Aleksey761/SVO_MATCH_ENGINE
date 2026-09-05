from pathlib import Path

p = Path("svo/sales_loader.py")
s = p.read_text(encoding="utf-8")

old = '''            for index, header in enumerate(normalized_headers):
                if header == "":
                    return index
'''

new = '''            for index, header in enumerate(normalized_headers):
                if header == "":
                    # SALES template has the "аименование" label in the
                    # numbering column A, while actual product names are
                    # stored in the adjacent column B.
                    sample_values = []
                    for data_row in worksheet.iter_rows(
                        min_row=2,
                        max_row=min(worksheet.max_row, 20),
                        values_only=True,
                    ):
                        if index < len(data_row):
                            sample_values.append(data_row[index])

                    if any(_looks_like_product_name(value) for value in sample_values):
                        return index

                    adjacent_index = index + 1
                    if adjacent_index < len(row):
                        adjacent_values = []
                        for data_row in worksheet.iter_rows(
                            min_row=2,
                            max_row=min(worksheet.max_row, 20),
                            values_only=True,
                        ):
                            if adjacent_index < len(data_row):
                                adjacent_values.append(data_row[adjacent_index])

                        if any(_looks_like_product_name(value) for value in adjacent_values):
                            return adjacent_index

                    continue
'''

if old not in s:
    raise SystemExit("SALES NAME HEADER BLOCK NOT FOUND")

s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("SALES NAME COLUMN FIXED FOR ACTUAL WORKBOOK")
