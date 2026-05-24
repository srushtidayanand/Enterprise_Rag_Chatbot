# Enterprise RAG Chatbot — Complete Project Document

---

## 1. Project Overview

An AI-powered chatbot that answers questions from company policy documents. Built for internal enterprise use across multiple devices on the same WiFi network. Each user sees only documents relevant to their role. The AI searches documents and generates answers using a locally running LLM (Mistral 7B).

---

## 2. Tech Stack

| Layer            | Technology                                      |
|------------------|-------------------------------------------------|
| Frontend         | HTML, CSS, JavaScript, PDF.js                   |
| Backend          | Python, FastAPI, Uvicorn                        |
| AI / LLM         | Mistral 7B via LM Studio (port 1234)            |
| Vector Search    | FAISS + sentence-transformers (all-MiniLM-L6-v2)|
| Database         | Neon PostgreSQL (cloud, SSL encrypted)          |
| Authentication   | JWT (JSON Web Tokens) with bcrypt               |
| PDF Generation   | fpdf2                                           |
| PDF Viewer       | PDF.js (in-browser with text highlighting)      |

---

## 3. Project Folder Structure

```
enterprise-rag-chatbot/
│
├── backend/
│   ├── app.py                  API endpoints (FastAPI)
│   ├── auth.py                 Login, JWT, account lockout, password rules
│   ├── database.py             PostgreSQL ORM models (SQLAlchemy)
│   ├── analytics.py            Query logs, chat history, stats
│   ├── rag_engine.py           FAISS search + LLM answer generation
│   ├── ingest_documents.py     Builds vectorstore from PDFs
│   └── .env                    DB credentials + JWT secret (NOT on GitHub)
│
├── frontend/
│   ├── index.html              Main chat interface
│   ├── login.html              Login page
│   ├── script.js               Frontend logic + PDF viewer
│   ├── style.css               Styling
│   └── config.js               Server IP (API_BASE)
│
├── data/
│   ├── employee/               Attendance, Leave, Code of Conduct, WFH Policy
│   ├── hr/                     Payroll, Recruitment & Selection Policy
│   └── manager/                Performance Review, Promotion Policy
│
├── vectorstore/                FAISS indexes (auto-generated, not on GitHub)
│   ├── employee/
│   ├── hr/
│   └── manager/
│
├── generate_docs.py            Generates all policy PDFs using fpdf2
├── requirements.txt            Python dependencies
├── start_server.bat            Double-click to start backend + frontend
└── .gitignore                  Excludes .env, vectorstore, .venv, *.db
```

---

## 4. User Roles & Access

| Role     | Username | Password     | Documents Accessible                              |
|----------|----------|--------------|---------------------------------------------------|
| Employee | john     | John@1234    | Attendance, Leave, Code of Conduct, WFH Policy    |
| HR       | alice    | Alice@1234   | Payroll Policy, Recruitment & Selection Policy    |
| Manager  | bob      | Bob@1234     | Performance Review Policy, Promotion Policy       |
| Admin    | admin    | Admin@1234   | All documents from all roles                      |

---

## 5. Database (Neon PostgreSQL)

### Connection
- Host: Neon cloud (SSL required)
- Credentials stored in `backend/.env` only
- Never hardcoded in source code

### Tables

**users**
| Column          | Type    | Description                          |
|-----------------|---------|--------------------------------------|
| username        | String  | Primary key, unique login name       |
| password_hash   | String  | bcrypt hashed password               |
| role            | String  | employee / hr / manager / admin      |
| created_at      | DateTime| Account creation time                |
| is_active       | Integer | 1 = active, 0 = disabled             |
| failed_attempts | Integer | Count of consecutive failed logins   |
| locked_until    | DateTime| Account locked until this time       |

**query_logs**
| Column           | Type    | Description                         |
|------------------|---------|-------------------------------------|
| id               | Integer | Auto increment                      |
| username         | String  | Who asked                           |
| role             | String  | Their role                          |
| question         | Text    | The question asked                  |
| answer           | Text    | AI generated answer                 |
| confidence       | Float   | Confidence score 0.0 - 1.0          |
| response_time_ms | Integer | Time taken to answer in ms          |
| sources_count    | Integer | Number of document chunks used      |
| feedback         | Integer | 1 = thumbs up, -1 = thumbs down     |
| timestamp        | DateTime| When it was asked                   |

