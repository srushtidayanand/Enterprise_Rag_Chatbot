
import os
import json
import logging
import time
from typing import List, Dict, Optional
import requests
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================
LM_STUDIO_API = "http://127.0.0.1:1234/v1/chat/completions"
LM_MODEL = "mistral-7b-instruct-v0.2@q4_0"
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
FAISS_PATH = "../vectorstore"
RETRIEVAL_K = 3
TEMPERATURE = 0.1
MAX_TOKENS = 500
REQUEST_TIMEOUT = 120

# Load embedding model
embedding_model = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)

# Load FAISS vector database (may not exist if ingest hasn't been run yet)
try:
    vector_db = FAISS.load_local(
        FAISS_PATH,
        embedding_model,
        allow_dangerous_deserialization=True
    )
    retriever = vector_db.as_retriever(search_kwargs={"k": RETRIEVAL_K})
    logger.info("Default vectorstore loaded")
except Exception as e:
    logger.warning(f"Could not load default vectorstore: {e}. Run ingest_documents.py first.")
    vector_db = None
    retriever = None


# ==================== SOURCE CITATIONS ====================

def _doc_url_from_path(filepath: str) -> str:
    normalized = filepath.replace("\\", "/")
    if "/data/" in normalized:
        return normalized.split("/data/")[-1]
    return os.path.basename(normalized)


def extract_sources(docs) -> List[Dict]:
    sources = []
    for doc in docs:
        raw_path = doc.metadata.get("source", "Unknown")
        sources.append({
            "filename": os.path.basename(raw_path),
            "page": doc.metadata.get("page", 0),
            "snippet": doc.page_content[:150] + "..." if len(doc.page_content) > 150 else doc.page_content,
            "doc_url": _doc_url_from_path(raw_path),
        })
    return sources


def calculate_confidence(docs) -> float:
    if not docs:
        return 0.0
    return min(0.95, 0.85 + (len(docs) * 0.02))


# ==================== STRICT PROMPT BUILDER ====================

ROLE_LABELS = {
    "employee": "Employee",
    "hr": "HR Manager",
    "manager": "Department Manager",
    "admin": "Administrator",
}


def build_strict_prompt(question: str, context: str, role: str) -> str:
    role_label = ROLE_LABELS.get(role, role.title())
    return f"""You are a strict enterprise knowledge assistant helping a {role_label}.

RULES — follow exactly:
1. Answer ONLY using information from the Context below.
2. Do NOT use any outside knowledge or make assumptions.
3. If the answer is not clearly present in the Context, respond with exactly:
   "I don't have information about this in the available documents. Please contact HR directly."
4. Be concise, factual, and direct. No creativity or elaboration beyond what the documents state.
5. Never invent numbers, dates, names, or policies.

Context:
{context}

Question: {question}

Answer:"""


# ==================== ROLE-BASED RETRIEVAL ====================

def get_role_specific_retriever(role: str):
    try:
        vectorstore_path = f"../vectorstore/{role}"
        if not os.path.exists(vectorstore_path):
            logger.warning(f"Role store {role} not found, using default")
            return retriever
        role_db = FAISS.load_local(
            vectorstore_path,
            embedding_model,
            allow_dangerous_deserialization=True
        )
        return role_db.as_retriever(search_kwargs={"k": RETRIEVAL_K})
    except Exception as e:
        logger.error(f"Error loading role store {role}: {e}")
        return retriever


def _no_vectorstore_response(start_time: float, role: str) -> Dict:
    return {
        "answer": "The document index has not been built yet. Please run ingest_documents.py first.",
        "sources": [],
        "confidence": 0.0,
        "role": role,
        "retrieval_time_ms": 0,
        "llm_time_ms": 0,
        "total_time_ms": int((time.time() - start_time) * 1000),
    }


# ==================== MAIN ASK (non-streaming) ====================

