from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional
from jose import jwt, JWTError
from src.database import get_db
from src.models.analytics import CourseView, EnrollmentEvent, ProgressEvent, Feedback
from dotenv import load_dotenv
import os

load_dotenv()
router = APIRouter()
JWT_SECRET = os.getenv("JWT_SECRET")

def get_current_user(authorization: str = Header(...)):
    try:
        token = authorization.replace("Bearer ", "")
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalide")

class ViewCreate(BaseModel):
    course_id: int

class ProgressCreate(BaseModel):
    course_id: int
    lesson_id: int
    progress: float

class FeedbackCreate(BaseModel):
    course_id: int
    rating: int
    comment: Optional[str] = ""

# ── TRACKING ──────────────────────────────────────────

@router.post("/view")
def track_view(data: ViewCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    view = CourseView(course_id=data.course_id, user_id=user["userId"])
    db.add(view)
    db.commit()
    return {"message": "Vue enregistrée"}

@router.post("/progress")
def track_progress(data: ProgressCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    existing = db.query(ProgressEvent).filter(
        ProgressEvent.user_id == user["userId"],
        ProgressEvent.lesson_id == data.lesson_id
    ).first()
    if existing:
        existing.progress = data.progress
    else:
        db.add(ProgressEvent(
            course_id=data.course_id,
            user_id=user["userId"],
            lesson_id=data.lesson_id,
            progress=data.progress
        ))
    db.commit()
    return {"message": "Progression enregistrée"}

@router.post("/feedback")
def submit_feedback(data: FeedbackCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    # Vérifie si déjà noté
    existing = db.query(Feedback).filter(
        Feedback.user_id == user["userId"],
        Feedback.course_id == data.course_id
    ).first()
    if existing:
        existing.rating = data.rating
        existing.comment = data.comment
        db.commit()
        return {"message": "Feedback mis à jour"}
    feedback = Feedback(
        course_id=data.course_id,
        user_id=user["userId"],
        rating=data.rating,
        comment=data.comment
    )
    db.add(feedback)
    db.commit()
    return {"message": "Feedback envoyé", "feedback_id": feedback.id}

# ── DASHBOARD INSTRUCTEUR ─────────────────────────────

@router.get("/dashboard")
def get_dashboard(db: Session = Depends(get_db), user=Depends(get_current_user)):
    if user["role"] not in ["instructor", "admin"]:
        raise HTTPException(status_code=403, detail="Accès refusé")

    total_views       = db.query(func.count(CourseView.id)).scalar() or 0
    total_enrollments = db.query(func.count(EnrollmentEvent.id)).scalar() or 0
    total_feedbacks   = db.query(func.count(Feedback.id)).scalar() or 0
    avg_rating        = db.query(func.avg(Feedback.rating)).scalar() or 0

    top_courses = db.query(
        CourseView.course_id,
        func.count(CourseView.id).label("views")
    ).group_by(CourseView.course_id)\
     .order_by(func.count(CourseView.id).desc())\
     .limit(5).all()

    # Feedbacks récents avec notes
    recent_feedbacks = db.query(Feedback)\
        .order_by(Feedback.created_at.desc())\
        .limit(10).all()

    # Progression moyenne par cours
    avg_progress = db.query(
        ProgressEvent.course_id,
        func.avg(ProgressEvent.progress).label("avg_progress")
    ).group_by(ProgressEvent.course_id).all()

    return {
        "total_views": total_views,
        "total_enrollments": total_enrollments,
        "total_feedbacks": total_feedbacks,
        "average_rating": round(float(avg_rating), 2),
        "top_courses": [
            {"course_id": c.course_id, "views": c.views}
            for c in top_courses
        ],
        "recent_feedbacks": [
            {
                "course_id": f.course_id,
                "user_id": f.user_id,
                "rating": f.rating,
                "comment": f.comment,
                "created_at": f.created_at.isoformat()
            }
            for f in recent_feedbacks
        ],
        "course_progress": [
            {
                "course_id": p.course_id,
                "avg_progress": round(float(p.avg_progress), 1)
            }
            for p in avg_progress
        ]
    }

@router.get("/course/{course_id}/stats")
def get_course_stats(
    course_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """Stats détaillées d'un cours spécifique"""
    views       = db.query(func.count(CourseView.id))\
        .filter(CourseView.course_id == course_id).scalar() or 0
    enrollments = db.query(func.count(EnrollmentEvent.id))\
        .filter(EnrollmentEvent.course_id == course_id).scalar() or 0
    feedbacks   = db.query(Feedback)\
        .filter(Feedback.course_id == course_id).all()
    avg_rating  = sum(f.rating for f in feedbacks) / len(feedbacks) if feedbacks else 0

    return {
        "course_id": course_id,
        "views": views,
        "enrollments": enrollments,
        "avg_rating": round(avg_rating, 2),
        "total_feedbacks": len(feedbacks),
        "feedbacks": [
            {
                "user_id": f.user_id,
                "rating": f.rating,
                "comment": f.comment,
                "created_at": f.created_at.isoformat()
            }
            for f in feedbacks
        ]
    }