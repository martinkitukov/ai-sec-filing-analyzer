from sqlalchemy import Column, String, DateTime, JSON, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class Filing(Base):
    __tablename__ = "filings"

    id = Column(String, primary_key=True)
    url = Column(String, nullable=False)
    content = Column(String, nullable=False)
    summary = Column(String)
    structured_data = Column(JSON)
    vector_id = Column(String)  # Reference to FAISS vector store
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Database connection
SQLALCHEMY_DATABASE_URL = "sqlite:///./sec_filings.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 