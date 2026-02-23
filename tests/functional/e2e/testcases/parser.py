import json
from pathlib import Path
from typing import cast

# Path to the shared testcases directory in athena-protobufs
_REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent
TESTCASES_DIR = _REPO_ROOT / "athena-protobufs" / "testcases"


class AthenaTestCase:
    def __init__(
        self,
        filepath: str,
        expected_output: list[float],
        classification_labels: list[str],
    ) -> None:
        self.id: str = "/".join(
            Path(filepath).parts[-2:]
        )  # e.g. "ducks/duck1.jpg"
        self.filepath: str = filepath
        self.expected_output: dict[str, float] = dict(
            zip(classification_labels, expected_output, strict=True)
        )
        self.classification_labels: list[str] = classification_labels


def load_test_cases(dirname: str = "benign_model") -> list[AthenaTestCase]:
    with Path.open(
        Path(TESTCASES_DIR / dirname / "expected_outputs.json"),
    ) as f:
        test_cases = cast(
            "dict[str, list[str] | list[list[str | list[float]]]]", json.load(f)
        )
    classification_labels = cast(
        "list[str]", test_cases["classification_labels"]
    )
    images = cast("list[list[str | list[float]]]", test_cases["images"])
    return [
        AthenaTestCase(
            str(
                Path(TESTCASES_DIR / dirname / "images" / cast("str", item[0]))
            ),
            cast("list[float]", item[1]),
            classification_labels,
        )
        for item in images
    ]
