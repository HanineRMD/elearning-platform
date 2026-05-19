from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routes.courses import router as courses_router

app = FastAPI(title="Course Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(courses_router, prefix="/api/courses", tags=["courses"])

@app.get("/health")
def health():
    return {"status": "OK", "service": "course-service"}