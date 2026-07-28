"""Auth JWT no contrato do Minimals (/api/auth/*)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.jwt_tokens import create_access_token, decode_access_token, parse_user_id, user_public_dict
from app.db.models import User, UserRole
from app.db.security import hash_password, verify_password
from app.db.session import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])
bearer_scheme = HTTPBearer(auto_error=False)


class SignInRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    firstName: str = Field(min_length=1, max_length=100)
    lastName: str = Field(min_length=1, max_length=100)


class TokenResponse(BaseModel):
    accessToken: str


class MeResponse(BaseModel):
    user: dict


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado.")
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = parse_user_id(payload)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado.",
        ) from exc

    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário inválido.")
    return user


@router.post("/sign-in", response_model=TokenResponse)
def sign_in(payload: SignInRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha inválidos.",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuário inativo.")
    return TokenResponse(accessToken=create_access_token(user))


@router.post("/sign-up", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def sign_up(payload: SignUpRequest, db: Session = Depends(get_db)) -> TokenResponse:
    email = payload.email.lower()
    exists = db.scalar(select(User).where(User.email == email))
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="E-mail já cadastrado.")

    full_name = f"{payload.firstName.strip()} {payload.lastName.strip()}".strip()
    user = User(
        id=uuid.uuid4(),
        email=email,
        full_name=full_name,
        hashed_password=hash_password(payload.password),
        role=UserRole.staff,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenResponse(accessToken=create_access_token(user))


@router.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user)) -> MeResponse:
    return MeResponse(user=user_public_dict(user))
