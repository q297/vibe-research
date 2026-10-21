from typing import Annotated

from fastapi import Depends

from app.config import Settings, get_settings
from app.services.registry import Services, get_services

Svc = Annotated[Services, Depends(get_services)]
Cfg = Annotated[Settings, Depends(get_settings)]
