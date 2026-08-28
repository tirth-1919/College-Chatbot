import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.app.config import settings
from backend.app.database import engine, Base
from backend.app.api.auth_routes import router as auth_router
from backend.app.api.chat_routes import router as chat_router
from backend.app.api.academic_routes import router as academic_router
from backend.app.api.visual_routes import router as visual_router
from backend.app.api.knowledge_routes import router as knowledge_router
from backend.app.api.admin_routes import router as admin_router
from database.seed.seed_data import seed_database

# Create database tables and auto-seed if needed
Base.metadata.create_all(bind=engine)
seed_database()

app = FastAPI(
    title=settings.APP_NAME,
    description="Production-Grade AI Assistant for Ahmedabad Institute of Technology (AIT) — 3-Tier Source Authority, Visual Retrieval, Voice AI, Admin Truth Layer & RAG",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all for local dev & production preview
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers under both root (/api) and versioned prefix (/api/v1) for flexible standard compliance
api_prefix = settings.API_V1_STR
app.include_router(auth_router, prefix=api_prefix)
app.include_router(chat_router, prefix=api_prefix)
app.include_router(academic_router, prefix=api_prefix)
app.include_router(visual_router, prefix=api_prefix)
app.include_router(knowledge_router, prefix=api_prefix)
app.include_router(admin_router, prefix=api_prefix)

# Direct /api prefix aliases
app.include_router(auth_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(academic_router, prefix="/api")
app.include_router(visual_router, prefix="/api")
app.include_router(knowledge_router, prefix="/api")
app.include_router(admin_router, prefix="/api")

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "database": "connected",
        "official_source": settings.AIT_OFFICIAL_URL,
        "environment": settings.ENVIRONMENT
    }

@app.get("/")
def root():
    return {
        "message": f"Welcome to {settings.APP_NAME} API",
        "portal_url": settings.AIT_OFFICIAL_URL,
        "docs": "/docs"
    }
