from pathlib import Path

from svo.loader import Loader
from svo.matcher import Matcher
from svo.normalizer import Normalizer
from svo.reporter import Reporter


class Engine:
    """Coordinates the complete matching pipeline."""

    def __init__(self):
        self.loader = Loader()
        self.normalizer = Normalizer()

    def run(
        self,
        master_file: str | Path | None = None,
        arrival_file: str | Path | None = None,
        output_file: str | Path | None = None,
        input_dir: str | Path | None = None,
    ):

        arrival_date = None
        if master_file is None or arrival_file is None:
            resolved_input = Path(input_dir) if input_dir is not None else Path("data")
            master_file, arrival_file, arrival_date = self.loader.discover_workbooks(resolved_input)

        if output_file is None:
            output_name = f"RESULT_{arrival_date}.xlsx" if arrival_date else "RESULT.xlsx"
            output_file = Path("output") / output_name
        arrival_output_date = arrival_date if arrival_date is not None else "None"
        matched_arrival_output = Path("output") / f"ARRIVAL_MATCH_{arrival_output_date}.xlsx"

        master = self.loader.load_master(master_file)
        arrival = self.loader.load_arrival(arrival_file)

        for item in arrival:
            self.normalizer.normalize(item)

        matcher = Matcher(master)
        matcher.match_all(arrival)

        reporter = Reporter()
        reporter.write(arrival, output_file, arrival_date=arrival_date)
        reporter.write_matched_arrival(arrival_file, arrival, matched_arrival_output)

        match_count = sum(1 for i in arrival if i.status == "MATCH")
        review_count = sum(1 for i in arrival if i.status == "REVIEW")

        return {
            "master": len(master),
            "arrival": len(arrival),
            "match": match_count,
            "review": review_count,
            "output": str(output_file),
            "matched_arrival_output": str(matched_arrival_output),
            "arrival_date": arrival_date,
            "master_file": str(Path(master_file)),
            "arrival_file": str(Path(arrival_file)),
        }
