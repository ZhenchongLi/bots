from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from contextlib import asynccontextmanager

from src.config.settings import settings
from src.api.proxy import router as proxy_router
from src.api.openai_api import router as openai_router
from src.api.auth_api import router as auth_router
from src.api.conversation_api import router as conversation_router
from src.log_config.middleware import LoggingMiddleware
from src.log_config.config import configure_logging
from src.api.responses import ORJSONResponse
from src.database.connection import init_db
from src.auth.client_auth import api_key_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    configure_logging()
    await init_db()
    
    # Display startup information
    print("\n" + "="*50)
    print("🤖 OfficeAI API Proxy Server Starting")
    print("="*50)
    
    if settings.enable_client_auth:
        default_admin_key = api_key_manager.get_default_admin_key()
        print(f"🔑 Default Admin API Key: {default_admin_key}")
        print("📝 Use this key for initial setup and to create additional API keys")
        print("⚠️  Remember to create new admin keys and revoke this default key in production!")
    else:
        print("⚠️  Client authentication is DISABLED")
    
    print(f"🌐 Server will start on http://{settings.host}:{settings.port}")
    print(f"📚 API Documentation: http://{settings.host}:{settings.port}/docs")
    print("="*50 + "\n")
    
    yield
    # Shutdown
    pass


def create_app() -> FastAPI:
    app = FastAPI(
        title="OpenAI API Proxy",
        description="A unified proxy service for OpenAI API requests with logging",
        version="0.1.0",
        lifespan=lifespan,
        default_response_class=ORJSONResponse,
    )

    app.add_middleware(LoggingMiddleware)
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure this properly in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(openai_router)
    app.include_router(auth_router)
    app.include_router(conversation_router)
    app.include_router(proxy_router)

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
        reload=True,
    )