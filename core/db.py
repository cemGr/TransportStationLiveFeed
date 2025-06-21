from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, declarative_base
import os

DATABASE_URL = os.getenv("DATABASE_URL")   # already set in .env / docker-compose

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False))
Base = declarative_base()

@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except:                 # noqa: E722  (bubble up later)
        session.rollback()
        raise
    finally:
        session.close()
