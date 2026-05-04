
import os
import json
import logging
import time
from typing import List, Dict, Optional, Tuple
import requests
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================
LM_STUDIO_API = "http://127.0.0.1:1234/v1/chat/completions"
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
FAISS_PATH = "../vectorstore"
CHUNK_SIZE = 600
CHUNK_OVERLAP = 150
RETRIEVAL_K = 3  # Optimized: can adjust to 1-5
TEMPERATURE = 0.1
MAX_TOKENS = 500
REQUEST_TIMEOUT = 120

# Load embedding model
embedding_model = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)

# Load FAISS vector database
vector_db = FAISS.load_local(
    FAISS_PATH,
    embedding_model,
    allow_dangerous_deserialization=True
)

retriever = vector_db.as_retriever(search_kwargs={"k": RETRIEVAL_K})


# ==================== PHASE 2A: SOURCE CITATIONS ====================

class DocumentSource:
    """Source citation structure"""
    def __init__(self, filename: str, page: int, snippet: str):
        self.filename = filename
        self.page = page
        self.snippet = snippet
    
    def to_dict(self):
        return {
            "filename": self.filename,
            "page": self.page,
            "snippet": self.snippet
        }


def extract_sources(docs) -> List[Dict]:
    """Extract source information from retrieved documents"""
    sources = []
    for doc in docs:
        source_dict = {
            "filename": doc.metadata.get("source", "Unknown"),
            "page": doc.metadata.get("page", 0),
            "snippet": doc.page_content[:150] + "..." if len(doc.page_content) > 150 else doc.page_content
        }
        sources.append(source_dict)
    return sources


def calculate_confidence(docs) -> float:
    """Calculate confidence score based on retrieval similarity"""
    if not docs:
        return 0.0
    # Return average similarity (placeholder: 0.85 baseline)
    return min(0.95, 0.85 + (len(docs) * 0.02))


# ==================== PHASE 1: OPTIMIZED RETRIEVAL ====================

def ask_question(question: str, role: str = None) -> Dict:
    """
    Ask a question and get answer with sources and metrics.
    
    Args:
        question: User question
        role: Optional role filter (employee, hr, manager)
    
    Returns:
        Dict with answer, sources, confidence, and timing
    """
    start_time = time.time()
    retrieval_start = time.time()
    
    logger.info(f"Question: {question} | Role: {role}")
    
    try:
        # Step 1: Retrieve relevant docs
        docs = retriever.invoke(question)
        retrieval_time = time.time() - retrieval_start
        
        if not docs:
            return {
                "answer": "No relevant information found in the documents.",
                "sources": [],
                "confidence": 0.0,
                "retrieval_time_ms": int(retrieval_time * 1000),
                "llm_time_ms": 0,
                "total_time_ms": int((time.time() - start_time) * 1000)
            }
        
        logger.info(f"Retrieved {len(docs)} documents in {retrieval_time:.2f}s")
        
        # Step 2: Extract sources (Phase 2a)
        sources = extract_sources(docs)
        
        # Step 3: Build context
        context = "\n\n".join([doc.page_content for doc in docs])
        
        # Step 4: Format prompt
        prompt = f"""You are an enterprise knowledge assistant.

Use ONLY the information from the context below.

Rules:
- Do NOT invent information.
- If the answer is not present in the context say:
"The information is not available in the provided documents."
- Be concise and direct.

Context:
{context}

Question:
{question}

Answer:"""
        
        # Step 5: Call LM Studio
        llm_start = time.time()
        response = requests.post(
            LM_STUDIO_API,
            json={
                "model": "mistral-7b-instruct-v0.2@q4_0",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": TEMPERATURE,
                "max_tokens": MAX_TOKENS
            },
            timeout=REQUEST_TIMEOUT
        )

        llm_time = time.time() - llm_start
        logger.info(f"LLM response in {llm_time:.2f}s")
        
        data = response.json()
        
        if "choices" in data and len(data["choices"]) > 0:
            answer = data["choices"][0]["message"]["content"].strip()
        else:
            answer = "The AI model returned an unexpected response."
        
        total_time = time.time() - start_time
        
        return {
            "answer": answer,
            "sources": sources,
            "confidence": calculate_confidence(docs),
            "retrieval_time_ms": int(retrieval_time * 1000),
            "llm_time_ms": int(llm_time * 1000),
            "total_time_ms": int(total_time * 1000),
            "timestamp": datetime.now().isoformat()
        }
    
    except requests.exceptions.ConnectionError:
        logger.error("Cannot connect to LM Studio API")
        return {
            "answer": "Error connecting to AI server.",
            "sources": [],
            "confidence": 0.0,
            "retrieval_time_ms": 0,
            "llm_time_ms": 0,
            "total_time_ms": int((time.time() - start_time) * 1000),
            "error": "LM_STUDIO_CONNECTION_FAILED"
        }
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return {
            "answer": "Error communicating with the AI model.",
            "sources": [],
            "confidence": 0.0,
            "retrieval_time_ms": 0,
            "llm_time_ms": 0,
            "total_time_ms": int((time.time() - start_time) * 1000),
            "error": str(e)
        }


