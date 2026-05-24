import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from collections import Counter
from database import get_session, QueryLog, ChatHistory


def log_query(username, role, question, answer, confidence, response_time_ms, sources_count=0) -> int:
    with get_session() as session:
        log = QueryLog(
            username=username, role=role, question=question, answer=answer,
            confidence=confidence, response_time_ms=response_time_ms, sources_count=sources_count
        )
        session.add(log)
        session.flush()
        return log.id


def log_chat(username, role, question, answer, sources, confidence, response_time_ms):
    with get_session() as session:
        session.add(ChatHistory(
            username=username, role=role, question=question, answer=answer,
            sources=json.dumps(sources), confidence=confidence, response_time_ms=response_time_ms
        ))


def submit_feedback(query_id: int, feedback: int):
    with get_session() as session:
        log = session.query(QueryLog).filter_by(id=query_id).first()
        if log:
            log.feedback = feedback


def get_query_stats(days: int = 7, role: Optional[str] = None) -> Dict:
    cutoff = datetime.now() - timedelta(days=days)
    with get_session() as session:
        q = session.query(QueryLog).filter(QueryLog.timestamp >= cutoff)
        if role:
            q = q.filter(QueryLog.role == role)
        rows = q.all()

    if not rows:
        return {"total_queries": 0, "total_users": 0, "avg_response_time_ms": 0,
                "top_questions": [], "average_confidence_score": 0, "by_role": {}, "period_days": days}

    total = len(rows)
    top_questions = [{"question": q, "count": c}
                     for q, c in Counter(r.question for r in rows).most_common(10)]
    by_role: Dict = {}
    for r in rows:
        if r.role not in by_role:
            by_role[r.role] = {"queries": 0, "times": [], "confidences": []}
        by_role[r.role]["queries"] += 1
        by_role[r.role]["times"].append(r.response_time_ms)
        by_role[r.role]["confidences"].append(r.confidence)

    for rl in by_role:
        t, cf = by_role[rl]["times"], by_role[rl]["confidences"]
        by_role[rl] = {"queries": by_role[rl]["queries"],
                       "avg_time_ms": round(sum(t) / len(t), 2) if t else 0,
                       "avg_confidence": round(sum(cf) / len(cf), 3) if cf else 0}

    return {
        "total_queries": total,
        "total_users": len(set(r.username for r in rows)),
        "avg_response_time_ms": round(sum(r.response_time_ms for r in rows) / total, 2),
        "top_questions": top_questions,
        "average_confidence_score": round(sum(r.confidence for r in rows) / total, 3),
        "by_role": by_role,
        "period_days": days,
    }


def get_user_activity(username: Optional[str] = None, limit: int = 100) -> List[Dict]:
    with get_session() as session:
        q = session.query(QueryLog).order_by(QueryLog.timestamp.desc())
        if username:
            q = q.filter(QueryLog.username == username)
        rows = q.limit(limit).all()
    return [{"id": r.id, "username": r.username, "role": r.role, "question": r.question,
             "answer": r.answer, "confidence": r.confidence, "response_time_ms": r.response_time_ms,
             "sources_count": r.sources_count, "feedback": r.feedback, "timestamp": str(r.timestamp)}
            for r in rows]


def get_chat_history(username: str, limit: int = 50) -> List[Dict]:
    with get_session() as session:
        rows = session.query(ChatHistory).filter(
            ChatHistory.username == username
        ).order_by(ChatHistory.timestamp.desc()).limit(limit).all()
    return [{"id": r.id, "question": r.question, "answer": r.answer,
             "sources": json.loads(r.sources) if r.sources else [],
             "confidence": r.confidence, "response_time_ms": r.response_time_ms,
             "timestamp": str(r.timestamp)} for r in rows]


def get_evaluation_metrics() -> Dict:
    with get_session() as session:
        rows = session.query(QueryLog).all()

    if not rows:
        return {"total_queries": 0, "avg_confidence": 0, "answer_rate": 0, "feedback_score": 0,
                "avg_response_time_ms": 0,
                "confidence_distribution": {"high": 0, "medium": 0, "low": 0},
                "queries_by_role": {}, "thumbs_up": 0, "thumbs_down": 0}

    total = len(rows)
    fb = [r for r in rows if r.feedback is not None]
    thumbs_up = sum(1 for r in fb if r.feedback == 1)
    answered = sum(1 for r in rows if r.answer and len(r.answer) > 30
                   and "not available" not in r.answer.lower()
                   and "don't have information" not in r.answer.lower())
    roles: Dict = {}
    for r in rows:
        roles[r.role] = roles.get(r.role, 0) + 1

    return {
        "total_queries": total,
        "avg_confidence": round(sum(r.confidence for r in rows) / total, 3),
        "answer_rate": round(answered / total, 3),
        "feedback_score": round(thumbs_up / len(fb), 3) if fb else 0,
        "avg_response_time_ms": round(sum(r.response_time_ms for r in rows) / total, 2),
        "confidence_distribution": {
            "high":   sum(1 for r in rows if r.confidence >= 0.75),
            "medium": sum(1 for r in rows if 0.5 <= r.confidence < 0.75),
            "low":    sum(1 for r in rows if r.confidence < 0.5),
        },
        "queries_by_role": roles,
        "thumbs_up": thumbs_up,
        "thumbs_down": sum(1 for r in fb if r.feedback == -1),
    }


def get_performance_metrics() -> Dict:
    with get_session() as session:
        rows = session.query(QueryLog.response_time_ms, QueryLog.confidence).all()

    if not rows:
        return {"total_queries": 0, "avg_response_time_ms": 0, "min_response_time_ms": 0,
                "max_response_time_ms": 0, "avg_confidence": 0, "records_stored": 0}

    times = [r.response_time_ms for r in rows]
    confs = [r.confidence for r in rows]
    sorted_times = sorted(times)
    p95_idx = max(0, int(len(sorted_times) * 0.95) - 1)

    return {
        "total_queries": len(rows),
        "avg_response_time_ms": round(sum(times) / len(times), 2),
        "min_response_time_ms": min(times),
        "max_response_time_ms": max(times),
        "p95_response_time_ms": sorted_times[p95_idx],
        "avg_confidence": round(sum(confs) / len(confs), 3),
        "records_stored": len(rows),
    }
