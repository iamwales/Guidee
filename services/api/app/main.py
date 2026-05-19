from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import agent, auth, billing, chat, user


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Guidee API",
        description="Backend for Guidee desktop AI assistant",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(chat.router)
    app.include_router(agent.router)
    app.include_router(auth.router)
    app.include_router(user.router)
    app.include_router(billing.router)

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "guidee-api"}

    return app


app = create_app()
