from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from datetime import datetime
from src.database import Base

class CourseView(Base):
    __tablename__ = "course_views"

    id        = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, nullable=False)
    user_id   = Column(String(100))
    viewed_at = Column(DateTime, default=datetime.utcnow)

class EnrollmentEvent(Base):
    __tablename__ = "enrollment_events"

    id          = Column(Integer, primary_key=True, index=True)
    course_id   = Column(Integer, nullable=False)
    user_id     = Column(String(100), nullable=False)
    enrolled_at = Column(DateTime, default=datetime.utcnow)

class ProgressEvent(Base):
    __tablename__ = "progress_events"

    id         = Column(Integer, primary_key=True, index=True)
    course_id  = Column(Integer, nullable=False)
    user_id    = Column(String(100), nullable=False)
    lesson_id  = Column(Integer, nullable=False)
    progress   = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=datetime.utcnow)

class Feedback(Base):
    __tablename__ = "feedbacks"

    id         = Column(Integer, primary_key=True, index=True)
    course_id  = Column(Integer, nullable=False)
    user_id    = Column(String(100), nullable=False)
    rating     = Column(Integer)        # 1 à 5
    comment    = Column(String(1000))
    created_at = Column(DateTime, default=datetime.utcnow)