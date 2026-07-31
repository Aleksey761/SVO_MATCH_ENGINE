from pathlib import Path

from svo.engine import Engine


def main():
    base = Path(__file__).parent
    result = Engine().run(input_dir=base / "data")
    print("=" * 40)
    print("SVO Match Engine v0.2")
    print("=" * 40)
    print(f"MASTER FILE : {result['master_file']}")
    print(f"ARRIVAL FILE: {result['arrival_file']}")
    print(f"SALES FILE  : {result['sales_file']}")
    print(f"ARRIVAL DATE: {result['arrival_date']}")
    print(f"SALES DATE  : {result['sales_date']}")
    print(f"MASTER : {result['master']}")
    print(f"ARRIVAL: {result['arrival']}")
    print(f"MATCH  : {result['match']}")
    print(f"REVIEW : {result['review']}")
    print("RESULT :", result['output'])
    print("ARRIVAL MATCH FILE:", result['matched_arrival_output'])


if __name__ == '__main__':
    main()
