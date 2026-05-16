# 📡 Enterprise RAG Chatbot - Complete API Specification

## API Overview

**Base URL:** `http://127.0.0.1:8000`  
**Protocol:** HTTP REST + JSON  
**Authentication:** JWT (Phase 3+)  
**Rate Limiting:** To be implemented

---

## Current API Endpoints (MVP - Phase 1)

### 1. Health Check

**Endpoint:** `GET /`

**Description:** Verify backend is running

**Request:**
```bash
curl http://127.0.0.1:8000/
```

**Response (200 OK):**
```json
{
  "message": "Enterprise RAG Chatbot Running 🚀"
}
```

**Error Responses:**
- `500` - Server error

**Use Case:** Frontend startup check, monitoring

---

### 2. Ask Question

**Endpoint:** `POST /ask`

**Description:** Submit question and get answer from RAG system

**Request:**
```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the vacation policy?"}'
```

**Request Body:**
```json
{
  "question": "What is the vacation policy?"
}
```

**Request Schema:**
```python
class Question(BaseModel):
    question: str  # Required, non-empty
```

**Response (200 OK):**
```json
{
  "answer": "Based on the vacation policy, employees are entitled to 20 days of annual vacation per year. Vacation requests must be submitted at least two weeks in advance through the HR portal."
}
```

**Response Time:** 60-120 seconds (typical)

**Error Responses:**

```json
// 400 Bad Request - Invalid input
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "question"],
      "msg": "Field required"
    }
  ]
}

// 503 Service Unavailable - LM Studio not running
{
  "detail": "Error connecting to AI server."
}

// 500 Internal Server Error
{
  "detail": "Error communicating with the AI model."
}
```

**Use Cases:**
- Regular Q&A
- Document lookup
- Policy questions

**Performance Notes:**
- Retrieval: 1-3 seconds
- LLM inference: 60-90 seconds
- Network latency: 1-2 seconds

---

## Planned API Endpoints (Future Phases)

### Phase 2a: Source Citations

**Endpoint:** `POST /ask-with-sources`

**Description:** Get answer with source document references

**Request:**
```bash
curl -X POST http://127.0.0.1:8000/ask-with-sources \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the vacation policy?"}'
```

**Response (200 OK):**
```json
{
  "answer": "Based on the vacation policy, employees are entitled to 20 days of annual vacation...",
  "sources": [
    {
      "filename": "company_handbook.pdf",
      "page": 12,
      "section": "Leave & Time Off",
      "snippet": "Vacation Policy: Employees get 20 days of annual vacation..."
    },
    {
      "filename": "hr_policies.pdf",
      "page": 5,
      "section": "Time Off Policies",
      "snippet": "PTO Request Form must be submitted at least 2 weeks in advance..."
    }
  ],
  "confidence_score": 0.92,
  "retrieval_time_ms": 245,
  "llm_time_ms": 67320
}
```

**Response Schema:**
```python
class Source(BaseModel):
    filename: str
    page: int
    section: str
    snippet: str

class AnswerWithSources(BaseModel):
    answer: str
    sources: List[Source]
    confidence_score: float  # 0.0-1.0
    retrieval_time_ms: int
    llm_time_ms: int
```

---

### Phase 2b: Streaming Responses

**Endpoint:** `POST /ask-stream`

**Description:** Get answer as stream (Server-Sent Events)

**Request:**
```bash
curl -X POST http://127.0.0.1:8000/ask-stream \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the vacation policy?"}' \
  -N  # -N to handle streaming
```

**Response (200 OK - Streaming):**
```
data: {"content": "Based"}
data: {"content": " on"}
data: {"content": " the"}
data: {"content": " vacation"}
data: {"content": " policy,"}
...
```

**JavaScript Client:**
```javascript
async function askWithStreaming() {
    const eventSource = new EventSource("http://127.0.0.1:8000/ask-stream");
    
    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log("Streamed content:", data.content);
        // Update UI with partial response
        updateChatDisplay(data.content);
    };
    
    eventSource.onerror = () => {
        eventSource.close();
        console.log("Stream completed");
    };
}
```

