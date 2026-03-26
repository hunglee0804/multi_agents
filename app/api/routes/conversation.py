from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.api.dependencies import get_current_user
from app.models.user import User

from app.core.database import get_db
from app.services import conversation_service, cache_service
from app.services.ai_service import process_user_message
from app.schemas.conversation import (
    ChatRequest, 
    ChatResponse, 
    ConversationListResponse, 
    ConversationDetailResponse
)

router = APIRouter()

# --- KEYS QUY ƯỚC CHO REDIS (Đã gắn thêm user_id để bảo mật) ---
# List: "conversations_list:{user_id}:{skip}:{limit}"
# Detail: "conversation_detail:{user_id}:{conversation_id}"

@router.post("/backend-api/f/conversation", response_model=ChatResponse)
def chat_with_agent(
    payload: ChatRequest, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Gửi tin nhắn, lưu DB, gọi AI và XÓA CACHE (Cache Invalidation)"""
    
    # 1. Xử lý tạo title và get/create Conversation (Đã sửa lỗi logic ở đây)
    title = payload.message[:30] + "..." if len(payload.message) > 30 else payload.message
    conv = conversation_service.create_or_get_conversation(db, current_user.id, payload.conversation_id, title=title)
    
    # 2. Lưu tin nhắn của user vào DB
    conversation_service.save_message(db, conv.id, role="user", content=payload.message)
    
    # 3. Gọi AI xử lý
    try:
        ai_result = process_user_message(conv.id, payload.message)
        ai_response_text = ai_result.get("response", "Error: No response from AI.")
    except Exception as e:
        ai_response_text = f"The system encountered an internal error: {str(e)}"

    # 4. Lưu tin nhắn của Assistant vào DB
    conversation_service.save_message(db, conv.id, role="assistant", content=ai_response_text)
    
    # ---------------------------------------------------------
    # CACHE INVALIDATION: Có dữ liệu mới, cần xóa cache cũ của chính user này đi
    # 1. Xóa cache của chi tiết hội thoại này
    cache_service.delete_cache(f"conversation_detail:{current_user.id}:{conv.id}")
    # 2. Xóa toàn bộ cache list của user này
    cache_service.delete_keys_by_pattern(f"conversations_list:{current_user.id}:*")
    # ---------------------------------------------------------

    return ChatResponse(conversation_id=conv.id, response=ai_response_text)


@router.get("/backend-api/conversations", response_model=List[ConversationListResponse])
def get_conversations(
    skip: int = 0, 
    limit: int = 20, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Tải danh sách chat (Sử dụng Cache-Aside)"""
    
    cache_key = f"conversations_list:{current_user.id}:{skip}:{limit}"
    
    # 1. Kiểm tra Cache
    cached_list = cache_service.get_cache(cache_key)
    if cached_list:
        print(f"⚡ [CACHE HIT] Returns a list from Redis ({cache_key})")
        return cached_list

    # 2. Nếu Cache Miss, gọi DB
    print(f"🐌 [CACHE MISS] Query the database for ({cache_key})")
    # Truyền thêm current_user.id vào service
    convs = conversation_service.get_conversations(db, current_user.id, skip=skip, limit=limit)
    
    # Chuyển đổi object DB sang dạng Dict để lưu vào Redis
    result_data = [
        {"id": c.id, "title": c.title, "created_at": c.created_at.isoformat()} 
        for c in convs
    ]
    
    # 3. Lưu vào Cache cho các lần gọi sau
    cache_service.set_cache(cache_key, result_data)
    
    return result_data


@router.get("/backend-api/conversation/{conversation_id}", response_model=ConversationDetailResponse)
def get_conversation_detail(
    conversation_id: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Tải chi tiết lịch sử tin nhắn (Sử dụng Cache-Aside)"""
    
    cache_key = f"conversation_detail:{current_user.id}:{conversation_id}"
    
    # 1. Kiểm tra Cache
    cached_detail = cache_service.get_cache(cache_key)
    if cached_detail:
        print(f"⚡ [CACHE HIT] Return details from Redis ({cache_key})")
        return cached_detail

    # 2. Nếu Cache Miss, gọi DB
    print(f"🐌 [CACHE MISS] Query the database for ({cache_key})")
    # Truyền thêm current_user.id vào service để tránh user này xem lén tin nhắn user khác
    conv = conversation_service.get_conversation_with_messages(db, conversation_id, current_user.id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found or you don't have permission")
    
    # Chuyển đổi sang Dict
    result_data = {
        "id": conv.id,
        "title": conv.title,
        "messages": [{"role": m.role, "content": m.content} for m in conv.messages]
    }
    
    # 3. Lưu vào Cache
    cache_service.set_cache(cache_key, result_data)
    
    return result_data

@router.delete("/backend-api/conversation/{conversation_id}")
def delete_conversation(
    conversation_id: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """API để xóa cuộc hội thoại"""
    success = conversation_service.delete_conversation(db, conversation_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found or access denied")

    # XÓA CACHE: Để Sidebar tải lại danh sách mới
    cache_service.delete_cache(f"conversation_detail:{current_user.id}:{conversation_id}")
    cache_service.delete_keys_by_pattern(f"conversations_list:{current_user.id}:*")

    return {"message": "Deleted successfully"}