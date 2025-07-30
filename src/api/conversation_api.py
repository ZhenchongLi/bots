from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from src.database.connection import get_db_session
from src.database.conversation_repository import ConversationRepository


router = APIRouter(prefix="/conversations", tags=["conversations"])


# Pydantic models for request/response
class MessageCreate(BaseModel):
    role: str  # 'user', 'assistant', 'system'
    content: str
    model_name: Optional[str] = None
    token_count: Optional[int] = None


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    model_name: Optional[str] = None
    token_count: Optional[int] = None
    timestamp: datetime

    class Config:
        from_attributes = True


class ConversationCreate(BaseModel):
    user_identifier: str
    title: Optional[str] = None
    session_id: Optional[str] = None


class ConversationResponse(BaseModel):
    id: int
    session_id: str
    title: Optional[str] = None
    user_identifier: str
    created_at: datetime
    updated_at: datetime
    messages: Optional[List[MessageResponse]] = []

    class Config:
        from_attributes = True


class ConversationUpdate(BaseModel):
    title: str


@router.post("/", response_model=ConversationResponse)
async def create_conversation(
    conversation_data: ConversationCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """创建新的会话"""
    repo = ConversationRepository(db)
    conversation = await repo.create_conversation(
        user_identifier=conversation_data.user_identifier,
        title=conversation_data.title,
        session_id=conversation_data.session_id
    )
    return conversation


@router.get("/user/{user_identifier}", response_model=List[ConversationResponse])
async def get_user_conversations(
    user_identifier: str,
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db_session)
):
    """获取用户的所有会话"""
    repo = ConversationRepository(db)
    conversations = await repo.get_conversations_by_user(
        user_identifier=user_identifier,
        limit=limit,
        offset=offset
    )
    return conversations


@router.get("/{session_id}", response_model=ConversationResponse)
async def get_conversation(
    session_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """获取特定会话及其消息"""
    repo = ConversationRepository(db)
    conversation = await repo.get_conversation_with_messages(session_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.post("/{session_id}/messages", response_model=MessageResponse)
async def add_message(
    session_id: str,
    message_data: MessageCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """向会话添加消息"""
    repo = ConversationRepository(db)
    
    # 检查会话是否存在
    conversation = await repo.get_conversation_by_session_id(session_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    message = await repo.add_message(
        conversation_id=conversation.id,
        role=message_data.role,
        content=message_data.content,
        model_name=message_data.model_name,
        token_count=message_data.token_count
    )
    return message


@router.get("/{session_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    session_id: str,
    limit: Optional[int] = Query(None, le=1000),
    db: AsyncSession = Depends(get_db_session)
):
    """获取会话的所有消息"""
    repo = ConversationRepository(db)
    
    # 检查会话是否存在
    conversation = await repo.get_conversation_by_session_id(session_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    messages = await repo.get_conversation_messages(
        conversation_id=conversation.id,
        limit=limit
    )
    return messages


@router.put("/{session_id}", response_model=ConversationResponse)
async def update_conversation(
    session_id: str,
    update_data: ConversationUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """更新会话标题"""
    repo = ConversationRepository(db)
    conversation = await repo.update_conversation_title(session_id, update_data.title)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.delete("/{session_id}")
async def delete_conversation(
    session_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """删除会话"""
    repo = ConversationRepository(db)
    success = await repo.delete_conversation(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"message": "Conversation deleted successfully"}