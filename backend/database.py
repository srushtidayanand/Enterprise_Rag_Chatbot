import os
import bcrypt
from contextlib import contextmanager
from pathlib import Path
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func
from sqlalchemy.engine import URL as _URL

# Load .env file
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

DB_HOST     = os.environ["DB_HOST"]
DB_PORT     = int(os.environ.get("DB_PORT", 5432))
DB_USER     = os.environ["DB_USER"]
DB_PASSWORD = os.environ["DB_PASSWORD"]
DB_NAME     = os.environ["DB_NAME"]

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    username = Column(String(100), primary_key=True)
    password_hash = Column(String(256), nullable=False)
    role = Column(String(50), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    is_active = Column(Integer, default=1)
    failed_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)


class TokenBlacklist(Base):
    __tablename__ = "token_blacklist"
    token = Column(Text, primary_key=True)
    created_at = Column(DateTime, server_default=func.now())


class QueryLog(Base):
    __tablename__ = "query_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), nullable=False)
    role = Column(String(50), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text)
    confidence = Column(Float, default=0.0)
    response_time_ms = Column(Integer, default=0)
    sources_count = Column(Integer, default=0)
    feedback = Column(Integer, nullable=True)
    timestamp = Column(DateTime, server_default=func.now())


class ChatHistory(Base):
    __tablename__ = "chat_history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), nullable=False)
    role = Column(String(50), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text)
    sources = Column(Text)
    confidence = Column(Float, default=0.0)
    response_time_ms = Column(Integer, default=0)
    timestamp = Column(DateTime, server_default=func.now())


_conn_url = _URL.create(
    drivername="postgresql+psycopg2",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME,
)
engine = create_engine(_conn_url, pool_pre_ping=True, connect_args={"sslmode": "require"})
print(f"[DB] Connected to Neon PostgreSQL at {DB_HOST}")

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_hash(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def init_db():
    Base.metadata.create_all(engine)
    with get_session() as session:
        for username, password, role in [
            ("john",  "John@1234",  "employee"),
            ("alice", "Alice@1234", "hr"),
            ("bob",   "Bob@1234",   "manager"),
            ("admin", "Admin@1234", "admin"),
        ]:
            if not session.query(User).filter_by(username=username).first():
                session.add(User(username=username, password_hash=_hash(password), role=role))


init_db()
