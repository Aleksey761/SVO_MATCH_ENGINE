from pathlib import Path

from svo.engine import Engine

def main():
    base=Path(__file__).parent
    result=Engine().run(
        base/'data'/'MASTER.xlsx',
        base/'data'/'ARRIVAL.xlsx',
        base/'output'/'RESULT.xlsx'
    )
    print("="*40)
    print("SVO Match Engine v0.2")
    print("="*40)
    print(f"MASTER : {result['master']}")
    print(f"ARRIVAL: {result['arrival']}")
    print(f"MATCH  : {result['match']}")
    print(f"REVIEW : {result['review']}")
    print("RESULT :", result['output'])

if __name__=='__main__':
    main()
