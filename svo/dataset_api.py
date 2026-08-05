from pathlib import Path

from .dataset_builder import DatasetBuilder, DatasetRecord


def load_master_dataset(
    dataset_file: str | Path = "output/MASTER_DATASET.xlsx",
    *,
    input_dir: str | Path = "data",
    rebuild_if_missing: bool = True,
) -> list[DatasetRecord]:
    """Single entrypoint for consumers to access MASTER_DATASET."""
    builder = DatasetBuilder()
    dataset_path = Path(dataset_file)

    if rebuild_if_missing and not dataset_path.exists():
        builder.build(input_dir=input_dir, output_file=dataset_path)

    return builder.load_dataset(dataset_path)
