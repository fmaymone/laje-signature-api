"""CRUD de usuários."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.security import hash_password
from app.db.session import get_db
from api.schemas_users import UserCreate, UserListResponse, UserRead, UserUpdate

router = APIRouter(prefix="/v1/users", tags=["users"])


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    exists = db.scalar(select(User).where(User.email == payload.email.lower()))
    if exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="E-mail já cadastrado.",
        )

    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name.strip(),
        hashed_password=hash_password(payload.password),
        role=payload.role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("", response_model=UserListResponse)
def list_users(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> UserListResponse:
    total = db.scalar(select(func.count()).select_from(User)) or 0
    items = db.scalars(select(User).order_by(User.created_at.desc()).offset(skip).limit(limit)).all()
    return UserListResponse(items=list(items), total=total)


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: uuid.UUID, db: Session = Depends(get_db)) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.")
    return user


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    db: Session = Depends(get_db),
) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.")

    data = payload.model_dump(exclude_unset=True)
    password = data.pop("password", None)
    if password:
        user.hashed_password = hash_password(password)
    if "full_name" in data and data["full_name"] is not None:
        user.full_name = data["full_name"].strip()
    if "role" in data and data["role"] is not None:
        user.role = data["role"]
    if "is_active" in data and data["is_active"] is not None:
        user.is_active = data["is_active"]

    db.add(user)
    db.commit()
    db.refresh(user)
    return user
