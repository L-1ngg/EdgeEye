import pytest

from app.services.inspection_service import reset_service_for_tests


@pytest.fixture(autouse=True)
def isolated_database(tmp_path):
    reset_service_for_tests(str(tmp_path / "edgeeye-test.db"))
