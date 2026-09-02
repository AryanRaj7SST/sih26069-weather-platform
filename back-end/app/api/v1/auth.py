"""Authentication API Router for Operator Login."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, OperatorProfile, TokenResponse, TokenResponseData

router = APIRouter()


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Operator Login Authentication",
    description="Authenticates disaster management operator credentials and returns a signed 24h JWT bearer token.",
)
async def login_operator(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate operator by email/username and password."""
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
