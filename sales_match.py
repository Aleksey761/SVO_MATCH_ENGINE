from pathlib import Path

from svo.engine import Engine


def main():
    base = Path(__file__).parent
    result = Engine().run_sales(input_dir=base / "data")
    print("=" * 40)
    print("SVO Sales Engine v0.1")
    print("=" * 40)
    print("SALES")
    print(f"Rows   : {result['rows']}")
    print(f"MATCH  : {result['match']}")
    print(f"REVIEW : {result['review']}")
    print(f"DATE   : {result['sales_date']}")
    print("OUTPUT :", result['output'])


if __name__ == '__main__':
    main()