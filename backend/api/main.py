"""
FastAPI Main Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.config import settings
from backend.api.routes import auth, design, file, websocket
from backend.database import Base, engine

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.API_TITLE,
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

# Include routers
app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(design.router, prefix=settings.API_PREFIX)
app.include_router(file.router, prefix=settings.API_PREFIX)
app.include_router(websocket.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "OpenManus Structural Design API", "version": settings.API_VERSION}


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy"}
