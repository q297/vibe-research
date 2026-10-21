"""Demo accounts and access control: a user only sees the companies linked to them"""

import hmac
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.config import Settings, get_settings
from app.contracts.common import ErrorCode
from app.contracts.insights import UserRole
from app.contracts.platform import Me
from app.errors import AppError
from app.stubs import load_fixture


class UserRecord(BaseModel):
    user_id: str
    username: str
    password: str
    display_name: str
    role: UserRole
    client_ids: list[str]
    is_demo_admin: bool = False

    def to_me(self) -> Me:
        return Me.model_validate(self.model_dump(exclude={"username", "password"}))


_USERS = {u["username"]: UserRecord.model_validate(u) for u in load_fixture("users.json")}
_USERS_BY_ID = {u.user_id: u for u in _USERS.values()}

_bearer = HTTPBearer(auto_error=False)


def authenticate(username: str, password: str) -> UserRecord | None:
    user = _USERS.get(username)
    if user and hmac.compare_digest(user.password, password):
        return user
    return None


def issue_token(user: UserRecord, settings: Settings) -> str:
    payload = {
        "sub": user.user_id,
        "exp": datetime.now(UTC) + timedelta(minutes=settings.jwt_ttl_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> UserRecord:
    if credentials is None:
        raise AppError(401, ErrorCode.UNAUTHORIZED, "Missing bearer token")
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise AppError(401, ErrorCode.UNAUTHORIZED, "Invalid token") from exc
    user = _USERS_BY_ID.get(payload.get("sub", ""))
    if user is None:
        raise AppError(401, ErrorCode.UNAUTHORIZED, "Unknown user")
    return user


CurrentUser = Annotated[UserRecord, Depends(current_user)]


def ensure_client_access(user: UserRecord, client_id: str) -> None:
    if client_id not in user.client_ids:
        raise AppError(403, ErrorCode.FORBIDDEN, "No access to this client")
