"""
app/repositories/database.py

Database engine, session factory, declarative base, and FastAPI dependency.
All SQLAlchemy setup lives here; no other module creates engines or sessions.
Supports portable local SQLite (with WAL mode & BEGIN IMMEDIATE concurrency)
and production PostgreSQL (with robust connection pooling & pool_pre_ping).
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session
from app.core.config import settings


# ── Engine Configuration ──────────────────────────────────────────────────────
_connect_args = {}
_engine_kwargs = {"echo": False}

if settings.DATABASE_URL.startswith("sqlite"):
    # SQLite threading requirement for FastAPI
    _connect_args["check_same_thread"] = False
    _connect_args["timeout"] = 30.0  # 30s busy timeout for concurrent threads
    _engine_kwargs["connect_args"] = _connect_args

elif settings.DATABASE_URL.startswith("postgresql"):
    # Production PostgreSQL connection pool settings
    _engine_kwargs["pool_size"] = 10
    _engine_kwargs["max_overflow"] = 20
    _engine_kwargs["pool_pre_ping"] = True  # Automatically reconnect dead connections
    _engine_kwargs["pool_recycle"] = 1800   # Recycle connections after 30 minutes

engine = create_engine(settings.DATABASE_URL, **_engine_kwargs)


# ── SQLite Specific Concurrency Hooks ─────────────────────────────────────────
if settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=30000")  # 30 second timeout
        cursor.close()

    @event.listens_for(engine, "begin")
    def _sqlite_do_begin(conn):
        # Prevent concurrent read-before-write race conditions in SQLite
        conn.exec_driver_sql("BEGIN IMMEDIATE")


# ── Session factory ───────────────────────────────────────────────────────────
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


# ── Declarative base ──────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── FastAPI dependency ────────────────────────────────────────────────────────
def get_db():
    """
    Yield a database session for a single request, then close it.
    Use as a FastAPI dependency: db: Session = Depends(get_db)
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
