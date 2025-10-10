import json
import os


# These files were NOT in the original Roke test set and were added later so manually excluded from tests.
EXCLUDED_FILENAMES = [
    "mountains/pexels-suketdedhia-671659.jpg",
    "lakeside/pexels-pixabay-210289.jpg",
    "lakeside/pexels-pixabay-210290.jpg",
    "lakeside/pexels-pixabay-210291.jpg",
]


class AthenaTestCase:
    def __init__(self, filepath: str, expected_output: list[float], classification_labels: list[str]) -> None:
        self.id = "/".join(filepath.split("/")[-2:])  # e.g. "ducks/duck1.jpg"
        self.filepath = filepath
        self.expected_output = dict(zip(classification_labels, expected_output, strict=True))
        self.classification_labels = classification_labels


def load_test_cases(dirname: str = "benign_model") -> list[AthenaTestCase]:
    with open(os.path.join(os.path.dirname(__file__), dirname, "expected_outputs.json"), "r") as f:
        test_cases = json.load(f)
    return [
        AthenaTestCase(
            os.path.join(os.path.dirname(__file__), dirname, "images", item[0]),
            item[1],
            test_cases["classification_labels"],
        )
        for item in test_cases["images"]
        if item[0] not in EXCLUDED_FILENAMES
    ]
