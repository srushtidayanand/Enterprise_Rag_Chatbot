# Enterprise RAG Chatbot — Complete Project Guide

---

## What is This Project?

An AI-powered chatbot that answers questions from company policy documents. Employees, HR, Managers, and Admins each see only the documents relevant to their role. The AI searches the documents and generates answers using a local LLM (Mistral 7B).

---

## Project Structure

```
enterprise-rag-chatbot/
│
├── backend/                  # Python FastAPI server
│   ├── app.py                # All API endpoints
│   ├── auth.py               # Login, JWT tokens, user management
│   ├── database.py           # SQLite database setup (ORM models)
│   ├── analytics.py          # Query logs, chat history, stats
│   ├── rag_engine.py         # AI search + answer generation
│   └── ingest_documents.py   # Build vectorstore from PDFs
│
├── frontend/                 # Browser UI (HTML/CSS/JS)
│   ├── index.html            # Main chat interface
│   ├── login.html            # Login page
│   ├── script.js             # Frontend logic
│   ├── style.css             # Styling
│   └── config.js             # Server IP configuration
│
├── data/                     # Policy documents (PDFs)
│   ├── employee/             # Attendance, Leave, Code of Conduct, WFH
│   ├── hr/                   # Payroll, Recruitment Policy
│   └── manager/              # Performance Review, Promotion Policy
│
├── vectorstore/              # FAISS vector indexes (auto-generated)
│   ├── employee/
│   ├── hr/
│   └── manager/
│
├── chatbot.db                # SQLite database (auto-created on first run)
├── generate_docs.py          # Script to generate sample policy PDFs
├── requirements.txt          # Python dependencies
└── start_server.bat          # Double-click to start everything
```

---

## Tech Stack

| Layer        | Technology                          |
|--------------|-------------------------------------|
| Frontend     | HTML, CSS, JavaScript               |
| Backend      | Python, FastAPI, Uvicorn            |
| AI / LLM     | Mistral 7B via LM Studio            |
| Vector Search| FAISS + sentence-transformers       |
| Database     | SQLite (local file: chatbot.db)     |
| Auth         | JWT (JSON Web Tokens)               |
| PDF Viewer   | PDF.js (in-browser highlighting)    |
| Doc Generation| fpdf2                              |

---

## User Roles & Document Access

| Role     | Username | Default Password | Documents Access                              |
|----------|----------|------------------|-----------------------------------------------|
| Employee | john     | password123      | Attendance, Leave, Code of Conduct, WFH       |
| HR       | alice    | password123      | Payroll, Recruitment Policy                   |
| Manager  | bob      | password123      | Performance Review, Promotion Policy          |
| Admin    | admin    | admin123         | All documents from all roles                  |

---

## Database (SQLite)

File location: `enterprise-rag-chatbot/chatbot.db`

### Tables

**users**
| Column        | Description                    |
|---------------|--------------------------------|
| username      | Unique login name (primary key)|
| password_hash | SHA-256 hashed password        |
| role          | employee / hr / manager / admin|
| created_at    | Account creation time          |
| is_active     | 1 = active, 0 = disabled       |

**query_logs**
| Column          | Description                        |
|-----------------|------------------------------------|
| id              | Auto increment ID                  |
| username        | Who asked the question             |
| role            | Their role at the time             |
| question        | The question they asked            |
| answer          | The AI's answer                    |
| confidence      | How confident the AI was (0-1)     |
| response_time_ms| How long it took to answer         |
| sources_count   | How many document chunks were used |
| feedback        | 1 = thumbs up, -1 = thumbs down    |
| timestamp       | When it was asked                  |

**chat_history**
| Column          | Description                        |
|-----------------|------------------------------------|
| id              | Auto increment ID                  |
| username        | Who had the conversation           |
| role            | Their role                         |
| question        | Question asked                     |
| answer          | Full AI answer                     |
| sources         | Document sources used (JSON)       |
| confidence      | Confidence score                   |
| response_time_ms| Response time                      |
| timestamp       | When it happened                   |

**token_blacklist**
| Column     | Description                    |
|------------|--------------------------------|
| token      | JWT token that was logged out  |
| created_at | When it was blacklisted        |

