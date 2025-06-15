from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel, HttpUrl
import uuid

from ..db.database import get_db
from ..db.models import Filing, Analysis
from ..utils.parser import EdgarParser
from ..utils.embedder import DocumentEmbedder

router = APIRouter()
parser = EdgarParser()
embedder = DocumentEmbedder()

class FilingRequest(BaseModel):
    url: HttpUrl
    question: Optional[str] = None

class FilingResponse(BaseModel):
    filing_id: str
    filing_type: str
    metadata: dict
    answer: Optional[str] = None

@router.post("/analyze", response_model=FilingResponse)
async def analyze_filing(request: FilingRequest, db: Session = Depends(get_db)):
    try:
        # Fetch and parse the document
        content = await parser.fetch_document(str(request.url))
        filing_type = parser.detect_filing_type(str(request.url), content)
        metadata = parser.parse_document(content, filing_type)

        # Create filing record
        filing_id = str(uuid.uuid4())
        filing = Filing(
            id=filing_id,
            url=str(request.url),
            filing_type=filing_type,
            content=content,
            metadata=metadata
        )
        db.add(filing)

        # Process document for embeddings
        vector_id = embedder.process_document(content, metadata)
        filing.vector_id = vector_id
        db.commit()

        # If question is provided, get answer
        answer = None
        if request.question:
            result = embedder.query_document(request.question)
            answer = result["answer"]

            # Store analysis
            analysis = Analysis(
                id=str(uuid.uuid4()),
                filing_id=filing_id,
                question=request.question,
                answer=answer
            )
            db.add(analysis)
            db.commit()

        return FilingResponse(
            filing_id=filing_id,
            filing_type=filing_type.value,
            metadata=metadata,
            answer=answer
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/filing/{filing_id}")
async def get_filing(filing_id: str, db: Session = Depends(get_db)):
    filing = db.query(Filing).filter(Filing.id == filing_id).first()
    if not filing:
        raise HTTPException(status_code=404, detail="Filing not found")
    
    return {
        "id": filing.id,
        "url": filing.url,
        "filing_type": filing.filing_type.value,
        "metadata": filing.metadata,
        "created_at": filing.created_at
    }

@router.get("/filing/{filing_id}/analyses")
async def get_filing_analyses(filing_id: str, db: Session = Depends(get_db)):
    analyses = db.query(Analysis).filter(Analysis.filing_id == filing_id).all()
    return [
        {
            "id": analysis.id,
            "question": analysis.question,
            "answer": analysis.answer,
            "created_at": analysis.created_at
        }
        for analysis in analyses
    ] 