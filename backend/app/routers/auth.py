from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from ..dependencies import get_current_user_id
from ..database import get_db
from ..models import User
from ..schemas import UserResponse, UserUpdate

router = APIRouter(prefix="/auth", tags=["auth"])

@router.get("/me", response_model=UserResponse)
async def get_current_user(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(User)
        .where(
            User.id == user_id
        )
    )

    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user

@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    payload: UserUpdate,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(User)
        .where(
            User.id == user_id
        )
    )

    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)

    await db.commit()
    await db.refresh(user)
    return user