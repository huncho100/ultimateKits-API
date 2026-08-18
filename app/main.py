from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routes.auth import router as auth_router
from app.routes.product import router as products_router


# ==========================================
# Application
# ==========================================

app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API for the Ultimate Kits e-commerce platform.",
    version=settings.APP_VERSION,
)


# ==========================================
# CORS
# ==========================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# Routers
# ==========================================

app.include_router(auth_router)
app.include_router(products_router)


# ==========================================
# Health Check
# ==========================================

@app.get("/")
def root():
    return {
        "message": "Ultimate Kits API is running",
        "status": "success",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
    }