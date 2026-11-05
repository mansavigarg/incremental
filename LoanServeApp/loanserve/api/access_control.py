"""Signed bearer tokens, role checks and audit entries."""

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config.constants import ADMIN_ONLY_METHODS, AUDIT_LOG_PATH, JWT_ALGORITHM, JWT_SECRET_KEY, TOKEN_LIFETIME_MINUTES


BEARER = HTTPBearer(auto_error=False)


class AccessControl:
    def __init__(self):
        self.secret_key = os.getenv("LOANSERVE_JWT_SECRET", JWT_SECRET_KEY)
        self.open_mode = os.getenv("LOANSERVE_OPEN_MODE") == "1"

    def issue_token(self, user_name, role):
        expiry = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_LIFETIME_MINUTES)
        return jwt.encode({"sub": user_name, "role": role, "exp": expiry}, self.secret_key, algorithm=JWT_ALGORITHM)

    def read_token(self, authorization_header):
        if not authorization_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Bearer token required")
        try:
            return jwt.decode(authorization_header[7:], self.secret_key, algorithms=[JWT_ALGORITHM])
        except jwt.PyJWTError as error:
            raise HTTPException(status_code=401, detail=f"Invalid bearer token: {error}") from error

    def authorise(self, request: Request, offered: Annotated[HTTPAuthorizationCredentials | None, Depends(BEARER)] = None):
        claims = self.read_token(request.headers.get("authorization", ""))
        if request.method in ADMIN_ONLY_METHODS and claims.get("role") != "administrator":
            raise HTTPException(status_code=403, detail=f"Role {claims.get('role')} cannot use {request.method}")
        return claims

    def record_audit_entry(self, user_name, action):
        path = Path(os.getenv("LOANSERVE_AUDIT_LOG", AUDIT_LOG_PATH))
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as log:
            log.write(f"{datetime.now(timezone.utc).isoformat()} {user_name} {action}\n")
