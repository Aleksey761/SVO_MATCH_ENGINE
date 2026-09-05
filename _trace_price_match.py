from svo.engine import Engine

engine = Engine()
engine.run_price_matching(
    master_file=r"output\MASTER_DATASET.xlsx",
    price_file=r"data\PRC.xlsx",
    output_file=r"output\price_match.xlsx",
)
