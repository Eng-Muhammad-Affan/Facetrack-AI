# app/auth/utils.py
import bcrypt
from fastapi import Response, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from datetime import datetime, timedelta
from app.core.config import settings
from fastapi.exceptions import HTTPException
from typing import Optional
from uuid import UUID
import uuid 

oauth2_scheme = HTTPBearer(auto_error=False)

class AuthRepository:
    def __init__(self):
        pass 

    def generate_registration_number(self):
        string = str(uuid.uuid4()).replace('-', '')[:6]

        # Separate letters and numbers
        letters = [char for char in string if char.isalpha()]
        numbers = [char for char in string if char.isdigit()]

        # Combine: first 3 from letters, last 3 from numbers, or vice versa
        result = ''.join(letters[:3]) + ''.join(numbers[:3])

        return result
    def get_status():
        current_time = datetime.now()
        current_hour = current_time.hour
    
        # 2. Check the class timing logic
        if current_hour <= 15:
            return "present"
            
        elif 15 <= current_hour < 18:
            return "late"
    
        else:
            return "absent"

    def hash_password(self, password: str) -> str:
        pwd_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed_bytes = bcrypt.hashpw(pwd_bytes, salt)
        return hashed_bytes.decode('utf-8')


    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        pwd_bytes = plain_password.encode('utf-8')
        hash_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(pwd_bytes, hash_bytes)


    def create_access_token(user_id: UUID, role:str, expires_delta: timedelta = None) -> str:
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode = {
            "sub": str(user_id),
            "role":role,
            "exp": expire,
            "type": "access"
        }
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


    def create_reset_token(user_id: UUID, email: str) -> str:
        expire = datetime.utcnow() + timedelta(hours=1)
        to_encode = {
            "sub": str(user_id),
            "email": email,
            "exp": expire,
            "type": "reset"
        }
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


    def get_current_user_from_cookie(request: Request) -> int:
        try:
            token = get_token_from_cookie(request)
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id = payload.get("sub")
            if user_id is None:
                raise HTTPException(stsatus_code=401, detail="Invalid authentication credentials")
            return user_id
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        except ValueError:
            raise HTTPException(status_code=401, detail="Invalid user ID in token")
    
    
    def require_admin(request: Request) -> bool:
        try:
            token = get_token_from_cookie(request)
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id = payload.get("sub")
            role = payload.get("role")
            if user_id is None:
                raise HTTPException(status_code=401, detail="Invalid authentication credentials for admin")
            if role != "admin":
                raise HTTPException(status_code=403, detail="Admin privileges required")
            return True
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials for admin")
        except ValueError:
            raise HTTPException(status_code=401, detail="Invalid user ID in token")


    def verify_reset_token(token: str) -> Optional[dict]:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            if payload.get("type") != "reset":
                return None

            user_id = payload.get("sub")
            email = payload.get("email")

            if not user_id or not email:
                return None

            return {
                "user_id": int(user_id),
                "email": email
            }
        except JWTError:
            return None


    def set_token_cookie(response: Response, token: str) -> None:
        response.set_cookie(
            key="singitronic_access_token",
            value=token,
            httponly=True,
            secure=True,
            samesite="none",
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            path="/"
        )

    def remove_token_cookie(response: Response) -> None:
        response.delete_cookie(
            key="singitronic_access_token",
            path="/",
            httponly=True,
            secure=settings.ENVIRONMENT == "production",
            samesite="lax"
        )


    def get_token_from_cookie(request: Request) -> str:
        token = request.cookies.get("singitronic_access_token")
        if not token:
            raise HTTPException(
                status_code=401,
                detail="Not authenticated",
            )
        return token


    def get_current_user_from_cookie(request: Request) -> int:
        try:
            token = get_token_from_cookie(request)
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id = payload.get("sub")
            if user_id is None:
                raise HTTPException(stsatus_code=401, detail="Invalid authentication credentials")
            return user_id
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        except ValueError:
            raise HTTPException(status_code=401, detail="Invalid user ID in token")


    def require_auth(request: Request) -> int:
        return get_current_user_from_cookie(request)

    def get_current_user(token: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
        if not token:
            raise HTTPException(status_code=401, detail="Not authenticated")
        try:
            payload = jwt.decode(
                token.credentials, 
                settings.SECRET_KEY, 
                algorithms=[settings.ALGORITHM]
            )
            user_id = payload.get("sub")
            if user_id is None:
                raise HTTPException(status_code=401, detail="Invalid token")
            return int(user_id)
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")
        except ValueError:
            raise HTTPException(status_code=401, detail="Invalid user ID in token")


    def send_reset_email(email: str, token: str) -> None:
        # TODO: Implement with your email provider (SendGrid, AWS SES, etc.)
        pass
