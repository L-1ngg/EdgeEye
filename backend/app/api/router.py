from fastapi import APIRouter

from app.api.routes import advice, assets, dashboard, health, inspections, reports, system

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(system.router, prefix="/system", tags=["system"])
api_router.include_router(dashboard.router, tags=["dashboard"])
api_router.include_router(inspections.router, tags=["inspections"])
api_router.include_router(assets.router, tags=["assets"])
api_router.include_router(advice.router, tags=["advice"])
api_router.include_router(reports.router, tags=["reports"])