**chat_history**
| Column           | Type    | Description                         |
|------------------|---------|-------------------------------------|
| id               | Integer | Auto increment                      |
| username         | String  | Who had the conversation            |
| role             | String  | Their role                          |
| question         | Text    | Question asked                      |
| answer           | Text    | Full AI answer                      |
| sources          | Text    | Document sources used (JSON)        |
| confidence       | Float   | Confidence score                    |
| response_time_ms | Integer | Response time in ms                 |
| timestamp        | DateTime| When it happened                    |

**token_blacklist**
| Column     | Type    | Description                         |
|------------|---------|-------------------------------------|
| token      | Text    | JWT token that was logged out       |
| created_at | DateTime| When it was blacklisted             |

---

## 6. Security Features Implemented

| #  | Feature                     | Details                                              |
|----|-----------------------------|------------------------------------------------------|
| 1  | bcrypt password hashing     | Passwords are impossible to reverse engineer         |
| 2  | JWT authentication          | Every API request requires a valid token             |
| 3  | JWT secret in .env          | Not in source code, not on GitHub                    |
| 4  | Token expiry (8 hours)      | Forces re-login after 8 hours                        |
| 5  | Token blacklist on logout   | Logged-out tokens are permanently rejected           |
| 6  | Token blacklist auto-cleanup| Expired tokens deleted automatically on every login  |
| 7  | Account lockout             | 5 wrong passwords = account locked for 15 minutes   |
| 8  | Rate limiting on login      | Max 10 login attempts per 60 seconds per IP          |
| 9  | Password complexity rules   | Min 8 chars, uppercase, lowercase, number, special   |
| 10 | Role-based access control   | Users can only see their role's documents            |
| 11 | Protected PDF download      | PDFs served only after JWT + role verification       |
| 12 | Path traversal prevention   | Filenames sanitized to block `../` attacks           |
| 13 | CORS restricted             | Only server IP allowed, not open to internet         |
| 14 | SSL to Neon DB              | Database connection is encrypted                     |
| 15 | Admin-only routes           | /admin/* endpoints blocked for non-admin users       |
| 16 | Role enforcement on analytics | Users only see their own activity                  |

---

## 7. Known Remaining Limitations

| # | Issue                  | Impact                                              |
|---|------------------------|-----------------------------------------------------|
| 1 | No HTTPS               | LAN traffic is unencrypted (HTTP only)              |
| 2 | Rate limit in-memory   | Resets if backend restarts                          |
| 3 | No audit log for admin | Admin actions not recorded                          |
| 4 | No password expiry     | Users can keep same password forever                |
| 5 | LM Studio no auth      | Port 1234 open on LAN without login                 |
| 6 | Questions in plain text| Sensitive queries readable in database              |

---

## 8. API Endpoints

| Method | Endpoint                              | Access   | Description                    |
|--------|---------------------------------------|----------|--------------------------------|
| GET    | /                                     | Public   | API info                       |
| GET    | /health                               | Public   | Health check                   |
| POST   | /login                                | Public   | Login, returns JWT token       |
| POST   | /logout                               | Auth     | Logout, blacklists token       |
| POST   | /ask                                  | Auth     | Ask a question (full response) |
| POST   | /ask-stream                           | Auth     | Ask a question (streaming)     |
| GET    | /chat/history                         | Auth     | Your chat history              |
| POST   | /feedback                             | Auth     | Submit thumbs up/down          |
| POST   | /change-password                      | Auth     | Change your password           |
| GET    | /user/info                            | Auth     | Get your profile               |
| GET    | /documents/list                       | Auth     | List your accessible documents |
| GET    | /documents/download/{role}/{filename} | Auth     | Download PDF (role checked)    |
| GET    | /analytics/stats                      | Auth     | Query statistics               |
| GET    | /analytics/activity                   | Auth     | User activity log              |
| GET    | /analytics/performance                | Admin/HR | Performance metrics            |
| GET    | /metrics/evaluation                   | Auth     | Evaluation metrics             |
| GET    | /admin/users                          | Admin    | List all users                 |
| POST   | /admin/create-user                    | Admin    | Create new user                |
| GET    | /admin/stats-detailed                 | Admin    | Full analytics                 |

Interactive API docs: `http://192.168.1.2:8000/docs`

---

## 9. Architecture — Server vs Client

```
CLIENT LAPTOP                        SERVER LAPTOP
─────────────                        ─────────────────────────────────────
                                     ┌─────────────────────────────────┐
Browser only            ──────►      │  Frontend  (port 8001)          │
                                     │  HTML / CSS / JS                │
                                     └────────────┬────────────────────┘
                                                  │
                        ──────►      ┌────────────▼────────────────────┐
                                     │  Backend API  (port 8000)       │
                                     │  FastAPI + Auth + RAG           │
                                     └──────┬─────────────┬────────────┘
                                            │             │
                                 ┌──────────▼──┐   ┌──────▼──────────┐
                                 │  LM Studio  │   │  Neon PostgreSQL │
                                 │  Mistral 7B │   │  (cloud, SSL)   │
                                 │  port 1234  │   │  users, logs    │
                                 └─────────────┘   └─────────────────┘
                                            │
                                 ┌──────────▼──────────┐
                                 │  FAISS Vectorstore   │
                                 │  (in memory on start)│
                                 │  employee/hr/manager │
                                 └─────────────────────┘
```

---

## 10. One-Time Setup (Server Laptop)

```cmd
cd enterprise-rag-chatbot

REM Create virtual environment
python -m venv .venv
.venv\Scripts\activate

REM Install dependencies
pip install -r requirements.txt

REM Generate policy PDFs
python generate_docs.py

REM Build FAISS vectorstore from PDFs
cd backend
python ingest_documents.py
cd ..

REM Open firewall ports (run CMD as Administrator)
netsh advfirewall firewall add rule name="RAG Backend" dir=in action=allow protocol=TCP localport=8000
netsh advfirewall firewall add rule name="RAG Frontend" dir=in action=allow protocol=TCP localport=8001
```

---

## 11. Running the App (Every Time)

### Step 1 — Start LM Studio
Open LM Studio app → load Mistral 7B → click Start Server (port 1234)

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
| Device        | URL                                      |
|---------------|------------------------------------------|
| Server laptop | http://localhost:8001/login.html         |
| Client laptop | http://192.168.1.2:8001/login.html       |

---

## 12. How to View Data

### Admin Dashboard (in app)
Login as `admin / Admin@1234` → Analytics tab

### Neon Dashboard
Go to console.neon.tech → SQL Editor:
```sql
SELECT username, question, confidence, timestamp FROM query_logs ORDER BY timestamp DESC;
SELECT username, question, answer, timestamp FROM chat_history ORDER BY timestamp DESC;
SELECT username, role, failed_attempts, locked_until FROM users;
```

---

## 13. Troubleshooting

| Problem                        | Fix                                                          |
|--------------------------------|--------------------------------------------------------------|
| Cannot connect to backend      | Check backend CMD is running, check firewall rules           |
| Client can't reach server      | Run ipconfig on server, update config.js with correct IP     |
| No AI answer                   | Make sure LM Studio is running with Mistral 7B on port 1234  |
| Account locked                 | Wait 15 minutes or admin resets in Neon users table          |
| Port already in use            | Close old CMD window or restart computer                     |
| PDF not loading                | Check you are logged in with correct role                    |
| DB connection error            | Check internet connection (Neon is cloud)                    |

---

## 14. Important Files — Do Not Delete

| File                  | Why Important                                      |
|-----------------------|----------------------------------------------------|
| backend/.env          | DB credentials and JWT secret                      |
| vectorstore/          | Pre-built document indexes — rebuild with ingest   |
| data/                 | All policy PDF documents                           |
| requirements.txt      | All Python package versions                        |

---

*Generated: May 2026 | Version: 3.0 | Internal use only*