**Python Client:**
```python
import requests
import json

response = requests.post(
    "http://127.0.0.1:8000/ask-stream",
    json={"question": "What is the vacation policy?"},
    stream=True
)

for line in response.iter_lines():
    if line:
        try:
            data = json.loads(line[6:])  # Remove "data: " prefix
            print(data["content"], end="", flush=True)
        except json.JSONDecodeError:
            pass
```

**Benefits:**
- Progressive display (feels faster)
- Better UX (user sees response immediately)
- Reduced memory (no buffering)

---

### Phase 3: Authentication

**Endpoint:** `POST /login`

**Description:** Authenticate user and get JWT token

**Request:**
```bash
curl -X POST http://127.0.0.1:8000/login \
  -H "Content-Type: application/json" \
  -d '{"username": "john", "password": "password123", "role": "employee"}'
```

**Request Body:**
```json
{
  "username": "john",
  "password": "password123",
  "role": "employee"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400,
  "role": "employee"
}
```

**Error Responses:**

```json
// 401 Unauthorized - Invalid credentials
{
  "detail": "Invalid username or password"
}

// 422 Unprocessable Entity - Invalid role
{
  "detail": "Invalid role. Must be: employee, hr, or manager"
}
```

**Response Schema:**
```python
class LoginRequest(BaseModel):
    username: str
    password: str
    role: str  # "employee", "hr", "manager"

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    role: str
```

**Token Format (JWT):**
```
Header: {"alg": "HS256", "typ": "JWT"}
Payload: {
  "username": "john",
  "role": "employee",
  "exp": 1704067200,  # expiry timestamp
  "iat": 1703980800   # issued at timestamp
}
Signature: HMAC-SHA256(secret_key)
```

---

### Phase 3: Ask with Authentication

**Endpoint:** `POST /ask`

**Modified for Phase 3** - Now requires authentication

**Request:**
```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -d '{"question": "What is the vacation policy?"}'
```

**Response (200 OK):**
```json
{
  "answer": "Based on the vacation policy, employees..."
}
```

**Error Responses:**

```json
// 401 Unauthorized - Missing or invalid token
{
  "detail": "Not authenticated"
}

// 403 Forbidden - Token valid but user not authorized
{
  "detail": "User does not have permission to access this resource"
}
```

**Authorization Behavior:**
- Extract role from JWT token
- Load role-specific vector store
- Retrieve only documents for that role
- No cross-role data access

**Example Role Filtering:**
```
Employee asks: "What is the vacation policy?"
├─ Load: vectorstore/employee/
├─ Available docs: employee_handbook.pdf, benefits_guide.pdf
└─ Cannot access: hr_policies.pdf, manager_guide.pdf

HR asks: "What is the vacation policy?"
├─ Load: vectorstore/hr/
├─ Available docs: hr_policies.pdf, payroll_rules.pdf
└─ Cannot access: employee_handbook.pdf
```

---

### Phase 3: Logout

**Endpoint:** `POST /logout`

**Description:** Invalidate current session token

**Request:**
```bash
curl -X POST http://127.0.0.1:8000/logout \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response (200 OK):**
```json
{
  "message": "Successfully logged out"
}
```

**Implementation Note:** Can be simplified to frontend-only (delete token from localStorage)

---

### Phase 4: Analytics

**Endpoint:** `GET /analytics/queries`

**Description:** Get query statistics and analytics

**Request (with auth token):**
```bash
curl -X GET "http://127.0.0.1:8000/analytics/queries?days=7&role=employee" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Query Parameters:**
- `days` (optional, default 7): Number of days to analyze
- `role` (optional): Filter by role

**Response (200 OK):**
```json
{
  "total_queries": 234,
  "total_users": 45,
  "avg_response_time_ms": 75000,
  "top_questions": [
    {"question": "What is the vacation policy?", "count": 23},
    {"question": "How do I request time off?", "count": 18},
    {"question": "What are the benefits?", "count": 15}
  ],
  "average_confidence_score": 0.88,
  "retrieval_accuracy": 0.85
}
```

