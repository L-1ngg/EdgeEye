import pytest

from app.core.config import settings
from app.services.inspection_service import reset_service_for_tests

settings.camera_bridge_enabled = False


@pytest.fixture(autouse=True)
def isolated_database(tmp_path):
    reset_service_for_tests(str(tmp_path / "edgeeye-test.db"))
