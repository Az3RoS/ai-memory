# conftest.py — shared test fixtures for ai-memory
import pytest

@pytest.fixture(scope='session')
def sample_project_dir(tmp_path_factory):
    return tmp_path_factory.mktemp('sample_project')