# ==================== PHASE 2B: STREAMING RESPONSES ====================

def ask_question_stream(question: str, role: str = "employee"):
    """
    Generate streaming response for a question.
    Yields chunks of response as they're generated.

    Args:
        question: User question
        role: Role filter — retrieves only documents the role is allowed to see

    Yields:
        JSON strings with content chunks
    """
    logger.info(f"Streaming question: {question} | Role: {role}")

    try:
        # Use role-specific retriever so each role only searches its own documents
        role_retriever = get_role_specific_retriever(role)
        docs = role_retriever.invoke(question)
        
        if not docs:
            yield json.dumps({"content": "No relevant information found in the documents."})
            return
        
        context = "\n\n".join([doc.page_content for doc in docs])
        
        # Yield sources first
        sources = extract_sources(docs)
        yield json.dumps({"type": "sources", "sources": sources})
        
        # Format prompt
        prompt = f"""You are an enterprise knowledge assistant.

Use ONLY the information from the context below.

Context:
{context}

Question:
{question}

Answer:"""
        
        # Stream from LM Studio
        response = requests.post(
            LM_STUDIO_API,
            json={
                "model": "mistral-7b-instruct-v0.2@q4_0",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": TEMPERATURE,
                "max_tokens": MAX_TOKENS,
                "stream": True
            },
            stream=True,
            timeout=REQUEST_TIMEOUT
        )
        
        for line in response.iter_lines():
            if line:
                try:
                    line_str = line.decode("utf-8") if isinstance(line, bytes) else line
                    if line_str.startswith("data: "):
                        line_str = line_str[6:]
                    if line_str.strip() == "[DONE]":
                        break
                    chunk = json.loads(line_str)
                    if "choices" in chunk and len(chunk["choices"]) > 0:
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield json.dumps({"type": "content", "content": content})
                except json.JSONDecodeError:
                    pass
    
    except Exception as e:
        logger.error(f"Streaming error: {e}")
        yield json.dumps({"type": "error", "error": str(e)})


# ==================== PHASE 3: ROLE-BASED RETRIEVAL ====================

def get_role_specific_retriever(role: str):
    """
    Load role-specific vector store.
    
    Args:
        role: "employee", "hr", or "manager"
    
    Returns:
        Retriever for that role
    """
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


def ask_question_with_role(question: str, role: str = "employee") -> Dict:
    """Ask question with role-based document filtering"""
    role_retriever = get_role_specific_retriever(role)
    
    start_time = time.time()
    
    try:
        docs = role_retriever.invoke(question)
        
        if not docs:
            return {
                "answer": "No relevant information found in the documents.",
                "sources": [],
                "confidence": 0.0,
                "role": role
            }
        
        sources = extract_sources(docs)
        context = "\n\n".join([doc.page_content for doc in docs])
        
        prompt = f"""You are an enterprise knowledge assistant.

Use ONLY the information from the context below.

Context:
{context}

Question:
{question}

Answer:"""
        
        llm_start = time.time()
        response = requests.post(
            LM_STUDIO_API,
            json={
                "model": "mistral-7b-instruct-v0.2@q4_0",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": TEMPERATURE,
                "max_tokens": MAX_TOKENS
            },
            timeout=REQUEST_TIMEOUT
        )

        data = response.json()
        answer = data["choices"][0]["message"]["content"].strip() if data.get("choices") else "Error"
        
        return {
            "answer": answer,
            "sources": sources,
            "confidence": calculate_confidence(docs),
            "role": role,
            "total_time_ms": int((time.time() - start_time) * 1000)
        }
    
    except Exception as e:
        logger.error(f"Error in role-based retrieval: {e}")
        return {
            "answer": "Error processing your question.",
            "sources": [],
            "confidence": 0.0,
            "role": role,
            "error": str(e)
        }