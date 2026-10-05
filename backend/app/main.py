import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.database import engine, Base
from app.routers import (
    auth_router, device_router, return_router,
    review_router, task_router, dashboard_router, audit_router
)
from app.services.rule_engine import seed_rules_if_empty
from app.database import SessionLocal

# Configure clinical operational logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("rural_health_system")

# Initialize database schema tables
Base.metadata.create_all(bind=engine)

# Seed rules on startup
db_session = SessionLocal()
try:
    seed_rules_if_empty(db_session)
finally:
    db_session.close()

app = FastAPI(
    title="Rural Health Loan-Device Return & Reconciliation System",
    description="Field-ready healthcare operational support system for portable medical device return checklist, accessory reconciliation, safety rule engine, and human-in-the-loop decision governance.",
    version="1.0.0"
)

# Centralized Error Boundary Exception Handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Centralized validation error boundary.
    Sanitizes schema errors, prevents malformed requests from corrupting DB state,
    and returns standardized JSON preserving 'detail' for client/test compatibility.
    """
    logger.warning(f"Validation failure on {request.method} {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "error": "Request Schema Validation Error",
            "code": "VALIDATION_ERROR",
            "status_code": 422,
            "path": request.url.path,
        },
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Centralized HTTP exception boundary.
    Formats business exceptions (400, 401, 403, 404, 409, 422) into structured JSON,
    ensuring 'detail' is preserved while adding standardized code and status attributes.
    """
    logger.info(f"HTTP exception {exc.status_code} on {request.method} {request.url.path}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error": exc.detail if isinstance(exc.detail, str) else "HTTP Error",
            "code": f"HTTP_{exc.status_code}",
            "status_code": exc.status_code,
            "path": request.url.path,
        },
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """
    Global catch-all exception boundary.
    Prevents raw tracebacks, internal database errors, and sensitive system details
    from leaking to field staff or external clients in 500 error responses.
    """
    logger.error(f"Unhandled 500 server exception on {request.method} {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal operational error occurred. The diagnostic event has been securely logged.",
            "error": "Internal Server Error",
            "code": "INTERNAL_SERVER_ERROR",
            "status_code": 500,
            "path": request.url.path,
        },
    )

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth_router.router)
app.include_router(device_router.router)
app.include_router(return_router.router)
app.include_router(review_router.router)
app.include_router(task_router.router)
app.include_router(dashboard_router.router)
app.include_router(audit_router.router)

@app.get("/")
def root():
    return {
        "system": "Rural Health Loan-Device Return Checklist & Accessory Reconciliation System",
        "status": "ONLINE",
        "docs": "/docs",
        "version": "1.0.0"
    }
