"""
Pydantic data models for AI SEC Filing Analyzer.

This module defines all request/response schemas with proper validation,
demonstrating professional API design and data validation practices.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl, validator
from enum import Enum


class FilingType(str, Enum):
    """Enumeration of supported SEC filing types."""
    FORM_10K = "10-K"
    FORM_10Q = "10-Q"
    FORM_8K = "8-K"
    FORM_20F = "20-F"
    FORM_DEF14A = "DEF 14A"
    OTHER = "OTHER"


class AnalysisRequest(BaseModel):
    """
    Request model for SEC filing analysis.
    
    This model validates incoming requests and ensures proper data types
    and constraints for the analysis endpoint.
    """
    
    filing_url: HttpUrl = Field(
        ...,
        description="URL to the SEC filing document",
        example="https://www.sec.gov/Archives/edgar/data/320193/000032019324000081/aapl-20240630.htm"
    )
    
    question: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Question to ask about the filing",
        example="What were the total revenues for Q3 2024?"
    )
    
    filing_type: Optional[FilingType] = Field(
        default=None,
        description="Type of SEC filing (optional, will be auto-detected)"
    )
    
    include_context: bool = Field(
        default=True,
        description="Whether to include relevant document context in response"
    )
    
    max_response_length: Optional[int] = Field(
        default=None,
        ge=100,
        le=4000,
        description="Maximum length of the AI response"
    )
    
    @validator('filing_url')
    def validate_sec_url(cls, v):
        """Validate that the URL appears to be a valid SEC filing URL."""
        url_str = str(v)
        if not ("sec.gov" in url_str.lower() or "edgar" in url_str.lower()):
            raise ValueError("URL must be a valid SEC filing URL")
        return v
    
    @validator('question')
    def validate_question(cls, v):
        """Validate question content and format."""
        if not v.strip():
            raise ValueError("Question cannot be empty")
        
        # Check for potentially problematic content
        prohibited_words = ["hack", "exploit", "bypass", "jailbreak"]
        if any(word in v.lower() for word in prohibited_words):
            raise ValueError("Question contains prohibited content")
        
        return v.strip()


class DocumentChunk(BaseModel):
    """Model representing a chunk of document text with metadata."""
    
    content: str = Field(..., description="Text content of the chunk")
    chunk_id: str = Field(..., description="Unique identifier for the chunk")
    similarity_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Similarity score to the query (0-1)"
    )
    page_number: Optional[int] = Field(
        default=None,
        description="Page number in the original document"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the chunk"
    )


class AnalysisResponse(BaseModel):
    """
    Response model for SEC filing analysis.
    
    This model structures the AI analysis results with proper typing
    and includes metadata for transparency and debugging.
    """
    
    question: str = Field(..., description="The original question asked")
    answer: str = Field(..., description="AI-generated answer to the question")
    
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score of the analysis (0-1)"
    )
    
    filing_info: Dict[str, Any] = Field(
        default_factory=dict,
        description="Information about the analyzed filing"
    )
    
    relevant_chunks: List[DocumentChunk] = Field(
        default_factory=list,
        description="Document chunks used to generate the answer"
    )
    
    processing_time_ms: int = Field(
        ...,
        description="Time taken to process the request in milliseconds"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the analysis was completed"
    )
    
    ai_model_info: Dict[str, str] = Field(
        default_factory=dict,
        description="Information about the AI models used"
    )


class ErrorResponse(BaseModel):
    """Standard error response model."""
    
    error: str = Field(..., description="Error type or category")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error details"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the error occurred"
    )


class HealthResponse(BaseModel):
    """Health check response model."""
    
    status: str = Field(..., description="Service health status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    ai_providers: Dict[str, str] = Field(..., description="AI provider information")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Health check timestamp"
    )


class FilingMetadata(BaseModel):
    """Model for SEC filing metadata."""
    
    company_name: Optional[str] = Field(default=None, description="Company name")
    filing_type: Optional[str] = Field(default=None, description="Type of filing")
    filing_date: Optional[str] = Field(default=None, description="Filing date")
    period_end_date: Optional[str] = Field(default=None, description="Period end date")
    cik: Optional[str] = Field(default=None, description="Central Index Key")
    ticker: Optional[str] = Field(default=None, description="Stock ticker symbol")
    document_size: Optional[int] = Field(default=None, description="Document size in characters")
    processed_chunks: Optional[int] = Field(default=None, description="Number of chunks processed")


# Example data for API documentation
class Examples:
    """Example data for API documentation and testing."""
    
    ANALYSIS_REQUEST = {
        "filing_url": "https://www.sec.gov/Archives/edgar/data/320193/000032019324000081/aapl-20240630.htm",
        "question": "What were the total net sales for the third quarter of 2024?",
        "filing_type": "10-Q",
        "include_context": True,
        "max_response_length": 2000
    }
    
    ANALYSIS_RESPONSE = {
        "question": "What were the total net sales for the third quarter of 2024?",
        "answer": "According to the 10-Q filing, Apple's total net sales for the third quarter of 2024 were $85.8 billion, representing a 5% increase compared to the same quarter in the previous year.",
        "confidence_score": 0.92,
        "filing_info": {
            "company_name": "Apple Inc.",
            "filing_type": "10-Q",
            "filing_date": "2024-08-01",
            "period_end_date": "2024-06-30"
        },
        "relevant_chunks": [],
        "processing_time_ms": 1250,
        "ai_model_info": {
            "llm": "gemini-1.5-flash",
            "embeddings": "sentence-transformers/all-MiniLM-L6-v2"
        }
    } 