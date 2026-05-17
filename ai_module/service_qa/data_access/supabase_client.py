from supabase import create_client, Client
from config.config import settings
from typing import Dict, Any, Optional, List
import jwt
import logging
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

class SupabaseDB:
    def __init__(self):
        # Dùng service_role key để bypass RLS trên backend
        key = settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY
        self.supabase: Client = create_client(settings.SUPABASE_URL, key)
    def verify_jwt_token(self, token: str) -> dict:
        """Xác thực JWT token từ Supabase Auth. Trả về payload nếu hợp lệ, nếu không raise HTTPException."""
        try:
            # Giải mã token mà không cần xác minh audience (có thể tùy chỉnh)
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_aud": False}
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    def save_document_metadata(self, file_name: str, file_url: str, extracted_content: str, project_id: str, user_id: str) -> Optional[str]:
        """Lưu thông tin file PDF vào bảng documents và trả về document_id"""
        try:
            result = self.supabase.table("documents").insert({
                "file_name": file_name,
                "file_url": file_url,
                "extracted_content": extracted_content,
                "project_id": project_id,
                "user_id": user_id,
                "status": "processing",
            }).execute()

            if result.data and len(result.data) > 0:
                return result.data[0]["id"]
            return None
        except Exception as e:
            logger.error(f"Lỗi khi lưu Document: {e}")
            raise

    def update_document_status(self, document_id: str, new_status: str):
        """Cập nhật trạng thái xử lý tài liệu"""
        try:
            self.supabase.table("documents").update({"status": new_status}).eq("id", document_id).execute()
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật status: {e}")

    def save_summary(self, document_id: str, summary_type: str, summary_text: str, original_text: str = None, user_id: str = None):
        """Lưu Overview hoặc Detailed summary vào bảng summaries"""
        try:
            self.supabase.table("summaries").insert({
                "document_id": document_id,
                "summary_type": summary_type,
                "summary_text": summary_text,
                "original_text": original_text,
                "user_id": user_id
            }).execute()
        except Exception as e:
            logger.error(f"Lỗi khi lưu Summary: {e}")

    def save_chat_message(self, project_id: str, thread_id: str, user_id: str, content: str, role: str):
        """Lưu lượt chat (user hỏi, AI đáp) vào bảng chat_history"""
        try:
            self.supabase.table("chat_history").insert({
                "project_id": project_id,
                "thread_id": thread_id,
                "user_id": user_id,
                "content": content,
                "role": role
            }).execute()
        except Exception as e:
            logger.error(f"Lỗi khi lưu Chat History: {e}")

    def get_chat_history(self, project_id: str, thread_id: str, limit: int = 5) -> List[dict]:
        """Lấy lịch sử hội thoại gần nhất của một thread"""
        try:
            result = (
                self.supabase.table("chat_history")
                .select("role, content, created_at")
                .eq("project_id", project_id)
                .eq("thread_id", thread_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            # Đảo ngược để lấy thứ tự cũ → mới
            return list(reversed(result.data)) if result.data else []
        except Exception as e:
            logger.error(f"Lỗi khi lấy Chat History: {e}")
            return []

    def upload_file_to_storage(self, file_bytes: bytes, project_id: str, file_name: str) -> str:
        """
        Upload file lên Supabase Storage bucket 'documents'.
        Đường dẫn lưu trữ: {project_id}/{file_name}
        Trả về public URL của file.
        """
        from config.config import settings
        path = f"{project_id}/{file_name}"
        try:
            self.supabase.storage.from_(settings.SUPABASE_STORAGE_BUCKET).upload(
                path=path,
                file=file_bytes,
                file_options={"content-type": "application/pdf", "upsert": "true"}
            )
            return self.supabase.storage.from_(settings.SUPABASE_STORAGE_BUCKET).get_public_url(path)
        except Exception as e:
            logger.error(f"Lỗi khi upload file lên Storage: {e}")
            raise