def ask_question_with_role(question: str, role: str = "employee") -> Dict:
    start_time = time.time()
    if retriever is None:
        return _no_vectorstore_response(start_time, role)
    role_retriever = get_role_specific_retriever(role)

    try:
        retrieval_start = time.time()
        docs = role_retriever.invoke(question)
        retrieval_time = time.time() - retrieval_start

        if not docs:
            return {
                "answer": "I don't have information about this in the available documents. Please contact HR directly.",
                "sources": [],
                "confidence": 0.0,
                "role": role,
                "retrieval_time_ms": int(retrieval_time * 1000),
                "llm_time_ms": 0,
                "total_time_ms": int((time.time() - start_time) * 1000),
            }

        sources = extract_sources(docs)
        context = "\n\n".join([doc.page_content for doc in docs])
        prompt = build_strict_prompt(question, context, role)

        llm_start = time.time()
        response = requests.post(
            LM_STUDIO_API,
            json={
                "model": LM_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": TEMPERATURE,
                "max_tokens": MAX_TOKENS,
            },
            timeout=REQUEST_TIMEOUT,
        )
        llm_time = time.time() - llm_start

        data = response.json()
        answer = (
            data["choices"][0]["message"]["content"].strip()
            if data.get("choices")
            else "The AI model returned an unexpected response."
        )

        return {
            "answer": answer,
            "sources": sources,
            "confidence": calculate_confidence(docs),
            "role": role,
            "retrieval_time_ms": int(retrieval_time * 1000),
            "llm_time_ms": int(llm_time * 1000),
            "total_time_ms": int((time.time() - start_time) * 1000),
            "timestamp": datetime.now().isoformat(),
        }

    except requests.exceptions.ConnectionError:
        logger.error("Cannot connect to LM Studio API")
        return {
            "answer": "Error connecting to AI server. Is LM Studio running?",
            "sources": [],
            "confidence": 0.0,
            "role": role,
            "retrieval_time_ms": 0,
            "llm_time_ms": 0,
            "total_time_ms": int((time.time() - start_time) * 1000),
            "error": "LM_STUDIO_CONNECTION_FAILED",
        }
    except Exception as e:
        logger.error(f"Error: {e}")
        return {
            "answer": "An error occurred while processing your question.",
            "sources": [],
            "confidence": 0.0,
            "role": role,
            "retrieval_time_ms": 0,
            "llm_time_ms": 0,
            "total_time_ms": int((time.time() - start_time) * 1000),
            "error": str(e),
        }


# ==================== STREAMING ASK ====================

def ask_question_stream(question: str, role: str = "employee"):
    logger.info(f"Streaming question: {question} | Role: {role}")

    if retriever is None:
        yield json.dumps({"type": "content", "content": "The document index has not been built yet. Please run ingest_documents.py first."})
        return

    try:
        role_retriever = get_role_specific_retriever(role)
        docs = role_retriever.invoke(question)

        if not docs:
            yield json.dumps({"type": "content", "content": "I don't have information about this in the available documents. Please contact HR directly."})
            return

        sources = extract_sources(docs)
        yield json.dumps({"type": "sources", "sources": sources})

        context = "\n\n".join([doc.page_content for doc in docs])
        prompt = build_strict_prompt(question, context, role)

        response = requests.post(
            LM_STUDIO_API,
            json={
                "model": LM_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": TEMPERATURE,
                "max_tokens": MAX_TOKENS,
                "stream": True,
            },
            stream=True,
            timeout=REQUEST_TIMEOUT,
        )

        confidence = calculate_confidence(docs)
        yield json.dumps({"type": "confidence", "confidence": confidence})

        for line in response.iter_lines():
            if line:
                line_str = line.decode("utf-8") if isinstance(line, bytes) else line
                if line_str.startswith("data: "):
                    line_str = line_str[6:]
                if line_str.strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(line_str)
                    if chunk.get("choices"):
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield json.dumps({"type": "content", "content": content})
                except json.JSONDecodeError:
                    pass

    except Exception as e:
        logger.error(f"Streaming error: {e}")
        yield json.dumps({"type": "error", "error": str(e)})


# ==================== SUGGESTIONS ====================

ROLE_TOPICS = {
    "employee": "attendance policy, leave policy, work from home rules, code of conduct",
    "hr": "recruitment process, payroll policy, selection criteria, hiring procedures",
    "manager": "performance review process, promotion criteria, employee evaluation",
    "admin": "all company policies, user management, system analytics",
}


def generate_suggestions(question: str, role: str) -> Dict:
    topics = ROLE_TOPICS.get(role, "company policies")
    prompt = (
        f'A user asked: "{question}"\n'
        f"They have access to documents about: {topics}\n\n"
        f"Suggest exactly 3 short follow-up questions they might ask next.\n"
        f"Output format (one line only): Question one? | Question two? | Question three?"
    )
    try:
        resp = requests.post(
            LM_STUDIO_API,
            json={
                "model": LM_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 120,
            },
            timeout=25,
        )
        text = resp.json()["choices"][0]["message"]["content"].strip()
        raw = [s.strip() for s in text.split("|") if s.strip()]
        suggestions = [s if s.endswith("?") else s + "?" for s in raw][:3]
        return {"suggestions": suggestions}
    except Exception:
        return {"suggestions": []}


# ==================== LEGACY (kept for compatibility) ====================

def ask_question(question: str, role: str = None) -> Dict:
    return ask_question_with_role(question, role or "employee")
