from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routes.auth import router as auth_router
from app.routes.product import router as products_router
from app.routes.cart import router as cart_router
from app.routes.orders import router as orders_router
from app.routes.admin import router as admin_router
from app.routes.payment import router as payment_router



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
app.include_router(cart_router)
app.include_router(orders_router)
app.include_router(admin_router)
app.include_router(payment_router)



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