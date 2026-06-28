from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta, timezone
import secrets

from db.database import get_db
from db.models import User
from db.schemas import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    UserPublic,
    RefreshRequest,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)

from core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    require_user,
)


router = APIRouter()



@router.post("/register", response_model=UserPublic)
def register(
    data:RegisterRequest,
    db:Session=Depends(get_db)
):

    exist = db.query(User).filter(
        User.email == data.email
    ).first()


    if exist:
        raise HTTPException(
            400,
            "Email already used"
        )


    exist_username = db.query(User).filter(
        User.username == data.username
    ).first()

    if exist_username:
        raise HTTPException(
            400,
            "Username already used"
        )


    user = User(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password)
    )


    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, "Username or email already used")
    db.refresh(user)


    return user




@router.post("/login",
response_model=TokenResponse)
def login(
    data:LoginRequest,
    db:Session=Depends(get_db)
):

    user=db.query(User).filter(
        User.email==data.email
    ).first()


    if not user or not verify_password(
        data.password,
        user.hashed_password
    ):
        raise HTTPException(
            401,
            "Invalid credentials"
        )

    if not user.is_active:
        raise HTTPException(
            403,
            "This account has been deactivated"
        )


    access=create_access_token(
        str(user.id),
        user.role.value
    )


    refresh=create_refresh_token(
        str(user.id)
    )


    return {
        "access_token":access,
        "refresh_token":refresh,
        "user":user
    }


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    data: RefreshRequest,
    db: Session = Depends(get_db)
):
    from core.security import decode_token

    payload = decode_token(data.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(401, "Invalid refresh token")

    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(401, "User not found")

    access = create_access_token(str(user.id), user.role.value)
    new_refresh = create_refresh_token(str(user.id))

    return {
        "access_token": access,
        "refresh_token": new_refresh,
        "user": user
    }


@router.post("/change-password")
def change_password(
    data: ChangePasswordRequest,
    payload=Depends(require_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user or not verify_password(data.current_password, user.hashed_password):
        raise HTTPException(401, "Current password is incorrect")

    user.hashed_password = hash_password(data.new_password)
    db.commit()
    return {"message": "Password updated"}


@router.post("/forgot-password")
def forgot_password(
    data: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    """Generates a password-reset token valid for 30 minutes.

    NOTE: this app has no email-sending service configured yet, so the
    token is returned directly in the response instead of being emailed.
    In production this should be sent by email and never exposed in the
    API response — replace the return value with a generic confirmation
    message once an email provider (e.g. SMTP, SendGrid, Resend) is wired
    up in Backend/core.
    """
    user = db.query(User).filter(User.email == data.email).first()
    # Always respond the same way whether or not the email exists, to
    # avoid leaking which emails are registered.
    if not user:
        return {"message": "If that email exists, a reset link has been generated."}

    token = secrets.token_urlsafe(32)
    user.reset_token = token
    user.reset_token_expires = datetime.now(timezone.utc) + timedelta(minutes=30)
    db.commit()

    return {
        "message": "If that email exists, a reset link has been generated.",
        "dev_reset_token": token,
    }


@router.post("/reset-password")
def reset_password(
    data: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.reset_token == data.token).first()
    if not user or not user.reset_token_expires:
        raise HTTPException(400, "Invalid or expired reset token")

    expires_at = user.reset_token_expires
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(400, "Invalid or expired reset token")

    user.hashed_password = hash_password(data.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()
    return {"message": "Password reset successful"}