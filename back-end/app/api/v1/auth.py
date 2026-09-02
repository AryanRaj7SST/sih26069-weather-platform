"""Authentication API Router for Operator Login and Token Management."""

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_operator
from app.core.rate_limiter import login_rate_limiter
from app.core.security import create_access_token, create_sse_ticket, revoke_token, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, OperatorProfile, TokenResponse, TokenResponseData

router = APIRouter()


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Operator Login Authentication",
    description="Authenticates disaster management operator credentials and returns a signed 24h JWT bearer token with sliding window rate limiting.",
)
async def login_operator(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate operator by email/username and password with rate limiting protection."""
    # 1. Rate Limiting Check (Client IP / Username bucket)
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"login:{client_ip}"
    if not login_rate_limiter.is_allowed(rate_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Too many failed login attempts. Please wait 60 seconds before trying again.",
            },
        )

    email_or_user = payload.username.strip().lower()

    stmt = select(User).where(
        User.email.ilike(email_or_user),
        User.is_active.is_(True),
    )
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_CREDENTIALS",
                "message": "Incorrect email or password. Access denied.",
            },
        )

    # Successful login: reset rate limit counter
    login_rate_limiter.reset(rate_key)

    # Generate JWT token
    access_token = create_access_token(
        subject=str(user.id),
        role=user.role,
        extra_claims={
            "email": user.email,
            "full_name": user.full_name,
        },
    )

    profile = OperatorProfile(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        jurisdiction_code="NATIONAL_DEOC",
    )

    return TokenResponse(
        success=True,
        data=TokenResponseData(
            access_token=access_token,
            token_type="bearer",
            expires_in_seconds=86400,
            operator=profile,
        ),
    )


@router.post(
    "/sse-ticket",
    status_code=status.HTTP_200_OK,
    summary="Generate Single-Use SSE Ticket Nonce",
    description="Exchanges an authenticated operator session for a 30-second single-use ticket nonce to establish secure EventSource streams without leaking tokens in URLs.",
)
async def generate_sse_ticket(
    operator: User = Depends(get_current_operator),
) -> dict:
    """Generate a single-use nonce for SSE connection establishment."""
    ticket = create_sse_ticket(subject=str(operator.id), role=operator.role)
    return {
        "success": True,
        "data": {
            "ticket": ticket,
            "expires_in_seconds": 30,
        },
    }


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Operator Logout & Token Revocation",
    description="Revokes the current JWT bearer access token, invalidating any active sessions across the platform.",
)
async def logout_operator(
    authorization: str = Header(..., description="Bearer access token to revoke"),
    _operator: User = Depends(get_current_operator),
) -> dict:
    """Explicitly revoke token and terminate operator session."""
    token = authorization.replace("Bearer ", "").strip()
    if token:
        revoke_token(token)
    return {
        "success": True,
        "data": {
            "message": "Operator session revoked successfully.",
        },
    }

