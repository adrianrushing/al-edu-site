from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import create_pool
from app.routes.data import router as data_router
from app.routes.health import router as health_router
from app.routes.metadata import router as metadata_router
from app.routes.predict import router as predict_router
from app.routes.rankings import router as rankings_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = create_pool()
    app.state.db_pool = pool
    try:
        yield
    finally:
        pool.close()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(metadata_router)
app.include_router(data_router)
app.include_router(predict_router)
app.include_router(rankings_router)
