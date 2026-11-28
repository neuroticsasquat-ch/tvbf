from collections.abc import Iterator

import pytest
from prefect.testing.utilities import prefect_test_harness


@pytest.fixture(autouse=True, scope="session")
def prefect_server() -> Iterator[None]:
    """One in-process Prefect server for the whole run: starting one takes seconds."""
    with prefect_test_harness():
        yield
