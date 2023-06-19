import pathlib

import pytest


@pytest.fixture
def resources_dir():
    return pathlib.Path(__file__).parent.resolve() / "resources"
