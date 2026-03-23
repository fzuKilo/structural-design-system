"""
Minimal FastAPI Application for testing frontend
Excludes design task routes that depend on PlanningFlow
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.config import settings
from backend.api.routes import auth, file, websocket
from backend.database import Base, engine

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.API_TITLE + " (Minimal)",
    version=settings.API_VERSION
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers (excluding design routes)
app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(file.router, prefix=settings.API_PREFIX)
app.include_router(websocket.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "OpenManus Structural Design API (Minimal)", "version": settings.API_VERSION}


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy"}
