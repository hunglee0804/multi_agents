from sqlalchemy.orm import Session
from app.models.conversation import Conversation
from app.models.message import Message
import uuid

def get_conversations(db: Session, user_id: str, skip: int = 0, limit: int = 50):
    """Get a list of conversations for the Sidebar, filter by user_id"""
    return db.query(Conversation).filter(Conversation.user_id == user_id).order_by(Conversation.created_at.desc()).offset(skip).limit(limit).all()

def get_conversation_with_messages(db: Session, conversation_id: str, user_id: str):
    """Extract details of a conversation (including messages), and verify the correct user_id."""
    return db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.user_id == user_id).first()

def create_or_get_conversation(db: Session, user_id: str, conversation_id: str = None, title: str = "New Conversation"):
    """Create a new conversation or retrieve the current user's existing conversation."""
    if not conversation_id:
        conversation_id = f"SESSION_{uuid.uuid4().hex[:6].upper()}"
        
    conv = db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.user_id == user_id).first()
    if not conv:
        # Nhớ lưu user_id khi tạo mới
        conv = Conversation(id=conversation_id, title=title, user_id=user_id)
        db.add(conv)
        db.commit()
        db.refresh(conv)
    return conv

def save_message(db: Session, conversation_id: str, role: str, content: str):
    """Save one message to the database."""
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message

def delete_conversation(db: Session, conversation_id: str, user_id: str):
    """Delete a conversation and all the messages within it."""
    conv = db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.user_id == user_id).first()
    if conv:
        db.delete(conv)
        db.commit()
        return True
    return False