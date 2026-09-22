import logging

from fastapi import Depends, FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.database import get_db
from app.routes.auth import router as auth_router
from app.routes.product import router as products_router
from app.routes.cart import router as cart_router
from app.routes.orders import router as orders_router
from app.routes.admin import router as admin_router
from app.routes.payment import router as payment_router


logger = logging.getLogger(__name__)



# ==========================================
# Application
# ==========================================

# The interactive docs and the OpenAPI schema enumerate every
# route, parameter and model, which is a map of the attack
# surface. They stay available in development and are turned
# off entirely when DEBUG is False.

app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API for the Ultimate Kits e-commerce platform.",
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
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
def health_check(
    db: Session = Depends(get_db),
):
    """
    Report whether the service can actually serve traffic.

    A health check that only proves the process is running
    will keep an instance in the load balancer long after
    its database has gone away, so every request this
    instance receives fails. The check therefore executes a
    trivial query and answers 503 when it cannot.

    Response shape is unchanged on success apart from an
    added "database" field.
    """

    try:
        db.execute(text("SELECT 1"))

    except SQLAlchemyError:
        logger.exception(
            "Health check failed: database is unreachable."
        )

        return JSONResponse(
            status_code=(
                status.HTTP_503_SERVICE_UNAVAILABLE
            ),
            content={
                "status": "unhealthy",
                "database": "unavailable",
            },
        )

    return {
        "status": "healthy",
        "database": "connected",
    }