---

## How to View Database Data

### Option 1 — Admin Dashboard (In App)
Login as `admin / admin123` → see Analytics, Chat History, Documents tabs.

### Option 2 — DB Browser for SQLite
1. Download from https://sqlitebrowser.org
2. Open `chatbot.db`
3. Click Browse Data → select any table

### Option 3 — Terminal Quick Check
```cmd
cd enterprise-rag-chatbot
.venv\Scripts\activate
python
```
```python
from backend.database import get_session, QueryLog, ChatHistory
with get_session() as s:
    for r in s.query(QueryLog).all():
        print(r.username, r.question[:60], r.timestamp)
```

---

## API Endpoints

| Method | Endpoint                  | Access  | Description                    |
|--------|---------------------------|---------|--------------------------------|
| POST   | /login                    | Public  | Login and get JWT token        |
| POST   | /logout                   | Auth    | Logout and blacklist token     |
| POST   | /ask                      | Auth    | Ask a question (full response) |
| POST   | /ask-stream               | Auth    | Ask a question (streaming)     |
| GET    | /chat/history             | Auth    | Get your chat history          |
| POST   | /feedback                 | Auth    | Submit thumbs up/down          |
| GET    | /documents/list           | Auth    | List accessible documents      |
| GET    | /analytics/stats          | Auth    | Query statistics               |
| GET    | /analytics/activity       | Auth    | User activity log              |
| GET    | /admin/users              | Admin   | List all users                 |
| POST   | /admin/create-user        | Admin   | Create new user                |
| GET    | /admin/stats-detailed     | Admin   | Full analytics                 |

Full interactive API docs: `http://localhost:8000/docs`

---

## Server vs Client — What Runs Where

```
CLIENT LAPTOP                    SERVER LAPTOP
─────────────                    ─────────────────────────────
Browser only         ──────►     Frontend (port 8001)
                                       │
                                       ▼
                     ──────►     Backend API (port 8000)
                                   │          │
                                   ▼          ▼
                              LM Studio    SQLite DB
                              (port 1234)  chatbot.db
                                   │
                                   ▼
                              FAISS Vectorstore
                              (PDF documents in memory)
```

---

## Setup — One Time (Server Laptop Only)

### Step 1 — Install dependencies
```cmd
cd enterprise-rag-chatbot
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2 — Generate policy documents
```cmd
python generate_docs.py
```

### Step 3 — Build vectorstore from documents
```cmd
cd backend
python ingest_documents.py
cd ..
```

### Step 4 — Open firewall ports (Run CMD as Administrator)
```cmd
netsh advfirewall firewall add rule name="RAG Backend" dir=in action=allow protocol=TCP localport=8000
netsh advfirewall firewall add rule name="RAG Frontend" dir=in action=allow protocol=TCP localport=8001
```

---

## Running the App — Every Time

### Step 1 — Start LM Studio
Open LM Studio → load Mistral 7B → click Start Server (port 1234)

### Step 2 — Start Backend (CMD window 1)
```cmd
cd enterprise-rag-chatbot
.venv\Scripts\activate
cd backend
python -m uvicorn app:app --host 0.0.0.0 --port 8000
```

### Step 3 — Start Frontend (CMD window 2)
```cmd
cd enterprise-rag-chatbot\frontend
python -m http.server 8001
```

### Step 4 — Open in Browser
- Server laptop: `http://localhost:8001/login.html`
- Client laptops: `http://192.168.1.2:8001/login.html`

---

## Important Notes

- Both CMD windows must stay open while the app is running
- All client laptops must be on the same WiFi as the server
- If server IP changes, update `frontend/config.js` with new IP
- Run `ingest_documents.py` again if you add new PDF documents
- `chatbot.db` is auto-created on first backend run — do not delete it

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Cannot connect to backend | Check backend CMD is running, check firewall rules |
| Client can't reach server | Run `ipconfig` on server, update config.js with correct IP |
| No AI answer | Make sure LM Studio is running with Mistral 7B on port 1234 |
| Empty chat history | Ask at least one question first, then check admin dashboard |
| Port already in use | Close old CMD window or restart computer |
