import pytest
from unittest.mock import patch
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from src.models.client import Client
from src.models.request_log import Base
from src.database.connection import init_default_client


class TestClientModel:
    """Test Client database model functionality."""
    
    @pytest.fixture
    async def async_session(self):
        """Create an async database session for testing."""
        # Use in-memory SQLite for testing
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Create session factory
        AsyncSessionLocal = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        async with AsyncSessionLocal() as session:
            yield session
        
        await engine.dispose()
    
    @pytest.mark.asyncio
    async def test_create_client(self, async_session):
        """Test creating a new client."""
        client = Client(
            name="test_client",
            api_key="test-api-key-123",
            description="Test client",
            is_active=True,
            is_default=False
        )
        
        async_session.add(client)
        await async_session.commit()
        
        # Verify client was created
        result = await async_session.execute(
            select(Client).where(Client.name == "test_client")
        )
        saved_client = result.scalar_one()
        
        assert saved_client.name == "test_client"
        assert saved_client.api_key == "test-api-key-123"
        assert saved_client.description == "Test client"
        assert saved_client.is_active is True
        assert saved_client.is_default is False
        assert saved_client.created_at is not None
        assert saved_client.updated_at is not None
    
    @pytest.mark.asyncio
    async def test_client_unique_constraints(self, async_session):
        """Test that client name and api_key are unique."""
        # Create first client
        client1 = Client(
            name="unique_client",
            api_key="unique-api-key",
            is_active=True
        )
        async_session.add(client1)
        await async_session.commit()
        
        # Try to create client with same name
        client2 = Client(
            name="unique_client",
            api_key="different-api-key",
            is_active=True
        )
        async_session.add(client2)
        
        with pytest.raises(Exception):  # Should raise integrity error
            await async_session.commit()
        
        await async_session.rollback()
        
        # Try to create client with same API key
        client3 = Client(
            name="different_client",
            api_key="unique-api-key",
            is_active=True
        )
        async_session.add(client3)
        
        with pytest.raises(Exception):  # Should raise integrity error
            await async_session.commit()
    
    @pytest.mark.asyncio
    async def test_find_default_client(self, async_session):
        """Test finding the default client."""
        # Create regular client
        regular_client = Client(
            name="regular_client",
            api_key="regular-key",
            is_active=True,
            is_default=False
        )
        async_session.add(regular_client)
        
        # Create default client
        default_client = Client(
            name="default_client",
            api_key="default-key",
            is_active=True,
            is_default=True
        )
        async_session.add(default_client)
        await async_session.commit()
        
        # Find default client
        result = await async_session.execute(
            select(Client).where(Client.is_default == True)
        )
        found_default = result.scalar_one()
        
        assert found_default.name == "default_client"
        assert found_default.is_default is True
    
    @pytest.mark.asyncio
    async def test_client_soft_delete(self, async_session):
        """Test client soft delete by deactivating."""
        client = Client(
            name="to_deactivate",
            api_key="deactivate-key",
            is_active=True
        )
        async_session.add(client)
        await async_session.commit()
        
        # Deactivate client
        client.is_active = False
        await async_session.commit()
        
        # Verify client is deactivated
        result = await async_session.execute(
            select(Client).where(Client.name == "to_deactivate")
        )
        deactivated_client = result.scalar_one()
        
        assert deactivated_client.is_active is False


class TestInitDefaultClient:
    """Test default client initialization functionality."""
    
    @pytest.fixture
    async def memory_engine(self):
        """Create an in-memory database engine for testing."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        yield engine
        await engine.dispose()
    
    @pytest.mark.asyncio
    async def test_init_default_client_creates_when_none_exists(self, memory_engine):
        """Test that init_default_client creates a client when none exists."""
        # Mock the database connection to use our test engine
        AsyncSessionLocal = sessionmaker(
            memory_engine, class_=AsyncSession, expire_on_commit=False
        )
        
        with patch('src.database.connection.AsyncSessionLocal', AsyncSessionLocal):
            # Call init_default_client
            await init_default_client()
            
            # Verify default client was created
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(Client).where(Client.is_default == True)
                )
                default_client = result.scalar_one()
                
                assert default_client.name == "default_client"
                assert default_client.api_key.startswith("default-")
                assert default_client.is_default is True
                assert default_client.is_active is True
                assert default_client.description == "Default client created at startup"
    
    @pytest.mark.asyncio
    async def test_init_default_client_skips_when_exists(self, memory_engine):
        """Test that init_default_client doesn't create duplicate when one exists."""
        AsyncSessionLocal = sessionmaker(
            memory_engine, class_=AsyncSession, expire_on_commit=False
        )
        
        # Create existing default client
        async with AsyncSessionLocal() as session:
            existing_client = Client(
                name="existing_default",
                api_key="existing-key-123",
                is_default=True,
                is_active=True
            )
            session.add(existing_client)
            await session.commit()
        
        with patch('src.database.connection.AsyncSessionLocal', AsyncSessionLocal):
            # Call init_default_client
            await init_default_client()
            
            # Verify no duplicate was created
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(Client).where(Client.is_default == True)
                )
                default_clients = result.scalars().all()
                
                assert len(default_clients) == 1
                assert default_clients[0].name == "existing_default"
                assert default_clients[0].api_key == "existing-key-123"