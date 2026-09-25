#  ______ libraries ...
from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File, status
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel
from typing import Optional
import numpy as np

#  ______ Config ...
from app.core.database import SessionLocal

#  ______ Utils  ...
from app.core.logger import logger

#  ______ Modules ...
from app.features.auth import User

#  ______ Pydantic Schemas ...
class UserUpdateSchema(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    # Add other fields as needed based on your UserData interface

class UserStatusUpdateSchema(BaseModel):
    is_active: bool

#  ______ startup ...
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

#  ______Router instance ...
router = APIRouter(prefix="/users", tags=["Users"])

# ============ USER ROUTES ============

@router.get("/", status_code=status.HTTP_200_OK)
async def get_users(
    db: Session = Depends(get_db)
):
    """Get all users"""
    try:
        users = db.query(User).all()
        
        # Convert to list of dictionaries for JSON serialization
        user_list = [
            {
                "id": str(user.id),
                "name": getattr(user, 'name', ''),
                "email": getattr(user, 'email', ''),
                "role": getattr(user, 'role', ''),
                "is_active": getattr(user, 'is_active', True),
                "department": getattr(user, 'department', True),
                "joined_at": getattr(user, 'joined_at', True),
                "registration_number": getattr(user, 'registration_number', True),
                # Add other fields as needed
            }
            for user in users
        ]
        
        return user_list  # Return array directly to match your React service expectation
    except Exception as e:
        logger.error(f"Error fetching users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch users"
        )


@router.post("/{user_id}", status_code=status.HTTP_200_OK)
async def update_user(
    user_id: str,
    user_data: UserUpdateSchema,
    db: Session = Depends(get_db)
):
    """Update a user"""
    try:
        # 1. Fetch the user from the database
        user = db.query(User).filter(User.id == user_id).first()
        
        # 2. If the user doesn't exist, raise a 404 error
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {user_id} not found"
            )
        
        # 3. Update the user fields
        update_data = user_data.dict(exclude_unset=True)  # Only update provided fields
        
        for field, value in update_data.items():
            setattr(user, field, value)
        
        # 4. Commit the changes
        db.commit()
        db.refresh(user)
        
        # 5. Return the updated user
        return {
            "id": str(user.id),
            "name": getattr(user, 'name', ''),
            "email": getattr(user, 'email', ''),
            "role": getattr(user, 'role', ''),
            "is_active": getattr(user, 'is_active', True),
            # Add other fields as needed
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user"
        )


@router.patch("/{user_id}/status", status_code=status.HTTP_200_OK)
async def update_user_status(
    user_id: str,
    status_data: UserStatusUpdateSchema,
    db: Session = Depends(get_db)
):
    """Toggle user active status"""
    try:
        # 1. Fetch the user from the database
        user = db.query(User).filter(User.id == user_id).first()
        
        # 2. If the user doesn't exist, raise a 404 error
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {user_id} not found"
            )
        
        # 3. Update the status
        user.is_active = status_data.is_active
        
        # 4. Commit the changes
        db.commit()
        db.refresh(user)
        
        # 5. Return the updated user
        return {
            "id": str(user.id),
            "name": getattr(user, 'name', ''),
            "email": getattr(user, 'email', ''),
            "role": getattr(user, 'role', ''),
            "is_active": user.is_active,
            # Add other fields as needed
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating status for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user status"
        )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Delete a user"""
    try:
        # 1. Fetch the user from the database
        user = db.query(User).filter(User.id == user_id).first()
        
        # 2. If the user doesn't exist, raise a 404 error
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {user_id} not found"
            )
        
        # 3. Delete the user and commit the transaction
        db.delete(user)
        db.commit()
        
        # 4. Return nothing (HTTP 204 No Content)
        return None
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        )