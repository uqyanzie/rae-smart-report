import json
from pathlib import Path
import pytest

@pytest.fixture(scope="session")
def workspace_root():
    return Path(__file__).resolve().parent.parent.parent

@pytest.fixture(scope="session")
def sample_data_dir(workspace_root):
    return workspace_root / "sample_data"

@pytest.fixture(scope="session")
def golden_totals(workspace_root):
    fixtures_path = workspace_root / "backend" / "tests" / "fixtures" / "golden_totals.json"
    if not fixtures_path.exists():
        pytest.fail(
            "golden_totals.json fixture not generated yet; "
            "it is a committed hard dependency, not an optional one"
        )
    with open(fixtures_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def raw_shopee_path(sample_data_dir):
    return sample_data_dir / "raw" / "raw_shopee_13_19_Jul26.xlsx"


@pytest.fixture(scope="session")
def raw_tts_path(sample_data_dir):
    return sample_data_dir / "raw" / "raw_tts_13_19_Jul26.xlsx"


@pytest.fixture(scope="session")
def raw_tp_path(sample_data_dir):
    return sample_data_dir / "raw" / "raw_tp_1_31_Aug26.xlsx"


@pytest.fixture(scope="session")
def raw_tts_aug_path(sample_data_dir):
    return sample_data_dir / "raw" / "raw_tts_17_23_Aug26.xlsx"

