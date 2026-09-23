"""
app/repositories/database.py

Database engine, session factory, declarative base, and FastAPI dependency.
All SQLAlchemy setup lives here; no other module creates engines or sessions.
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session
from app.core.config import settings


# ── Engine ────────────────────────────────────────────────────────────────────
# SQLite requires check_same_thread=False when used with FastAPI's threading model.
# PostgreSQL does not need this argument; it is safely ignored via connect_args.
_connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    _connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=_connect_args,
    # Echo SQL to stdout in development — remove or set to False for production.
    echo=False,
)

# Enable WAL mode for SQLite so reads don't block writes during concurrent access.
if settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# ── Session factory ───────────────────────────────────────────────────────────
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


# ── Declarative base ──────────────────────────────────────────────────────────
# All ORM models inherit from this Base.
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
