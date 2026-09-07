from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routers import (
    auth_router, device_router, return_router,
    review_router, task_router, dashboard_router, audit_router
)
from app.services.rule_engine import seed_rules_if_empty
from app.database import SessionLocal

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
