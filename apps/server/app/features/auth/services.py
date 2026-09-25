from app.core.logger import logger

# from app.services.face_service import FaceService
# from app.services.file_upload import SupabaseBlobUpload 

from app.features.auth import UserSignup, User
from fastapi.exceptions import HTTPException
from app.features.face_embedding import FaceEmbedding


class AuthService: 
    def __init__(self, db, face_service, blob_upload):

        self.face_service = face_service
        self.blob_upload = blob_upload
        self.db = db
        
    async def signup(self, payload:UserSignup):
        
        name , email , department , image = payload.model_dump().values()

        # ✅ 1. Check if user already exists
        existing_user = self.db.query(User).filter(User.email == payload.email).first()

        if existing_user:
            raise HTTPException(409, "Email already registered")

        uploaded_filedata = self.blob_upload.upload_file_to_supabase(image)

        # ✅ 2. Create user in database
        new_user = User(
            registration_number=generate_registration_number(),
            name=name,
            email=email,
            department=department
        )
        self.db.add(new_user)
        self.db.flush()  # Get user.id without committing

        # ✅ 3. Extract embedding from uploaded image
        try:
            embedding = await self.face_service.extract_embedding(image)
            # This already validates: exactly 1 face, no multiple faces
        except ValueError as e:
            raise HTTPException(400, str(e))

        # ✅ 4. Convert embedding to list for pgvector
        embedding_list = self.face_service.get_embedding_for_storage(embedding)

        # ✅ 5. Store embedding in database
        face_embedding = FaceEmbedding(
            student_id=new_user.id,
            embedding=embedding_list
        )
        self.db.add(face_embedding)

        # ✅ 6. Commit everything
        self.db.commit()
        self.db.refresh(new_user)

        # ✅ 7. Return response
        return {
            "status": "success",
            "student_id": new_user.id,
            "registration_number": new_user.registration_number,
            "name": new_user.name
        }