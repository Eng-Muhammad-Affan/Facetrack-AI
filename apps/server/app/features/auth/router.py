# app/api/auth_router.py
from fastapi import APIRouter, Depends, HTTPException, Form , UploadFile, File
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.features.auth import User
from app.features.auth import FaceEmbedding
from app.features.attendance_log import AttendanceLog
from datetime import datetime
from dateutil import parser 

import numpy as np
from app.features.auth import generate_registration_number 
from app.features.auth.services import AuthService

# from app.auth.utils import (
#     verify_password,
#     create_access_token,
#     hash_password,
#     set_token_cookie,
#     remove_token_cookie,
#     require_auth,
#     create_reset_token,
#     verify_reset_token,
#     send_reset_email,
# )

from app.core.logger import logger

from app.services.face_service import FaceService 
from app.services.file_upload import SupabaseBlobUpload 

router = APIRouter(prefix="/auth", tags=["Auth"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ============ PUBLIC ROUTES (No auth required) ============

@router.post("/signup", status_code=201)
async def signup(
    name: str = Form(...),
    email: str = Form(...),
    department: str = Form(...),
    image: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    service = AuthService(db);

    uploaded_filedata = blob_upload.upload_file_to_supabase(image)

    # ✅ 2. Create user in database
    new_user = User(
        registration_number=generate_registration_number(),
        name=name,
        email=email,
        department=department
    )
    db.add(new_user)
    db.flush()  # Get user.id without committing

    # ✅ 3. Extract embedding from uploaded image
    try:
        embedding = await face_service.extract_embedding(image)
        # This already validates: exactly 1 face, no multiple faces
    except ValueError as e:
        raise HTTPException(400, str(e))
    
    # ✅ 4. Convert embedding to list for pgvector
    embedding_list = face_service.get_embedding_for_storage(embedding)
    
    # ✅ 5. Store embedding in database
    face_embedding = FaceEmbedding(
        student_id=new_user.id,
        embedding=embedding_list
    )
    db.add(face_embedding)
    
    # ✅ 6. Commit everything
    db.commit()
    db.refresh(new_user)
    
    # ✅ 7. Return response
    return {
        "status": "success",
        "student_id": new_user.id,
        "registration_number": new_user.registration_number,
        "name": new_user.name
    }