**Response Schema:**
```python
class QueryStats(BaseModel):
    total_queries: int
    total_users: int
    avg_response_time_ms: float
    top_questions: List[Dict[str, Union[str, int]]]
    average_confidence_score: float
    retrieval_accuracy: float
```

---

**Endpoint:** `GET /analytics/user-activity`

**Description:** Get per-user activity logs

**Request:**
```bash
curl -X GET "http://127.0.0.1:8000/analytics/user-activity?limit=100" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response (200 OK):**
```json
{
  "activity": [
    {
      "timestamp": "2024-04-18T10:30:45Z",
      "username": "john",
      "role": "employee",
      "question": "What is the vacation policy?",
      "response_length": 245,
      "confidence": 0.92,
      "response_time_ms": 67500
    },
    {
      "timestamp": "2024-04-18T10:25:30Z",
      "username": "alice",
      "role": "hr",
      "question": "How to onboard new employees?",
      "response_length": 312,
      "confidence": 0.95,
      "response_time_ms": 71200
    }
  ],
  "total_records": 234
}
```

---

### Phase 4: Document Management

**Endpoint:** `POST /documents/upload`

**Description:** Upload new PDF documents

**Request:**
```bash
curl -X POST http://127.0.0.1:8000/documents/upload \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -F "file=@new_policy.pdf" \
  -F "role=employee"
```

**Request Parameters:**
- `file` (required): PDF file
- `role` (required): "employee", "hr", or "manager"

**Response (200 OK):**
```json
{
  "message": "Document uploaded successfully",
  "filename": "new_policy.pdf",
  "role": "employee",
  "chunks_created": 42,
  "vectorstore_updated": true
}
```

---

**Endpoint:** `DELETE /documents/{document_id}`

**Description:** Remove document from knowledge base

**Request:**
```bash
curl -X DELETE http://127.0.0.1:8000/documents/new_policy.pdf \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response (200 OK):**
```json
{
  "message": "Document deleted successfully",
  "filename": "new_policy.pdf",
  "chunks_removed": 42
}
```

---

## Error Handling

### Standard Error Response Format

```json
{
  "detail": "Error description",
  "error_code": "ERR_001",
  "timestamp": "2024-04-18T10:30:45Z",
  "request_id": "req_abc123def456"
}
```

### HTTP Status Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| 200 | OK | Successful request |
| 201 | Created | Resource created |
| 400 | Bad Request | Invalid input format |
| 401 | Unauthorized | Missing/invalid auth token |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 422 | Unprocessable Entity | Validation error |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Backend error |
| 503 | Service Unavailable | LM Studio not running |

### Common Error Codes

```
ERR_001: Invalid question format
ERR_002: LM Studio connection failed
ERR_003: Vector store not found
ERR_004: Invalid authentication token
ERR_005: Unauthorized role access
ERR_006: Rate limit exceeded
ERR_007: Document processing failed
ERR_008: Database error
ERR_009: Unknown error
```

---

## CORS & Security

### CORS Headers (Current MVP)

```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, DELETE
Access-Control-Allow-Headers: Content-Type, Authorization
Access-Control-Allow-Credentials: true
```

### Security Considerations

**Phase 1 (Current):**
- ⚠️ No authentication
- ⚠️ CORS allows all origins
- ⚠️ No rate limiting
- ⚠️ No HTTPS

**Phase 3+:**
- ✅ JWT authentication required
- ✅ CORS restricted to allowed domains
- ✅ Rate limiting (10 req/min per user)
- ✅ HTTPS enforced
- ✅ Token expiration (24 hours)
- ✅ Role-based access control
- ✅ Audit logging

---

## Rate Limiting (Future)

### Limits (Planned for Phase 3)

```
Anonymous Users: 5 requests/minute
Authenticated Users: 100 requests/minute
Admin Users: Unlimited
```

### Rate Limit Headers

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 99
X-RateLimit-Reset: 1704067200
```

---

## Client Examples

### Python Client

```python
import requests
import json
from typing import Dict

class EnterpriseRAGClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.token = None
        self.role = None
    
    def login(self, username: str, password: str, role: str) -> str:
        """Login and store token"""
        response = requests.post(
            f"{self.base_url}/login",
            json={
                "username": username,
                "password": password,
                "role": role
            }
        )
        data = response.json()
        self.token = data["access_token"]
        self.role = data["role"]
        return self.token
    
    def ask(self, question: str) -> str:
        """Ask a question"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }
        response = requests.post(
            f"{self.base_url}/ask",
            json={"question": question},
            headers=headers
        )
        return response.json()["answer"]
    
    def ask_stream(self, question: str):
        """Ask with streaming"""
        headers = {
            "Authorization": f"Bearer {self.token}"
        }
        response = requests.post(
            f"{self.base_url}/ask-stream",
            json={"question": question},
            headers=headers,
            stream=True
        )
        
        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line[6:])
                    yield data["content"]
                except:
                    pass
    
    def get_analytics(self, days: int = 7) -> Dict:
        """Get analytics"""
        headers = {
            "Authorization": f"Bearer {self.token}"
        }
        response = requests.get(
            f"{self.base_url}/analytics/queries?days={days}",
            headers=headers
        )
        return response.json()

# Usage
if __name__ == "__main__":
    client = EnterpriseRAGClient()
    
    # Login
    token = client.login("john", "password123", "employee")
    print(f"Logged in: {token[:20]}...")
    
    # Ask question
    answer = client.ask("What is the vacation policy?")
    print(f"Answer: {answer}")
    
    # Stream
    print("Streaming response:")
    for chunk in client.ask_stream("How do I request time off?"):
        print(chunk, end="", flush=True)
    print()
    
    # Analytics
    stats = client.get_analytics(days=7)
    print(f"Stats: {stats}")
```

---

### JavaScript/Fetch Client

```javascript
class EnterpriseRAGClient {
    constructor(baseUrl = "http://127.0.0.1:8000") {
        this.baseUrl = baseUrl;
        this.token = null;
        this.role = null;
    }
    
    async login(username, password, role) {
        const response = await fetch(`${this.baseUrl}/login`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({username, password, role})
        });
        const data = await response.json();
        this.token = data.access_token;
        this.role = data.role;
        localStorage.setItem("token", this.token);
        return this.token;
    }
    
    async ask(question) {
        const response = await fetch(`${this.baseUrl}/ask`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${this.token}`
            },
            body: JSON.stringify({question})
        });
        const data = await response.json();
        return data.answer;
    }
    
    streamQuestion(question, onChunk, onComplete) {
        const eventSource = new EventSource(
            `${this.baseUrl}/ask-stream`
        );
        
        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            onChunk(data.content);
        };
        
        eventSource.onerror = () => {
            eventSource.close();
            onComplete();
        };
    }
    
    async getAnalytics(days = 7) {
        const response = await fetch(
            `${this.baseUrl}/analytics/queries?days=${days}`,
            {
                headers: {
                    "Authorization": `Bearer ${this.token}`
                }
            }
        );
        return await response.json();
    }
}

// Usage
const client = new EnterpriseRAGClient();

async function main() {
    // Login
    await client.login("john", "password123", "employee");
    console.log("Logged in");
    
    // Ask question
    const answer = await client.ask("What is the vacation policy?");
    console.log("Answer:", answer);
    
    // Stream
    client.streamQuestion(
        "How do I request time off?",
        (chunk) => console.log(chunk),
        () => console.log("Stream complete")
    );
}

main();
```

---

## Pagination & Filtering (Future)

### Pagination Example

```
GET /analytics/queries?page=1&limit=20
```

Response includes:
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 234,
    "pages": 12
  }
}
```

---

## Versioning Strategy

**Current:** v1.0 (implicit, no version in URL)

**Future versioning:**
```
GET /v2/ask          # API version 2
GET /v1/ask          # API version 1 (legacy)
```

---

## API Documentation

### Generate OpenAPI/Swagger Docs

FastAPI automatically generates interactive docs:

```
Swagger UI: http://127.0.0.1:8000/docs
ReDoc: http://127.0.0.1:8000/redoc
OpenAPI JSON: http://127.0.0.1:8000/openapi.json
```

---

**API Version:** 1.0  
**Last Updated:** 2024-04  
**Status:** MVP Phase 1
