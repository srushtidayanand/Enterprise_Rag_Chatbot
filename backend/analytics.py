"""
Analytics Module - Query tracking and statistics
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import defaultdict, Counter
import json

# In-memory query log (use real DB in production)
QUERY_LOG = []


class QueryRecord:
    def __init__(self, username: str, role: str, question: str, answer: str, 
                 confidence: float, response_time_ms: int, sources_count: int):
        self.timestamp = datetime.now()
        self.username = username
        self.role = role
        self.question = question
        self.answer = answer
        self.confidence = confidence
        self.response_time_ms = response_time_ms
        self.sources_count = sources_count
    
    def to_dict(self):
        return {
            "timestamp": self.timestamp.isoformat(),
            "username": self.username,
            "role": self.role,
            "question": self.question,
            "answer_length": len(self.answer),
            "confidence": self.confidence,
            "response_time_ms": self.response_time_ms,
            "sources_count": self.sources_count
        }


def log_query(username: str, role: str, question: str, answer: str, 
              confidence: float, response_time_ms: int, sources_count: int = 0):
    """Log a query for analytics"""
    record = QueryRecord(username, role, question, answer, confidence, response_time_ms, sources_count)
    QUERY_LOG.append(record)


def get_query_stats(days: int = 7, role: Optional[str] = None) -> Dict:
    """Get query statistics for a period"""
    cutoff_time = datetime.now() - timedelta(days=days)
    
    # Filter by date
    filtered_logs = [log for log in QUERY_LOG if log.timestamp >= cutoff_time]
    
    # Filter by role if provided
    if role:
        filtered_logs = [log for log in filtered_logs if log.role == role]
    
    if not filtered_logs:
        return {
            "total_queries": 0,
            "total_users": 0,
            "avg_response_time_ms": 0,
            "top_questions": [],
            "average_confidence_score": 0,
            "by_role": {},
            "period_days": days
        }
    
    # Calculate statistics
    total_queries = len(filtered_logs)
    unique_users = len(set(log.username for log in filtered_logs))
    avg_response_time = sum(log.response_time_ms for log in filtered_logs) / total_queries
    avg_confidence = sum(log.confidence for log in filtered_logs) / total_queries
    
    # Top questions
    question_counts = Counter(log.question for log in filtered_logs)
    top_questions = [
        {"question": q, "count": c} 
        for q, c in question_counts.most_common(10)
    ]
    
    # By role
    by_role = defaultdict(lambda: {"queries": 0, "avg_time_ms": 0, "avg_confidence": 0})
    role_times = defaultdict(list)
    role_confidences = defaultdict(list)
    
    for log in filtered_logs:
        by_role[log.role]["queries"] += 1
        role_times[log.role].append(log.response_time_ms)
        role_confidences[log.role].append(log.confidence)
    
    for role_key in by_role:
        if role_times[role_key]:
            by_role[role_key]["avg_time_ms"] = sum(role_times[role_key]) / len(role_times[role_key])
        if role_confidences[role_key]:
            by_role[role_key]["avg_confidence"] = sum(role_confidences[role_key]) / len(role_confidences[role_key])
    
    return {
        "total_queries": total_queries,
        "total_users": unique_users,
        "avg_response_time_ms": round(avg_response_time, 2),
        "top_questions": top_questions,
        "average_confidence_score": round(avg_confidence, 3),
        "by_role": dict(by_role),
        "period_days": days
    }


def get_user_activity(username: Optional[str] = None, limit: int = 100) -> List[Dict]:
    """Get user activity logs"""
    logs = QUERY_LOG[-limit:] if len(QUERY_LOG) > limit else QUERY_LOG
    
    if username:
        logs = [log for log in logs if log.username == username]
    
    return [log.to_dict() for log in reversed(logs)]  # Most recent first


def get_role_stats(role: str) -> Dict:
    """Get statistics for a specific role"""
    role_logs = [log for log in QUERY_LOG if log.role == role]
    
    if not role_logs:
        return {
            "role": role,
            "total_queries": 0,
            "users": 0,
            "avg_response_time_ms": 0,
            "avg_confidence": 0
        }
    
    return {
        "role": role,
        "total_queries": len(role_logs),
        "users": len(set(log.username for log in role_logs)),
        "avg_response_time_ms": round(sum(log.response_time_ms for log in role_logs) / len(role_logs), 2),
        "avg_confidence": round(sum(log.confidence for log in role_logs) / len(role_logs), 3),
        "most_asked": Counter(log.question for log in role_logs).most_common(5)
    }


def get_performance_metrics() -> Dict:
    """Get system performance metrics"""
    if not QUERY_LOG:
        return {
            "total_queries": 0,
            "avg_response_time_ms": 0,
            "min_response_time_ms": 0,
            "max_response_time_ms": 0,
            "avg_confidence": 0
        }
    
    response_times = [log.response_time_ms for log in QUERY_LOG]
    confidences = [log.confidence for log in QUERY_LOG]
    
    return {
        "total_queries": len(QUERY_LOG),
        "avg_response_time_ms": round(sum(response_times) / len(response_times), 2),
        "min_response_time_ms": min(response_times),
        "max_response_time_ms": max(response_times),
        "avg_confidence": round(sum(confidences) / len(confidences), 3),
        "records_stored": len(QUERY_LOG)
    }


def clear_old_logs(days: int = 30):
    """Clear logs older than specified days"""
    global QUERY_LOG
    cutoff_time = datetime.now() - timedelta(days=days)
    QUERY_LOG = [log for log in QUERY_LOG if log.timestamp >= cutoff_time]
