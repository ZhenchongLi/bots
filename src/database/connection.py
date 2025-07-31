from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.config.settings import settings
from src.models.request_log import Base
from src.models.conversation import Conversation, ConversationMessage
from src.models.client import Client
from sqlalchemy import select
import os
import uuid
import hashlib
import time


# Create database directory if it doesn't exist
os.makedirs(os.path.dirname("./data/proxy.db"), exist_ok=True)

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=False,  # Set to True for SQL debugging
)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Initialize default client after tables are created
    await init_default_client()


async def init_default_client():
    """Check if default_client exists, create if not."""
    async with AsyncSessionLocal() as session:
        # Check if a default client already exists
        result = await session.execute(
            select(Client).where(Client.is_default == True)
        )
        existing_default = result.scalar_one_or_none()
        
        if existing_default is None:
            # Generate API key for default client
            key_suffix = hashlib.sha256(
                f"{uuid.uuid4()}{time.time()}".encode()
            ).hexdigest()[:32]
            api_key = f"default-{key_suffix}"
            
            # Create default client
            default_client = Client(
                name="default_client",
                api_key=api_key,
                description="Default client created at startup",
                is_active=True,
                is_default=True
            )
            
            session.add(default_client)
            await session.commit()
            
            print(f"✅ Created default_client with API key: {api_key}")
        else:
            print(f"✅ Default client already exists: {existing_default.name}")


async def get_db_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()