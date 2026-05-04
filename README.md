# Enterprise RAG Chatbot

A role-aware internal knowledge chatbot built with Retrieval-Augmented Generation (RAG). Employees query company policy documents through a chat interface; responses are grounded in actual documents and scoped by the user's role.

---

## Features

### RAG Core
- Semantic document retrieval using FAISS + Sentence-Transformers (`all-MiniLM-L6-v2`)
- Answer generation via Mistral 7B (served locally through LM Studio)
- Role-scoped vectorstores — each role has its own FAISS index, with fallback to the shared index

### Authentication & Authorization
- JWT-based auth (HS256, 24-hour expiry) with token blacklist on logout
- Role-Based Access Control (RBAC): `employee`, `hr`, `manager`, `admin`
- Admin-only endpoints for user management

### Chat
- **Standard Q&A** (`POST /ask`) — full answer with timing metadata
- **Streaming** (`POST /ask-stream`) — Server-Sent Events for real-time token-by-token output
- Per-query metrics: `retrieval_time_ms`, `llm_time_ms`, `total_time_ms`

### Source Citations & Confidence
- Every response includes source references: document filename, page number, 150-character snippet
- Confidence score (0–1) derived from FAISS retrieval similarity

### Analytics
| Endpoint | What it returns |
|---|---|
| `GET /analytics/stats` | Total queries, unique users, avg response time, top questions, per-role breakdown |
| `GET /analytics/performance` | Min/max/avg times, p95 percentile, daily query counts |
| `GET /analytics/activity` | Per-user query history with confidence trends |

### Admin
- Create users, list users, full dashboard stats — admin role only

### Frontend
- Login page with demo credentials
- Chat UI with role badge, streaming animation, expandable source cards, performance metrics
- Vanilla HTML/CSS/JS — no build step required

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI 0.104.1, Python 3.x, Uvicorn |
| RAG | FAISS, Sentence-Transformers, LangChain |
| LLM | Mistral 7B via LM Studio (local, port 1234) |
| Auth | JWT (python-jose), bcrypt (passlib) |
| Frontend | HTML5, CSS3, vanilla JavaScript |

---

## Project Structure

```
enterprise-rag-chatbot/
├── backend/
│   ├── app.py              # FastAPI app — all 15 endpoints
│   ├── rag_engine.py       # FAISS retrieval, LLM calls, streaming, confidence scoring
│   ├── auth.py             # JWT auth, RBAC, user store, token blacklist
│   ├── analytics.py        # Query logging and stats aggregation
│   └── ingest_documents.py # Build vectorstores from PDF/DOCX files
├── frontend/
│   ├── login.html
│   ├── index.html          # Main chat UI
│   ├── script.js
│   └── style.css
├── data/
│   ├── employee/           # Attendance, code of conduct, leave, WFH policies
│   ├── hr/                 # Payroll and recruitment policies
│   └── manager/            # Performance review and promotion policies
├── vectorstore/            # Generated — run ingest_documents.py to create
└── requirements.txt
```

---

## Setup

### Prerequisites
- Python 3.9+
- [LM Studio](https://lmstudio.ai/) with Mistral 7B loaded and local server running on port `1234`

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/enterprise-rag-chatbot.git
cd enterprise-rag-chatbot
```

### 2. Create a virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Ingest documents

Run once to build FAISS vectorstores from the PDFs in `data/`.

```bash
# Shared vectorstore
python backend/ingest_documents.py

# Role-specific vectorstores (recommended)
python backend/ingest_documents.py --role employee
python backend/ingest_documents.py --role hr
python backend/ingest_documents.py --role manager
```

### 5. Start LM Studio

Open LM Studio, load **Mistral 7B**, and start the local server on port `1234`.

### 6. Start the backend

```bash
cd backend
uvicorn app:app --reload --port 8000
```

### 7. Start the frontend

```bash
cd frontend
python -m http.server 8001
```

### 8. Open the app

[http://localhost:8001/login.html](http://localhost:8001/login.html)

---

## Demo Users

| Username | Password | Role |
|---|---|---|
| john | password123 | employee |
| alice | password123 | hr |
| bob | password123 | manager |
| admin | admin123 | admin |

---

## API Reference

### Authentication
```
POST /login              # Returns JWT token
POST /logout             # Invalidates token
POST /change-password    # Update current user's password
```

### Chat
```
POST /ask                # Standard response with sources and metrics
POST /ask-stream         # SSE streaming response
```

Request body:
```json
{
  "question": "What is the leave policy?"
}
```

### Analytics
```
GET /analytics/stats        # Query stats (?date_from=&date_to=&role=)
GET /analytics/performance  # System performance metrics
GET /analytics/activity     # User query history
```

### Admin (admin role only)
```
POST /admin/create-user
GET  /admin/users
GET  /admin/stats-detailed
```

### Health
```
GET /        # Version and feature list
GET /health  # Detailed health check
```

---

## Configuration

Key parameters in `backend/rag_engine.py`:

```python
RETRIEVAL_K = 3              # Documents retrieved per query
TEMPERATURE = 0.1            # LLM temperature (lower = more deterministic)
MAX_TOKENS = 500             # Max tokens in LLM response
REQUEST_TIMEOUT = 120        # LM Studio API timeout (seconds)
TOKEN_EXPIRATION_HOURS = 24  # JWT token lifetime
```

---

## Performance

| Operation | Typical Time |
|---|---|
| Cold start (model load) | 2–4 s |
| Warm query (full round-trip) | 0.8–1.5 s |
| FAISS retrieval only | 50–150 ms |
| LLM inference (Mistral 7B) | 800–1500 ms |
| Streaming overhead | +20–30% |

---

## Roadmap

- [ ] Persistent query storage (SQLite / PostgreSQL)
- [ ] Rate limiting
- [ ] Redis caching layer
- [ ] Admin UI dashboard
- [ ] Cloud deployment (Azure / AWS / GCP)
- [ ] User feedback collection
- [ ] Multi-language support
