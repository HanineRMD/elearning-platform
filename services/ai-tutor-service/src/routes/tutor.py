from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from jose import jwt, JWTError
import httpx
from dotenv import load_dotenv
import os
import json
import re

load_dotenv()
router = APIRouter()
JWT_SECRET = os.getenv("JWT_SECRET")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "mistral")

# ── Auth ──────────────────────────────────────────────
def get_current_user(authorization: str = Header(...)):
    try:
        token = authorization.replace("Bearer ", "")
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalide")

# ── Appel Ollama avec fallback si non disponible ──────
async def call_ollama(prompt: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={"model": MODEL_NAME, "prompt": prompt, "stream": False}
            )
            data = response.json()
            return data.get("response", "")
    except Exception as e:
        # Ollama non disponible → réponse de secours
        return None

# ── Schémas ───────────────────────────────────────────
class QuestionRequest(BaseModel):
    question: str
    course_title: Optional[str] = ""
    course_content: Optional[str] = ""

class QuizRequest(BaseModel):
    course_title: str
    course_content: str
    num_questions: int = 3

class RecommendRequest(BaseModel):
    completed_courses: List[str] = []
    interests: Optional[str] = ""

# ── ROUTES ────────────────────────────────────────────

@router.post("/ask")
async def ask_question(data: QuestionRequest, user=Depends(get_current_user)):
    prompt = f"""Tu es un tuteur pédagogique expert et bienveillant.
Cours : {data.course_title}
Contenu : {data.course_content}
Question : {data.question}
Réponds de façon claire et simple en français."""

    answer = await call_ollama(prompt)

    # Si Ollama n'est pas disponible, réponse de secours
    if not answer:
        answer = (
            f"Bonne question sur **{data.course_title}** ! "
            f"Concernant '{data.question}', voici ce que je peux te dire : "
            f"ce sujet est fondamental dans ce domaine. "
            f"Je te conseille de consulter la documentation officielle et de pratiquer avec des exercices. "
            f"⚠️ Note : Le service IA complet nécessite Ollama. Lance : `ollama pull mistral`"
        )

    return {"question": data.question, "answer": answer}


@router.post("/quiz")
async def generate_quiz(data: QuizRequest, user=Depends(get_current_user)):
    prompt = f"""Génère {data.num_questions} questions QCM sur : {data.course_title}
Contenu : {data.course_content}
Format JSON strict :
{{
  "questions": [
    {{
      "question": "...",
      "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
      "correct": "A",
      "explanation": "..."
    }}
  ]
}}"""

    raw = await call_ollama(prompt)

    if raw:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass

    # Quiz de secours si Ollama absent
    return {
        "questions": [
            {
                "question": f"Quel est l'objectif principal du cours '{data.course_title}' ?",
                "options": [
                    "A) Apprendre les concepts fondamentaux",
                    "B) Faire du sport",
                    "C) Cuisiner",
                    "D) Dessiner"
                ],
                "correct": "A",
                "explanation": f"Ce cours vise à maîtriser les bases de {data.course_title}."
            },
            {
                "question": "Quelle est la meilleure façon d'apprendre ?",
                "options": [
                    "A) Regarder sans pratiquer",
                    "B) Pratiquer régulièrement",
                    "C) Mémoriser sans comprendre",
                    "D) Ne jamais faire d'erreurs"
                ],
                "correct": "B",
                "explanation": "La pratique régulière est la clé de l'apprentissage."
            },
            {
                "question": "Qu'est-ce qu'un microservice ?",
                "options": [
                    "A) Un très petit ordinateur",
                    "B) Un service indépendant avec une seule responsabilité",
                    "C) Un langage de programmation",
                    "D) Une base de données"
                ],
                "correct": "B",
                "explanation": "Un microservice est un composant autonome avec une fonction précise."
            }
        ]
    }


@router.post("/recommend")
async def get_recommendations(data: RecommendRequest, user=Depends(get_current_user)):
    completed = ", ".join(data.completed_courses) if data.completed_courses else "aucun"
    prompt = f"""Conseiller pédagogique.
Cours complétés : {completed}
Intérêts : {data.interests}
Suggère 3 thèmes en JSON :
{{
  "recommendations": [
    {{"theme": "...", "reason": "..."}}
  ]
}}"""

    raw = await call_ollama(prompt)

    if raw:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass

    # Recommandations de secours
    return {
        "recommendations": [
            {"theme": "Docker & Kubernetes", "reason": "Essentiel pour déployer des microservices."},
            {"theme": "FastAPI avancé",      "reason": "Approfondir le développement d'APIs REST."},
            {"theme": "CI/CD avec GitHub Actions", "reason": "Automatiser tes déploiements."}
        ]
    }