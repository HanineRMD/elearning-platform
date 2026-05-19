# 🎓 eLearning Platform — Microservices Architecture

Plateforme d'apprentissage en ligne avec IA pédagogique et workflow automatisé.

---

## 🏗️ Architecture

```
Client → Nginx (Gateway :80) → Microservices
                               ├── Frontend      :3001 (Next.js)
                               ├── User Service  :8002 (Node.js)
                               ├── Course Service:8001 (FastAPI)
                               ├── Analytics     :8003 (FastAPI)
                               └── AI Tutor      :8004 (FastAPI + Ollama)

Datastores
├── PostgreSQL  :5432
├── MongoDB     :27017
├── MinIO       :9000 / :9001
└── Ollama      :11434

Automation
└── n8n         :5678
```

---

## 🚀 Lancement rapide

### Prérequis
- Docker Desktop installé
- 8 Go RAM minimum (pour Ollama)

### Démarrer tous les services

```bash
git clone <repo-url>
cd elearning-platform
docker-compose up -d --build
```

### Vérifier que tout tourne

```bash
docker-compose ps
```

---

## 🌐 Accès aux interfaces

| Service | URL | Credentials |
|---|---|---|
| Frontend | http://localhost:3001 | — |
| API Gateway | http://localhost:80 | — |
| n8n Automation | http://localhost:5678 | admin / admin |
| MinIO Console | http://localhost:9001 | minioadmin / minioadmin |
| AI Tutor API | http://localhost:8004/docs | — |
| Course API | http://localhost:8001/docs | — |
| User API | http://localhost:8002/docs | — |

---

## 🤖 Configuration Ollama (IA locale)

```bash
# Télécharger le modèle Mistral (une seule fois)
docker exec -it ollama ollama pull mistral

# Vérifier
docker exec -it ollama ollama list
```

---

## 📦 MinIO — Buckets

```bash
# Créer les buckets via CLI
docker run --rm --network elearning-network \
  --entrypoint sh minio/mc -c "
    mc alias set local http://minio:9000 minioadmin minioadmin &&
    mc mb local/course-media &&
    mc mb local/user-avatars &&
    mc mb local/feedback-reports &&
    mc ls local
  "
```

---

## 🔄 n8n — Workflow Feedback

### Importer le workflow
1. Ouvrir http://localhost:5678
2. Menu ☰ → Workflows → Import from file
3. Sélectionner `feedback-workflow-v2.json`
4. Activer le workflow (toggle)

### Tester le workflow

```bash
curl -X POST http://localhost:5678/webhook/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "user": "alice",
    "course": "DevOps M1",
    "rating": 5,
    "comment": "Cours très bien structuré !"
  }'
```

### Réponse attendue

```json
{
  "success": true,
  "feedback_id": "fb_...",
  "sentiment": "positif",
  "ai_summary": "Feedback positif pour DevOps M1. Note: 5/5.",
  "stored_as": "fb_..._DevOps-M1.json",
  "timestamp": "2026-..."
}
```

---

## 🧪 Tests des microservices

### User Service — Inscription

```bash
curl -X POST http://localhost:8002/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Alice","email":"alice@test.com","password":"123456"}'
```

### Course Service — Liste des cours

```bash
curl http://localhost:8001/api/courses
```

### AI Tutor — Question

```bash
curl -X POST http://localhost:8004/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"Explique Docker","course_id":"1"}'
```

### Analytics — Dashboard

```bash
curl http://localhost:8003/api/analytics/dashboard
```

---

## 🗄️ Structure du projet

```
elearning-platform/
├── docker-compose.yml
├── init-db.sql
├── nginx/
│   └── nginx.conf
├── frontend/
│   ├── Dockerfile
│   └── src/
├── services/
│   ├── user-service/
│   │   ├── Dockerfile
│   │   └── src/
│   ├── course-service/
│   │   ├── Dockerfile
│   │   └── main.py
│   ├── analytics-service/
│   │   ├── Dockerfile
│   │   └── main.py
│   └── ai-tutor-service/
│       ├── Dockerfile
│       └── main.py
└── n8n/
    └── feedback-workflow-v2.json
```

---

## 🛑 Arrêter les services

```bash
# Arrêter sans supprimer les données
docker-compose down

# Arrêter ET supprimer les volumes (reset complet)
docker-compose down -v
```

---

## 👨‍💻 Auteur

Projet réalisé dans le cadre du **Master DevOps & Cloud — M1**  
Intégration microservices · IA · Automatisation n8n · Containerisation Docker
