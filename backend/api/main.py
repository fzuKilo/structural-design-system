"""
FastAPI Main Application
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from backend.api.config import settings
from backend.api.routes import auth, design, file, websocket, admin
from backend.api.middleware import get_current_user
from backend.database import Base, engine, User
from backend.database.migrations.run_migration import run_migration


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create database tables and initialize RBAC + default admin on startup
    run_migration()
    yield


app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    lifespan=lifespan,
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
app.include_router(admin.router, prefix=settings.API_PREFIX)
app.include_router(websocket.router)


@app.get("/api/menu/all")
async def get_menu_list(current_user: User = Depends(get_current_user)):
    """返回前端菜单列表"""
    menus = [
        {
            "id": 1,
            "component": "/dashboard/workspace/index",
            "type": "menu",
            "status": 1,
            "meta": {"icon": "carbon:workspace", "order": 0, "title": "page.dashboard.workspace", "affixTab": True},
            "name": "Workspace",
            "path": "/workspace",
        },
        {
            "id": 2,
            "component": "structural/index",
            "type": "menu",
            "status": 1,
            "meta": {"icon": "carbon:construction", "order": 1, "title": "我的设计"},
            "name": "StructuralDesign",
            "path": "/structural",
        },
        {
            "id": 3,
            "component": "_core/about/index",
            "type": "menu",
            "status": 1,
            "meta": {"icon": "lucide:copyright", "order": 9999, "title": "关于系统"},
            "name": "About",
            "path": "/about",
        },
    ]
    return {"code": 0, "data": menus}


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "OpenManus Structural Design API", "version": settings.API_VERSION}


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy"}
