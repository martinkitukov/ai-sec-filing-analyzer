"""
API routes for SEC filing analysis.

This module implements the main analysis endpoints following RESTful principles
and demonstrates proper error handling and response formatting.
"""

import time
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse

from app.models.schemas import (
    AnalysisRequest, 
    AnalysisResponse, 
    ErrorResponse,
    Examples
)
from app.core.config import get_settings, Settings
from app.services.analyzer_service import AnalyzerService
from app.utils.exceptions import (
    DocumentProcessingError,
    AIServiceError,
    ValidationError
)

# Create router instance
router = APIRouter()

# Dependency injection for settings
def get_analyzer_service(settings: Settings = Depends(get_settings)) -> AnalyzerService:
    """
    Dependency injection for analyzer service.
    
    This follows the Dependency Inversion Principle by injecting the service
    rather than creating it directly in the route handlers.
    """
    return AnalyzerService(settings)


@router.post(
    "/analyze",
    response_model=AnalysisResponse,
    responses={
        200: {
            "description": "Successful analysis",
            "content": {
                "application/json": {
                    "example": Examples.ANALYSIS_RESPONSE
                }
            }
        },
        400: {
            "description": "Invalid request",
            "model": ErrorResponse
        },
        422: {
            "description": "Validation error",
            "model": ErrorResponse
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse
        }
    },
    summary="Analyze SEC Filing",
    description="""
    Analyze a SEC filing document using AI to answer specific questions.
    
    This endpoint demonstrates:
    - **Document Processing**: Fetches and parses SEC filings
    - **Vector Embeddings**: Creates searchable document representations
    - **LLM Integration**: Uses Google Gemini for intelligent analysis
    - **Contextual Responses**: Provides relevant, accurate answers
    
    **Example Use Cases:**
    - "What were the Q3 2024 earnings?"
    - "What are the main risk factors mentioned?"
    - "What is the company's cash position?"
    """
)
async def analyze_filing(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    analyzer: AnalyzerService = Depends(get_analyzer_service)
) -> AnalysisResponse:
    """
    Analyze a SEC filing and answer questions about it.
    
    Args:
        request: Analysis request containing filing URL and question
        background_tasks: FastAPI background tasks for cleanup
        analyzer: Injected analyzer service
        
    Returns:
        AnalysisResponse: AI-generated analysis results
        
    Raises:
        HTTPException: For various error conditions
    """
    start_time = time.time()
    
    try:
        # Perform the analysis
        result = await analyzer.analyze_filing(
            filing_url=str(request.filing_url),
            question=request.question,
            filing_type=request.filing_type,
            include_context=request.include_context,
            max_response_length=request.max_response_length
        )
        
        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)
        result.processing_time_ms = processing_time_ms
        
        # Schedule cleanup tasks in background
        background_tasks.add_task(
            _cleanup_temporary_files,
            analyzer.get_temp_files()
        )
        
        return result
        
    except ValidationError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "Validation Error",
                "message": str(e),
                "details": {"field": e.field if hasattr(e, 'field') else None}
            }
        )
        
    except DocumentProcessingError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Document Processing Error",
                "message": str(e),
                "details": {"url": str(request.filing_url)}
            }
        )
        
    except AIServiceError as e:
        raise HTTPException(
            status_code=502,
            detail={
                "error": "AI Service Error",
                "message": str(e),
                "details": {"provider": "Google Gemini"}
            }
        )
        
    except Exception as e:
        # Log the full error for debugging
        print(f"Unexpected error in analyze_filing: {str(e)}")
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal Server Error",
                "message": "An unexpected error occurred during analysis",
                "details": None
            }
        )


@router.get(
    "/supported-filings",
    summary="Get Supported Filing Types",
    description="Returns a list of SEC filing types supported by the analyzer"
)
async def get_supported_filings() -> Dict[str, Any]:
    """
    Get information about supported SEC filing types.
    
    Returns:
        Dict containing supported filing types and their descriptions
    """
    return {
        "supported_types": [
            {
                "code": "10-K",
                "name": "Annual Report",
                "description": "Comprehensive annual business and financial report"
            },
            {
                "code": "10-Q", 
                "name": "Quarterly Report",
                "description": "Quarterly financial report"
            },
            {
                "code": "8-K",
                "name": "Current Report", 
                "description": "Report of triggering events or corporate changes"
            },
            {
                "code": "20-F",
                "name": "Foreign Annual Report",
                "description": "Annual report for foreign companies"
            },
            {
                "code": "DEF 14A",
                "name": "Proxy Statement",
                "description": "Shareholder meeting proxy statement"
            }
        ],
        "capabilities": [
            "Financial data extraction",
            "Risk factor analysis", 
            "Management discussion analysis",
            "Balance sheet information",
            "Income statement data",
            "Cash flow analysis"
        ]
    }


@router.get(
    "/examples",
    summary="Get Example Queries",
    description="Returns example questions and expected response formats"
)
async def get_examples() -> Dict[str, Any]:
    """
    Get example queries and responses for API testing.
    
    Returns:
        Dict containing example requests and responses
    """
    return {
        "example_questions": [
            "What were the total revenues for Q3 2024?",
            "What are the main risk factors mentioned in this filing?",
            "What is the company's current cash and cash equivalents?",
            "How much did the company spend on research and development?",
            "What was the net income for the reporting period?",
            "What are the company's largest operating expenses?",
            "What new acquisitions or investments were made?",
            "What is management's outlook for the next quarter?",
            "What legal proceedings is the company involved in?",
            "What were the earnings per share for this period?"
        ],
        "sample_request": Examples.ANALYSIS_REQUEST,
        "sample_response_format": Examples.ANALYSIS_RESPONSE,
        "tips": [
            "Be specific in your questions for better results",
            "Reference specific time periods when asking about financial data", 
            "Ask about specific line items for detailed financial information",
            "Questions about trends work well with multiple period comparisons"
        ]
    }


async def _cleanup_temporary_files(temp_files: list) -> None:
    """
    Background task to clean up temporary files.
    
    Args:
        temp_files: List of temporary file paths to clean up
    """
    import os
    
    for file_path in temp_files:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            # Log but don't fail on cleanup errors
            print(f"Warning: Failed to cleanup temporary file {file_path}: {e}")


# Note: Exception handlers should be added to the main FastAPI app, not individual routers 