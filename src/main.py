from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from contextlib import asynccontextmanager

from src.config.settings import settings
from src.api.proxy import router as proxy_router
from src.api.openai_api import router as openai_router
from src.logging.middleware import LoggingMiddleware
from src.logging.config import configure_logging
from src.database.connection import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    configure_logging()
    await init_db()
    yield
    # Shutdown
    pass


def create_app() -> FastAPI:
    app = FastAPI(
        title="OpenAI API Proxy",
        description="A unified proxy service for OpenAI API requests with logging",
        version="0.1.0",
        lifespan=lifespan,
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