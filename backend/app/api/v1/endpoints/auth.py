from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.db.session import get_db
from app.models.models import Organization, User, SystemSettings, AuditLog
from app.schemas.schemas import RegisterRequest, LoginRequest, TokenResponse, RefreshRequest
from app.core.security import (
    hash_password, verify_password, create_access_token, create_refresh_token,
    decode_token, create_email_verification_token
)
from app.services.email_service import email_service

router = APIRouter()


@router.post("/register", response_model=dict, status_code=201)
async def register(
    payload: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    # Check if email exists
    existing = await db.execute(select(User).where(User.email == payload.admin_email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create organization
    org = Organization(
        name=payload.company_name,
        website=payload.website,
        company_size=payload.company_size,
        industry=payload.industry,
    )
    db.add(org)
    await db.flush()

    # Create default settings
    settings_obj = SystemSettings(organization_id=org.id)
    db.add(settings_obj)

    # Create admin user
    from app.models.models import UserRole
    user = User(
        organization_id=org.id,
        email=payload.admin_email,
        full_name=payload.first_admin_name,
        hashed_password=hash_password(payload.password),
        role=UserRole.ORG_ADMIN,
    )
    db.add(user)
    await db.commit()

    # Send verification email
    token = create_email_verification_token(payload.admin_email)
    background_tasks.add_task(
        email_service.send_email_verification,
        payload.admin_email,
        payload.first_admin_name,
        token,
    )

    return {"message": "Registration successful. Please check your email to verify your account."}


@router.get("/verify-email")
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    payload = decode_token(token)
    if not payload or payload.get("type") != "email_verify":
        raise HTTPException(status_code=400, detail="Invalid or expired verification link")

    email = payload.get("sub")
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.email_verified = True
    
    org_result = await db.execute(
        select(Organization).where(Organization.id == user.organization_id)
    )
    org = org_result.scalar_one_or_none()
    if org:
        org.email_verified = True

    await db.commit()
    return {"message": "Email verified successfully"}


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")

    # user.last_login = datetime.utcnow()

    from sqlalchemy import update
    await db.execute(
        update(User)
        .where(User.email == payload.email)
        .values(last_login=datetime.utcnow())
    )

    # Audit log
    log = AuditLog(
        user_id=user.id,
        organization_id=user.organization_id,
        action="login",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(log)
    await db.commit()

    token_data = {"sub": str(user.id), "org": str(user.organization_id), "role": user.role.value}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    token_data = decode_token(payload.refresh_token)
    if not token_data or token_data.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_id = token_data.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    new_data = {"sub": str(user.id), "org": str(user.organization_id), "role": user.role.value}
    return TokenResponse(
        access_token=create_access_token(new_data),
        refresh_token=create_refresh_token(new_data),
    )


@router.get("/me")
async def get_me(db: AsyncSession = Depends(get_db), credentials: str = None):
    from app.api.deps import get_current_user
    # Handled via dependency in routes that need auth
    return {"message": "Use /auth/me with Authorization header"}
