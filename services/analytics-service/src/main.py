from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.database import engine, Base
from src.routes.analytics import router as analytics_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Analytics Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analytics_router, prefix="/api/analytics", tags=["analytics"])

@app.get("/health")
def health():
    return {"status": "OK", "service": "analytics-service"}