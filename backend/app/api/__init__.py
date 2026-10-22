from fastapi import APIRouter

from app.api import admin, clients, feedback, insights, news, platform
from app.errors import ERROR_RESPONSES

router_v1 = APIRouter(prefix="/v1", responses=ERROR_RESPONSES)
for module in (platform, clients, news, insights, feedback, admin):
    router_v1.include_router(module.router)
