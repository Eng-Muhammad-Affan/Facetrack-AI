import os
import uuid
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from fastapi import UploadFile, HTTPException, status
from supabase import create_client, Client
from urllib.parse import urlparse, unquote
import logging

logger = logging.getLogger(__name__)

class SupabaseBlobUpload:
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 10MB default
    
    def __init__(self):
        load_dotenv()
        
        self.SUPABASE_URL = os.getenv("SUPABASE_URL")
        self.SUPABASE_KEY = os.getenv("SUPABASE_API_KEY")
        self.BUCKET_NAME = os.getenv("SUPABASE_BUCKET_NAME")
        
        if not all([self.SUPABASE_URL, self.SUPABASE_KEY, self.BUCKET_NAME]):
            raise ValueError("Missing Supabase credentials in environment variables.")
        
        self.supabase: Client = create_client(self.SUPABASE_URL, self.SUPABASE_KEY)
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent path traversal and ensure uniqueness."""
        # Remove any path components
        filename = Path(filename).name
        
        # Remove special characters (keep alphanumeric, dots, dashes, underscores)
        import re
        filename = re.sub(r'[^\w\-\.]', '_', filename)
        
        # Ensure uniqueness
        name, ext = os.path.splitext(filename)
        unique_name = f"{name}_{uuid.uuid4().hex}{ext}"
        
        return unique_name
    
    def _validate_file_size(self, file_content: bytes) -> None:
        """Validate file size to prevent memory issues."""
        if len(file_content) > self.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum allowed size of {self.MAX_FILE_SIZE} bytes"
            )
    
    async def upload_file_to_supabase(
        self, 
        file: UploadFile, 
        folder: str = "uploads",
        custom_filename: Optional[str] = None
    ) -> dict:
        """
        Upload file to Supabase storage.
        
        Args:
            file: FastAPI UploadFile object
            folder: Folder path within bucket
            custom_filename: Optional custom filename (will be sanitized)
        
        Returns:
            dict with public_url and file_path
        """
        try:
            # Read file content
            file_content = await file.read()
            
            # Validate file size
            self._validate_file_size(file_content)
            
            # Generate safe filename
            if custom_filename:
                filename = self._sanitize_filename(custom_filename)
            else:
                filename = self._sanitize_filename(file.filename)
            
            # Build file path
            file_path = f"{folder.rstrip('/')}/{filename}" if folder else filename
            
            # Upload file
            response = self.supabase.storage.from_(self.BUCKET_NAME).upload(
                path=file_path,
                file=file_content,
                file_options={
                    "content-type": file.content_type or "application/octet-stream",
                    "upsert": True  # Use boolean, not string
                }
            )
            
            # Generate public URL
            public_url = self.supabase.storage.from_(self.BUCKET_NAME).get_public_url(file_path)
            
            logger.info(f"File uploaded successfully: {file_path}")
            
            return {
                "url": public_url,
                "file_path": file_path,
                "filename": filename,
                "size": len(file_content),
                "content_type": file.content_type
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Upload failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Upload failed: {str(e)}"
            )
    
    def extract_storage_details(self, url: str) -> tuple[str, str]:
        """Parse Supabase public URL to extract bucket name and file path."""
        try:
            parsed_url = urlparse(url)
            path_parts = parsed_url.path.strip("/").split("/")
            
            # Strict validation
            expected_prefix = ['storage', 'v1', 'object', 'public']
            if len(path_parts) < 6 or path_parts[:4] != expected_prefix:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid Supabase public URL structure."
                )
            
            bucket_name = path_parts[4]
            file_path = unquote("/".join(path_parts[5:]))
            
            return bucket_name, file_path
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to parse URL: {str(e)}"
            )
    
    async def delete_file_from_storage(self, public_url: str) -> dict:
        """
        Delete file from Supabase storage.
        
        Returns:
            dict with deletion status
        """
        try:
            bucket_name, file_path = self.extract_storage_details(public_url)
            
            logger.info(f"Attempting to delete: bucket={bucket_name}, path={file_path}")
            
            # Remove file
            response = self.supabase.storage.from_(bucket_name).remove([file_path])
            
            # Check if deletion was successful
            # Supabase returns data with empty list if file doesn't exist
            if hasattr(response, 'data') and response.data:
                deleted_files = response.data
                if not deleted_files:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="File not found or already deleted from the bucket."
                    )
            elif isinstance(response, list) and not response:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="File not found or already deleted from the bucket."
                )
            
            logger.info(f"File deleted successfully: {file_path}")
            
            return {
                "deleted": True,
                "file_path": file_path,
                "bucket": bucket_name
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Delete failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Supabase storage error: {str(e)}"
            )
    
    async def upload_multiple_files(
        self, 
        files: list[UploadFile], 
        folder: str = "uploads"
    ) -> list[dict]:
        """Upload multiple files to Supabase storage."""
        results = []
        errors = []
        
        for file in files:
            try:
                result = await self.upload_file_to_supabase(file, folder)
                results.append(result)
            except HTTPException as e:
                errors.append({
                    "filename": file.filename,
                    "error": e.detail
                })
        
        return {
            "uploaded": results,
            "failed": errors,
            "total_files": len(files),
            "successful_uploads": len(results),
            "failed_uploads": len(errors)
        }