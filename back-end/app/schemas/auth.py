"""Pydantic schemas for authentication and operator profiles."""

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    """Payload for operator login authentication."""

    username: str = Field(..., description="Email address or username of operator")
    password: str = Field(..., description="Plain text password")


class OperatorProfile(BaseModel):
    """Authenticated operator profile summary."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: str
    jurisdiction_code: Optional[str] = "NATIONAL_DEOC"


class TokenResponseData(BaseModel):
    """Token payload returning JWT access token and operator details."""

    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int = 86400
    operator: OperatorProfile


class TokenResponse(BaseModel):
    """Standard API envelope for successful authentication."""

    success: bool = True
    data: TokenResponseData
    meta: Dict[str, Any] = Field(default_factory=dict)
