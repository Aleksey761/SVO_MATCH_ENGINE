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

    def run(self, master_file: str | Path,
            arrival_file: str | Path,
            output_file: str | Path):

        master = self.loader.load_master(master_file)
        arrival = self.loader.load_arrival(arrival_file)

        for item in arrival:
            self.normalizer.normalize(item)

        matcher = Matcher(master)
        matcher.match_all(arrival)

        Reporter().write(arrival, output_file)

        match_count = sum(1 for i in arrival if i.status == "MATCH")
        review_count = sum(1 for i in arrival if i.status == "REVIEW")

        return {
            "master": len(master),
            "arrival": len(arrival),
            "match": match_count,
            "review": review_count,
            "output": str(output_file),
        }
