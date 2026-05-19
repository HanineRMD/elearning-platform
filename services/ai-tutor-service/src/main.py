from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routes.tutor import router as tutor_router

app = FastAPI(title="AI Tutor Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tutor_router, prefix="/api/ai", tags=["ai-tutor"])

@app.get("/health")
def health():
    return {"status": "OK", "service": "ai-tutor-service"}