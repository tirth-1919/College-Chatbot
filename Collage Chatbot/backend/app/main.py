import os
import secrets
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from backend.app.config import settings
from backend.app.database import engine, Base
from backend.app.api.auth_routes import router as auth_router
from backend.app.api.chat_routes import router as chat_router
from backend.app.api.academic_routes import router as academic_router
from backend.app.api.visual_routes import router as visual_router
from backend.app.api.knowledge_routes import router as knowledge_router
from backend.app.api.admin_routes import router as admin_router
from backend.app.api.whatsapp_routes import router as whatsapp_router
from backend.app.api.metrics_routes import router as metrics_router
from backend.app.api.security_routes import router as security_router
from backend.app.api.enhanced_auth_routes import router as enhanced_auth_router
from backend.app.api.enhanced_services_routes import router as enhanced_services_router
from backend.app.api.admin_enhanced_routes import router as admin_enhanced_router
from backend.app.security.csrf import CSRFMiddleware
from database.seed.seed_data import seed_database

# Create database tables and auto-seed if needed
Base.metadata.create_all(bind=engine)
seed_database()

# Rate Limiter Setup
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title=settings.APP_NAME,
    description="Production-Grade AI Assistant for Ahmedabad Institute of Technology (AIT) — 3-Tier Source Authority, Visual Retrieval, Voice AI, Admin Truth Layer & RAG",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security Headers Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; img-src 'self' data: https: https://www.aitindia.in; font-src 'self' data: https://fonts.gstatic.com; connect-src 'self' https://www.aitindia.in https://generativelanguage.googleapis.com;"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=()"
        return response

# Add security middleware
app.add_middleware(SecurityHeadersMiddleware)

# Add CSRF protection middleware
csrf_secret = os.getenv("CSRF_SECRET_KEY", secrets.token_urlsafe(32))
app.add_middleware(CSRFMiddleware, secret_key=csrf_secret)

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
app.include_router(whatsapp_router, prefix=api_prefix)
app.include_router(security_router, prefix=api_prefix)
app.include_router(enhanced_auth_router, prefix=api_prefix)
app.include_router(enhanced_services_router, prefix=api_prefix)
app.include_router(admin_enhanced_router, prefix=api_prefix)

# Direct /api prefix aliases
app.include_router(auth_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(academic_router, prefix="/api")
app.include_router(visual_router, prefix="/api")
app.include_router(knowledge_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(whatsapp_router, prefix="/api")
app.include_router(security_router, prefix="/api")
app.include_router(enhanced_auth_router, prefix="/api")
app.include_router(enhanced_services_router, prefix="/api")
app.include_router(admin_enhanced_router, prefix="/api")

# Prometheus & System Metrics Endpoints
app.include_router(metrics_router)
app.include_router(metrics_router, prefix="/api")
app.include_router(metrics_router, prefix=api_prefix)

@app.on_event("startup")
async def startup_background_tasks():
    """Initializes background synchronization, model artifact warmup & schedulers safely without blocking startup"""
    try:
        from rag.schedulers.website_sync_scheduler import WebsiteSyncScheduler
        from backend.app.database import SessionLocal
        from ml.intent.intent_classifier import IntentClassifier

        db = SessionLocal()
        try:
            # Initialize / warm up ML Intent Classifier from active database record / artifact
            classifier = IntentClassifier(use_ml=True, db=db)
            app.state.intent_classifier = classifier
            print(f"[AIT Server] Active Intent Classifier initialized (Version: {classifier.model_version}, Trained: {classifier.is_trained})")
        except Exception as ml_err:
            print(f"[AIT Server] Note on Intent Classifier startup warmup: {ml_err}. Fallback rule-based matcher active.")

        scheduler = WebsiteSyncScheduler(
            sync_interval_hours=getattr(settings, "KNOWLEDGE_SYNC_INTERVAL_HOURS", 24),
            enable_change_detection=getattr(settings, "KNOWLEDGE_SYNC_ENABLED", True)
        )
        scheduler.set_db_session(db)
        scheduler.start()
        app.state.scheduler = scheduler
    except Exception as e:
        print(f"[AIT Server] Note on background sync scheduler startup: {e}")


# ----------------- Static Frontend & SPA Serving Configuration -----------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"
FRONTEND_ASSETS = FRONTEND_DIST / "assets"
PUBLIC_ASSETS = BASE_DIR / "frontend" / "public" / "assets"

# Mount frontend built assets if available
if FRONTEND_ASSETS.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_ASSETS)), name="assets")
elif PUBLIC_ASSETS.exists():
    app.mount("/assets", StaticFiles(directory=str(PUBLIC_ASSETS)), name="public_assets")

@app.get("/health")
@limiter.limit("100/minute")
def health_check(request: Request):
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "database": "connected",
        "official_source": settings.AIT_OFFICIAL_URL,
        "environment": settings.ENVIRONMENT
    }

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    favicon_dist = FRONTEND_DIST / "favicon.ico"
    if favicon_dist.exists():
        return FileResponse(str(favicon_dist))
    return Response(status_code=204)

@app.get("/")
@limiter.limit("100/minute")
def serve_root(request: Request):
    index_path = FRONTEND_DIST / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {
        "message": f"Welcome to {settings.APP_NAME} Unified API & Web Server",
        "status": "backend_online",
        "frontend_note": "Frontend dist build not found. Run 'npm run build' in frontend directory.",
        "portal_url": settings.AIT_OFFICIAL_URL,
        "docs": "/docs"
    }

# SPA Fallback Catch-all for client-side routing (/chat, /academic, /study, /gallery, /admin, /login, etc.)
@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str, request: Request):
    # Never intercept backend APIs, docs, health, metrics or openapi
    if full_path.startswith(("api", "health", "metrics", "docs", "redoc", "openapi.json")):
        raise HTTPException(status_code=404, detail=f"API route /{full_path} not found")

    # Check if a static file directly in dist exists (e.g. vite.svg, robots.txt)
    static_file = FRONTEND_DIST / full_path
    if static_file.is_file() and static_file.exists():
        return FileResponse(str(static_file))

    # Return index.html for React SPA client-side routes
    index_path = FRONTEND_DIST / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))

    raise HTTPException(status_code=404, detail="Resource not found")

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "message": str(exc)}
    )
