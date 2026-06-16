from app.models.dashboard import Dashboard
from app.models.system import SystemOverview
from app.services.inspection_service import current_timestamp, get_service


def get_system_overview() -> SystemOverview:
    return get_service().get_system_overview()


def get_dashboard() -> Dashboard:
    return get_service().get_dashboard()
