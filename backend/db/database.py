from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from pathlib import Path
from backend.core.config import settings
from backend.db.models import Base

# Absolute path so the DB is always found regardless of CWD at startup
_DATA_DIR = Path(__file__).parent.parent.parent / "data"
_DATA_DIR.mkdir(exist_ok=True)

# Use posix-style slashes so SQLite URL works on both Windows and Unix
_db_url = f"sqlite:///{(_DATA_DIR / 'pgagi_interview.db').as_posix()}"

engine = create_engine(
    _db_url,
    connect_args={"check_same_thread": False},  # SQLite
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)
    # Migrate: add pending_question column if the sessions table pre-dates it
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE sessions ADD COLUMN pending_question TEXT"))
            conn.commit()
        except Exception:
            pass  # Column already exists


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
