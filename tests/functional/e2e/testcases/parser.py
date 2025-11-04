import json
from pathlib import Path

# These files were NOT in the original Roke test set and were added later so
# manually excluded from tests.
EXCLUDED_FILENAMES = [
    "mountains/pexels-suketdedhia-671659.jpg",
    "lakeside/pexels-pixabay-210289.jpg",
    "lakeside/pexels-pixabay-210290.jpg",
    "lakeside/pexels-pixabay-210291.jpg",
]


class AthenaTestCase:
    def __init__(
        self,
        filepath: str,
        expected_output: list[float],
        classification_labels: list[str],
    ) -> None:
        self.id: str = "/".join(
            filepath.split("/")[-2:]
        )  # e.g. "ducks/duck1.jpg"
        self.filepath: str = filepath
        self.expected_output: dict[str, float] = dict(
            zip(classification_labels, expected_output, strict=True)
        )
        self.classification_labels: list[str] = classification_labels


def load_test_cases(dirname: str = "benign_model") -> list[AthenaTestCase]:
    with Path.open(
        Path(Path(__file__).parent / dirname / "expected_outputs.json"),
    ) as f:
        test_cases = json.load(f)
    return [
        AthenaTestCase(
            str(Path(Path(__file__).parent / dirname / "images" / item[0])),
            item[1],
            test_cases["classification_labels"],
        )
        for item in test_cases["images"]
        if item[0] not in EXCLUDED_FILENAMES
    ]
