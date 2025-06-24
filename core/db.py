from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import os
DATABASE_URL = os.getenv("DATABASE_URL")   # already set in .env / docker-compose

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False))

@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()
