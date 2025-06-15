from sqlalchemy import Column, String, DateTime, JSON, Text, Enum
from sqlalchemy.sql import func
import enum
from .database import Base

class FilingType(enum.Enum):
    FORM_10K = "10-K"
    FORM_8K = "8-K"
    FORM_S1 = "S-1"
    FORM_144 = "144"
    OTHER = "OTHER"

class Filing(Base):
    __tablename__ = "filings"

    id = Column(String, primary_key=True)
    url = Column(String, nullable=False, unique=True)
    filing_type = Column(Enum(FilingType), nullable=False)
    content = Column(Text, nullable=False)
    metadata = Column(JSON)
    vector_id = Column(String)  # Reference to FAISS vector store
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(String, primary_key=True)
    filing_id = Column(String, nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now()) 