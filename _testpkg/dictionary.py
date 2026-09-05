from pathlib import Path
import json


CONFIG_DIR = Path(__file__).parent.parent / "config"


def load_json(name: str):
    path = CONFIG_DIR / f"{name}.json"

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class Dictionary:

    def __init__(self):
        self.aliases = load_json("aliases")
        self.brands = load_json("brands")
        self.categories = load_json("categories")
        self.aromas = load_json("aromas")
        self.volumes = load_json("volumes")
        self.stop_words = load_json("stop_words")
        self.rules = load_json("rules")