from datetime import datetime
import json

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from jose import jwt, JWTError
from src.database import get_db
from src.models.course import Announcement, Assignment, Certificate, Course, Lesson, Enrollment, Rating, Submission
from dotenv import load_dotenv
import os

load_dotenv()
router = APIRouter()
JWT_SECRET = os.getenv("JWT_SECRET")

# ── Schémas ───────────────────────────────────────────
class CourseCreate(BaseModel):
    title: str
    description: str
    price: float = 0.0
    is_free: bool = False
    category: str

class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    is_free: Optional[bool] = None
    category: Optional[str] = None

class CourseResponse(BaseModel):
    id: int
    title: str
    description: str
    price: float
    is_free: bool
    category: str
    instructor_id: Optional[str] = None
    class Config:
        from_attributes = True

class EnrollRequest(BaseModel):
    course_id: int

class LessonCreate(BaseModel):
    title: str
    content: str
    video_url: Optional[str] = ""
    order: int = 1

class LessonResponse(BaseModel):
    id: int
    title: str
    content: str
    video_url: Optional[str]
    order: int
    course_id: int
    class Config:
        from_attributes = True
class AnnouncementCreate(BaseModel):
    title: str
    content: str

class AnnouncementResponse(BaseModel):
    id: int
    title: str
    content: str
    created_at: str  # ← doit être string
    course_id: int
    
    class Config:
        from_attributes = True
        # Ajoute cette ligne pour convertir automatiquement datetime en string
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
class AssignmentCreate(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: str  # ISO format
    max_score: int = 100

class AssignmentResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    due_date: str
    max_score: int
    course_id: int
    
    class Config:
        from_attributes = True

class SubmissionCreate(BaseModel):
    content: Optional[str] = None
    file_url: Optional[str] = None
class RatingCreate(BaseModel):
    rating: int  # 1-5
    comment: Optional[str] = None

# ── Auth ──────────────────────────────────────────────
def get_current_user(authorization: str = Header(...)):
    try:
        token = authorization.replace("Bearer ", "")
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalide")

def get_current_user_optional(authorization: Optional[str] = Header(None)):
    if not authorization:
        return None
    try:
        token = authorization.replace("Bearer ", "")
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except JWTError:
        return None

# ── COURSES ───────────────────────────────────────────
@router.post("/{course_id}/announcements", response_model=AnnouncementResponse)
def create_announcement(
    course_id: int,
    announcement: AnnouncementCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    # Vérifier que l'instructeur est propriétaire
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.instructor_id == user["userId"]
    ).first()
    if not course:
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    new_announcement = Announcement(
        course_id=course_id,
        title=announcement.title,
        content=announcement.content
    )
    db.add(new_announcement)
    db.commit()
    db.refresh(new_announcement)
    
    # Retourner avec la date convertie en string
    return AnnouncementResponse(
        id=new_announcement.id,
        title=new_announcement.title,
        content=new_announcement.content,
        created_at=new_announcement.created_at.isoformat(),
        course_id=new_announcement.course_id
    )
@router.get("/courses/{course_id}/assignments/student")
def get_student_assignments(
    course_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """Récupère les devoirs d'un cours pour l'étudiant connecté"""
    # Vérifier que l'étudiant est inscrit
    enrollment = db.query(Enrollment).filter(
        Enrollment.user_id == user["userId"],
        Enrollment.course_id == course_id
    ).first()
    if not enrollment:
        raise HTTPException(status_code=403, detail="Vous n'êtes pas inscrit à ce cours")
    
    assignments = db.query(Assignment).filter(
        Assignment.course_id == course_id
    ).order_by(Assignment.due_date).all()
    
    # Récupérer les soumissions de l'étudiant
    submissions = db.query(Submission).filter(
        Submission.user_id == user["userId"],
        Submission.assignment_id.in_([a.id for a in assignments])
    ).all()
    
    return {
        "assignments": assignments,
        "submissions": submissions
    }
@router.get("/courses/{course_id}/enrollment")
def check_enrollment(
    course_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """Vérifie si l'utilisateur est inscrit au cours"""
    enrollment = db.query(Enrollment).filter(
        Enrollment.user_id == user["userId"],
        Enrollment.course_id == course_id
    ).first()
    return {"enrolled": enrollment is not None}
@router.get("/{course_id}/announcements", response_model=List[AnnouncementResponse])
def get_announcements(
    course_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user_optional)
):
    announcements = db.query(Announcement).filter(
        Announcement.course_id == course_id
    ).order_by(Announcement.created_at.desc()).all()
    
    # Convertir les dates en string ISO
    result = []
    for a in announcements:
        result.append(AnnouncementResponse(
            id=a.id,
            title=a.title,
            content=a.content,
            created_at=a.created_at.isoformat(),
            course_id=a.course_id
        ))
    return result
@router.post("/{course_id}/assignments", response_model=AssignmentResponse)
def create_assignment(
    course_id: int,
    assignment: AssignmentCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    from datetime import datetime
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.instructor_id == user["userId"]
    ).first()
    if not course:
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    new_assignment = Assignment(
        course_id=course_id,
        title=assignment.title,
        description=assignment.description,
        due_date=datetime.fromisoformat(assignment.due_date),
        max_score=assignment.max_score
    )
    db.add(new_assignment)
    db.commit()
    db.refresh(new_assignment)
    return new_assignment

@router.get("/{course_id}/assignments", response_model=List[AssignmentResponse])
def get_assignments(course_id: int, db: Session = Depends(get_db)):
    return db.query(Assignment).filter(
        Assignment.course_id == course_id
    ).order_by(Assignment.due_date).all()

@router.post("/assignments/{assignment_id}/submit")
def submit_assignment(
    assignment_id: int,
    submission: SubmissionCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    # Vérifier que l'étudiant est inscrit au cours
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Devoir non trouvé")
    
    enrollment = db.query(Enrollment).filter(
        Enrollment.user_id == user["userId"],
        Enrollment.course_id == assignment.course_id
    ).first()
    if not enrollment:
        raise HTTPException(status_code=403, detail="Vous devez être inscrit au cours")
    
    # Vérifier si déjà soumis
    existing = db.query(Submission).filter(
        Submission.assignment_id == assignment_id,
        Submission.user_id == user["userId"]
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Vous avez déjà soumis ce devoir")
    
    new_submission = Submission(
        assignment_id=assignment_id,
        user_id=user["userId"],
        content=submission.content,
        file_url=submission.file_url
    )
    db.add(new_submission)
    db.commit()
    return {"message": "Devoir soumis avec succès", "submission_id": new_submission.id}
@router.post("/{course_id}/ratings")
def add_rating(
    course_id: int,
    rating_data: RatingCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    # Vérifier que l'étudiant est inscrit
    enrollment = db.query(Enrollment).filter(
        Enrollment.user_id == user["userId"],
        Enrollment.course_id == course_id
    ).first()
    if not enrollment:
        raise HTTPException(status_code=403, detail="Vous devez être inscrit pour noter")
    
    # Vérifier si déjà noté
    existing = db.query(Rating).filter(
        Rating.user_id == user["userId"],
        Rating.course_id == course_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Vous avez déjà noté ce cours")
    
    rating = Rating(
        user_id=user["userId"],
        course_id=course_id,
        rating=rating_data.rating,
        comment=rating_data.comment
    )
    db.add(rating)
    db.commit()
    
    # Mettre à jour la moyenne
    from sqlalchemy import func
    avg = db.query(func.avg(Rating.rating)).filter(Rating.course_id == course_id).scalar() or 0
    course = db.query(Course).filter(Course.id == course_id).first()
    course.average_rating = avg
    db.commit()
    
    return {"message": "Avis ajouté", "average_rating": round(avg, 2)}

@router.get("/{course_id}/ratings")
def get_course_ratings(
    course_id: int,
    db: Session = Depends(get_db)
):
    ratings = db.query(Rating).filter(Rating.course_id == course_id).all()
    from sqlalchemy import func
    avg = db.query(func.avg(Rating.rating)).filter(Rating.course_id == course_id).scalar() or 0
    
    return {
        "course_id": course_id,
        "average_rating": round(avg, 2),
        "total_ratings": len(ratings),
        "ratings": [
            {"user_id": r.user_id, "rating": r.rating, "comment": r.comment, "created_at": r.created_at}
            for r in ratings
        ]
    }
# ========== CERTIFICATS ==========

@router.post("/{course_id}/certificates/{user_id}")
def generate_certificate(
    course_id: int,
    user_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    # Vérifier que l'instructeur est propriétaire
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.instructor_id == user["userId"]
    ).first()
    if not course:
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    # Vérifier que l'étudiant a complété le cours (progress = 100%)
    enrollment = db.query(Enrollment).filter(
        Enrollment.user_id == user_id,
        Enrollment.course_id == course_id
    ).first()
    if not enrollment or enrollment.progress < 100:
        raise HTTPException(status_code=400, detail="L'étudiant n'a pas encore complété le cours")
    
    # Vérifier si certificat existe déjà
    existing = db.query(Certificate).filter(
        Certificate.course_id == course_id,
        Certificate.user_id == user_id
    ).first()
    if existing:
        return {"message": "Certificat déjà généré", "certificate_url": existing.certificate_url}
    
    # Générer URL du certificat (à implémenter avec génération PDF)
    certificate_url = f"/certificates/{course_id}/{user_id}.pdf"
    
    new_certificate = Certificate(
        course_id=course_id,
        user_id=user_id,
        certificate_url=certificate_url
    )
    db.add(new_certificate)
    db.commit()
    
    return {"message": "Certificat généré", "certificate_url": certificate_url}
@router.get("/{course_id}/export")
def export_course(
    course_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.instructor_id == user["userId"]
    ).first()
    if not course:
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    lessons = db.query(Lesson).filter(Lesson.course_id == course_id).all()
    assignments = db.query(Assignment).filter(Assignment.course_id == course_id).all()
    
    export_data = {
        "course": {
            "title": course.title,
            "description": course.description,
            "price": course.price,
            "is_free": course.is_free,
            "category": course.category
        },
        "lessons": [
            {"title": l.title, "content": l.content, "video_url": l.video_url, "order": l.order}
            for l in lessons
        ],
        "assignments": [
            {"title": a.title, "description": a.description, "max_score": a.max_score}
            for a in assignments
        ]
    }
    
    return {"export_data": json.dumps(export_data, default=str)}
# ========== STATISTIQUES ÉTUDIANT ==========

@router.get("/my-progress")
def get_my_progress(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """Dashboard étudiant - voir sa progression"""
    enrollments = db.query(Enrollment).filter(
        Enrollment.user_id == user["userId"]
    ).all()
    
    courses_data = []
    for enrollment in enrollments:
        course = db.query(Course).filter(Course.id == enrollment.course_id).first()
        lessons_count = db.query(Lesson).filter(Lesson.course_id == course.id).count()
        
        courses_data.append({
            "course_id": course.id,
            "title": course.title,
            "progress": enrollment.progress,
            "lessons_completed": int((enrollment.progress / 100) * lessons_count) if lessons_count else 0,
            "total_lessons": lessons_count,
            "enrolled_at": enrollment.enrolled_at
        })
    
    return {
        "user_id": user["userId"],
        "total_courses": len(enrollments),
        "average_progress": sum(e.progress for e in enrollments) / len(enrollments) if enrollments else 0,
        "courses": courses_data
    }
@router.post("/import")
def import_course(
    import_data: dict,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    if user["role"] not in ["instructor", "admin"]:
        raise HTTPException(status_code=403, detail="Accès réservé aux instructeurs")
    
    data = import_data.get("course", {})
    new_course = Course(
        title=data.get("title"),
        description=data.get("description", ""),
        price=data.get("price", 0),
        is_free=data.get("is_free", data.get("price", 0) == 0),
        category=data.get("category", "General"),
        instructor_id=user["userId"]
    )
    db.add(new_course)
    db.commit()
    
    # Importer les leçons
    for lesson_data in import_data.get("lessons", []):
        lesson = Lesson(
            course_id=new_course.id,
            title=lesson_data.get("title"),
            content=lesson_data.get("content", ""),
            video_url=lesson_data.get("video_url", ""),
            order=lesson_data.get("order", 1)
        )
        db.add(lesson)
    db.commit()
    
    return {"message": "Cours importé avec succès", "course_id": new_course.id}
@router.post("/courses/{course_id}/certificate")
def generate_student_certificate(
    course_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """Génère un certificat pour l'étudiant connecté"""
    # Vérifier que l'étudiant est inscrit
    enrollment = db.query(Enrollment).filter(
        Enrollment.user_id == user["userId"],
        Enrollment.course_id == course_id
    ).first()
    if not enrollment:
        raise HTTPException(status_code=403, detail="Vous n'êtes pas inscrit à ce cours")
    
    # Vérifier que le cours est complété (progress = 100%)
    if enrollment.progress < 100:
        raise HTTPException(status_code=400, detail="Vous devez compléter le cours à 100% pour obtenir le certificat")
    
    # Vérifier si certificat existe déjà
    existing = db.query(Certificate).filter(
        Certificate.course_id == course_id,
        Certificate.user_id == user["userId"]
    ).first()
    if existing:
        return {"certificate_url": existing.certificate_url}
    
    # Générer un nouveau certificat
    course = db.query(Course).filter(Course.id == course_id).first()
    certificate_url = f"/certificates/{course_id}/{user['userId']}.pdf"
    
    new_certificate = Certificate(
        course_id=course_id,
        user_id=user["userId"],
        certificate_url=certificate_url
    )
    db.add(new_certificate)
    db.commit()
    
    return {"certificate_url": certificate_url}
@router.get("/courses/{course_id}/assignments/student")
def get_course_assignments_for_student(
    course_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """Récupère tous les devoirs d'un cours pour un étudiant"""
    # Vérifier que l'étudiant est inscrit
    enrollment = db.query(Enrollment).filter(
        Enrollment.user_id == user["userId"],
        Enrollment.course_id == course_id
    ).first()
    if not enrollment:
        raise HTTPException(status_code=403, detail="Vous n'êtes pas inscrit à ce cours")
    
    assignments = db.query(Assignment).filter(
        Assignment.course_id == course_id
    ).order_by(Assignment.due_date).all()
    
    # Récupérer les soumissions
    submissions = db.query(Submission).filter(
        Submission.user_id == user["userId"],
        Submission.assignment_id.in_([a.id for a in assignments])
    ).all()
    
    submissions_dict = {s.assignment_id: s for s in submissions}
    
    result = []
    for a in assignments:
        submission = submissions_dict.get(a.id)
        result.append({
            "id": a.id,
            "title": a.title,
            "description": a.description,
            "due_date": a.due_date.isoformat() if a.due_date else None,
            "max_score": a.max_score,
            "submitted": submission is not None,
            "score": submission.score if submission else None,
            "feedback": submission.feedback if submission else None,
            "submitted_at": submission.submitted_at.isoformat() if submission and submission.submitted_at else None
        })
    
    return {"assignments": result, "submissions": submissions}
@router.get("/my-certificates")
def get_my_certificates(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    certificates = db.query(Certificate).filter(
        Certificate.user_id == user["userId"]
    ).all()
    return {"certificates": certificates}
@router.get("/assignments/{assignment_id}/submissions")
def get_submissions(
    assignment_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    course = db.query(Course).filter(Course.id == assignment.course_id).first()
    
    if course.instructor_id != user["userId"] and user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Accès réservé à l'instructeur")
    
    submissions = db.query(Submission).filter(
        Submission.assignment_id == assignment_id
    ).all()
    return {"submissions": submissions, "count": len(submissions)}
@router.get("/", response_model=List[CourseResponse])
def get_courses(
    category: Optional[str] = Query(None),
    is_free: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Course)
    if category:
        query = query.filter(Course.category == category)
    if is_free is not None:
        query = query.filter(Course.is_free == is_free)
    return query.all()

@router.get("/my-courses", response_model=List[CourseResponse])
def get_my_courses(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """Cours créés par l'instructeur connecté"""
    return db.query(Course).filter(
        Course.instructor_id == user["userId"]
    ).all()

@router.get("/{course_id}", response_model=CourseResponse)
def get_course(course_id: int, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Cours non trouvé")
    return course

@router.post("/", response_model=CourseResponse)
def create_course(
    course_data: CourseCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    if user["role"] not in ["instructor", "admin"]:
        raise HTTPException(status_code=403, detail="Accès refusé")
    # Si prix = 0, automatiquement gratuit
    data = course_data.dict()
    if data["price"] == 0:
        data["is_free"] = True
    course = Course(**data, instructor_id=user["userId"])
    db.add(course)
    db.commit()
    db.refresh(course)
    return course

@router.put("/{course_id}", response_model=CourseResponse)
def update_course(
    course_id: int,
    course_data: CourseUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Cours non trouvé")
    if course.instructor_id != user["userId"] and user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Accès refusé")
    for field, value in course_data.dict(exclude_none=True).items():
        setattr(course, field, value)
    # Sync is_free avec price
    if course.price == 0:
        course.is_free = True
    db.commit()
    db.refresh(course)
    return course

@router.delete("/{course_id}")
def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Cours non trouvé")
    if course.instructor_id != user["userId"] and user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Accès refusé")
    db.delete(course)
    db.commit()
    return {"message": "Cours supprimé"}

@router.post("/enroll")
def enroll_course(
    enroll_data: EnrollRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    course = db.query(Course).filter(Course.id == enroll_data.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Cours non trouvé")
    existing = db.query(Enrollment).filter(
        Enrollment.user_id == user["userId"],
        Enrollment.course_id == enroll_data.course_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Déjà inscrit à ce cours")
    enrollment = Enrollment(
        user_id=user["userId"],
        course_id=enroll_data.course_id
    )
    db.add(enrollment)
    db.commit()
    return {"message": "Inscription réussie !"}

@router.get("/{course_id}/students")
def get_course_students(
    course_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """Liste des étudiants inscrits à un cours"""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Cours non trouvé")
    if course.instructor_id != user["userId"] and user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Accès refusé")
    enrollments = db.query(Enrollment).filter(
        Enrollment.course_id == course_id
    ).all()
    return {
        "course_id": course_id,
        "course_title": course.title,
        "total_students": len(enrollments),
        "students": [
            {
                "user_id": e.user_id,
                "enrolled_at": e.enrolled_at,
                "progress": e.progress
            }
            for e in enrollments
        ]
    }

# ── LEÇONS ────────────────────────────────────────────

@router.post("/{course_id}/lessons", response_model=LessonResponse)
def add_lesson(
    course_id: int,
    lesson_data: LessonCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Cours non trouvé")
    if course.instructor_id != user["userId"] and user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Accès refusé")
    lesson = Lesson(**lesson_data.dict(), course_id=course_id)
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson

@router.get("/{course_id}/lessons", response_model=List[LessonResponse])
def get_lessons(course_id: int, db: Session = Depends(get_db)):
    return db.query(Lesson).filter(
        Lesson.course_id == course_id
    ).order_by(Lesson.order).all()

@router.delete("/{course_id}/lessons/{lesson_id}")
def delete_lesson(
    course_id: int,
    lesson_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    lesson = db.query(Lesson).filter(
        Lesson.id == lesson_id,
        Lesson.course_id == course_id
    ).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Leçon non trouvée")
    db.delete(lesson)
    db.commit()
    return {"message": "Leçon supprimée"}