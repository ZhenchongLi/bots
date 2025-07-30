from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from src.models.conversation import Conversation, ConversationMessage


class ConversationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_conversation(
        self,
        user_identifier: str,
        title: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Conversation:
        if not session_id:
            session_id = str(uuid.uuid4())
        
        conversation = Conversation(
            session_id=session_id,
            title=title or f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            user_identifier=user_identifier
        )
        
        self.session.add(conversation)
        await self.session.commit()
        await self.session.refresh(conversation)
        return conversation

    async def get_conversation_by_session_id(self, session_id: str) -> Optional[Conversation]:
        result = await self.session.execute(
            select(Conversation).where(Conversation.session_id == session_id)
        )
        return result.scalar_one_or_none()

    async def get_conversations_by_user(
        self, 
        user_identifier: str, 
        limit: int = 50, 
        offset: int = 0
    ) -> List[Conversation]:
        query = select(Conversation).where(
            Conversation.user_identifier == user_identifier
        ).order_by(desc(Conversation.updated_at)).limit(limit).offset(offset)
        
        result = await self.session.execute(query)
        return result.scalars().all()

    async def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        model_name: Optional[str] = None,
        token_count: Optional[int] = None
    ) -> ConversationMessage:
        message = ConversationMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            model_name=model_name,
            token_count=token_count
        )
        
        self.session.add(message)
        
        # Update conversation's updated_at timestamp
        conversation = await self.session.get(Conversation, conversation_id)
        if conversation:
            conversation.updated_at = datetime.now()
        
        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def get_conversation_messages(
        self, 
        conversation_id: int, 
        limit: Optional[int] = None
    ) -> List[ConversationMessage]:
        query = select(ConversationMessage).where(
            ConversationMessage.conversation_id == conversation_id
        ).order_by(ConversationMessage.timestamp)
        
        if limit:
            query = query.limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_conversation_with_messages(self, session_id: str) -> Optional[Conversation]:
        result = await self.session.execute(
            select(Conversation).where(Conversation.session_id == session_id)
        )
        conversation = result.scalar_one_or_none()
        
        if conversation:
            # Explicitly load messages
            messages_result = await self.session.execute(
                select(ConversationMessage).where(
                    ConversationMessage.conversation_id == conversation.id
                ).order_by(ConversationMessage.timestamp)
            )
            conversation.messages = messages_result.scalars().all()
        
        return conversation

    async def update_conversation_title(self, session_id: str, title: str) -> Optional[Conversation]:
        conversation = await self.get_conversation_by_session_id(session_id)
        if conversation:
            conversation.title = title
            conversation.updated_at = datetime.now()
            await self.session.commit()
            await self.session.refresh(conversation)
        return conversation

    async def delete_conversation(self, session_id: str) -> bool:
        conversation = await self.get_conversation_by_session_id(session_id)
        if conversation:
            await self.session.delete(conversation)
            await self.session.commit()
            return True
        return False