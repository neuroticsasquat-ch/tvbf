"""The environment this project builds: Prefect, at the version the pin names."""

import tomllib
from pathlib import Path

import prefect

PYPROJECT = Path(__file__).parents[1] / "pyproject.toml"


def test_prefect_is_the_pinned_version() -> None:
    dependencies = tomllib.loads(PYPROJECT.read_text())["project"]["dependencies"]

    print(f"prefect {prefect.__version__}")
    assert f"prefect=={prefect.__version__}" in dependencies
