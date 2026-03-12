from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import auth, recipes


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (Alembic handles this in prod; kept for dev convenience)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="Recipe Manager API",
    description="Manage your favourite recipes with filtering, auth, and more.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(recipes.router, prefix=API_PREFIX)


@app.get("/health", tags=["Health"])
async def health() -> dict:
    return {"status": "ok"}
