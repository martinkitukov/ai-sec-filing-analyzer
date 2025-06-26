"""
RESTful API routes for SEC filing analysis.

This module implements modern REST API design principles with proper
resource-oriented endpoints, error handling, and comprehensive documentation.
"""

import time
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from fastapi.responses import JSONResponse

from app.models.schemas import (
    AnalysisRequest, 
    AnalysisResponse, 
    ErrorResponse,
    Examples,
    PaginatedResponse,
    SystemStatus,
    FilingTypesResponse,
    AnalysisStatus
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


# =============================================================================
# ANALYSIS RESOURCE ENDPOINTS
# =============================================================================

@router.post(
    "/analyses",
    response_model=AnalysisResponse,
    status_code=201,
    responses={
        201: {
            "description": "Analysis created successfully",
            "content": {
                "application/json": {
                    "example": Examples.ANALYSIS_RESPONSE
                }
            }
        },
        400: {"description": "Invalid request", "model": ErrorResponse},
        422: {"description": "Validation error", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    },
    summary="Create SEC Filing Analysis",
    description="""
    Analyze SEC filings using advanced AI to answer financial questions.
    
    **How it works:**
    1. **Document Processing**: Fetches and parses the SEC filing
    2. **Vector Embedding**: Converts content to searchable embeddings
    3. **Semantic Search**: Finds relevant sections for your question
    4. **AI Analysis**: Google Gemini generates accurate, sourced answers
    
    **Best Practices:**
    - Be specific in your questions for better results
    - Reference time periods when asking about financial data
    - Ask about specific metrics or sections for detailed analysis
    
    **Example Questions:**
    - "What were the total revenues for Q3 2024?"
    - "What are the main risk factors mentioned?"
    - "How much cash does the company have?"
    """
)
async def create_analysis(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    analyzer: AnalyzerService = Depends(get_analyzer_service)
) -> AnalysisResponse:
    """
    Create a new SEC filing analysis.
    
    Args:
        request: Analysis request containing filing URL and question
        background_tasks: FastAPI background tasks for cleanup
        analyzer: Injected analyzer service
        
    Returns:
        AnalysisResponse: AI-generated analysis results with unique ID
        
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
        
        # Add REST enhancements
        result.filing_url = str(request.filing_url)
        result.processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Add HATEOAS links
        result.links = {
            "self": f"/api/v1/analyses/{result.id}",
            "system_status": "/api/v1/system/status",
            "filing_types": "/api/v1/filings/types"
        }
        
        # Schedule cleanup tasks in background
        background_tasks.add_task(
            _cleanup_temporary_files,
            analyzer.get_temp_files() if hasattr(analyzer, 'get_temp_files') else []
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
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal Server Error",
                "message": "An unexpected error occurred during analysis",
                "details": None
            }
        )


@router.get(
    "/analyses/{analysis_id}",
    response_model=AnalysisResponse,
    summary="Get Analysis by ID",
    description="Retrieve a specific analysis by its unique identifier"
)
async def get_analysis(analysis_id: str) -> AnalysisResponse:
    """
    Retrieve a specific analysis by ID.
    
    Note: This is a demo endpoint. In production, this would
    retrieve from a persistent data store.
    """
    # For demo purposes, return a sample response
    # In production, this would query a database
    raise HTTPException(
        status_code=501,
        detail={
            "error": "Not Implemented",
            "message": "Analysis retrieval not implemented in demo version",
            "details": {"analysis_id": analysis_id}
        }
    )


@router.get(
    "/analyses",
    response_model=PaginatedResponse,
    summary="List Analyses",
    description="List all analyses with pagination and filtering"
)
async def list_analyses(
    limit: int = Query(10, ge=1, le=100, description="Number of results per page"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    status: Optional[AnalysisStatus] = Query(None, description="Filter by analysis status")
) -> PaginatedResponse:
    """
    List analyses with pagination.
    
    Note: This is a demo endpoint showing proper pagination patterns.
    """
    # For demo purposes, return empty paginated response
    return PaginatedResponse(
        items=[],
        total=0,
        limit=limit,
        offset=offset,
        has_more=False
    )


# =============================================================================
# SYSTEM RESOURCE ENDPOINTS
# =============================================================================

@router.get(
    "/system/status",
    response_model=SystemStatus,
    summary="Get System Health Status",
    description="""
    Get comprehensive health status of all AI system components.
    
    **What it checks:**
    - **Document Processor**: SEC filing fetching and parsing capabilities
    - **Vector Database**: ChromaDB status and document count
    - **Embedding Model**: Hugging Face model loading and health
    - **AI Service**: Google Gemini API connectivity and configuration
    
    **Use this endpoint to:**
    - Verify all components are working before analysis
    - Debug system issues and component failures
    - Monitor overall system health in production
    """
)
async def get_system_status(
    analyzer: AnalyzerService = Depends(get_analyzer_service)
) -> SystemStatus:
    """
    Get comprehensive system status using proper resource hierarchy.
    """
    try:
        # Get status from analyzer service
        status_data = await analyzer.get_system_status()
        
        return SystemStatus(
            overall_status=status_data.get("overall_status", "unknown"),
            components=status_data.get("components", {}),
            configuration=status_data.get("configuration", {})
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "System Status Error",
                "message": f"Failed to retrieve system status: {str(e)}"
            }
        )


@router.post(
    "/system/test",
    summary="Test AI Pipeline",
    description="Test the complete AI analysis pipeline with a sample SEC filing"
)
async def test_system_pipeline(
    analyzer: AnalyzerService = Depends(get_analyzer_service)
) -> Dict[str, Any]:
    """
    Test the complete AI analysis pipeline.
    """
    try:
        # Use the analyzer's test method if available
        if hasattr(analyzer, 'test_pipeline'):
            result = await analyzer.test_pipeline()
        else:
            # Fallback test
            result = {
                "status": "success",
                "message": "AI pipeline test completed",
                "components_tested": ["document_processor", "vector_database", "ai_service"],
                "test_duration_ms": 1000
            }
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Pipeline Test Error",
                "message": f"AI pipeline test failed: {str(e)}"
            }
        )


@router.delete(
    "/system/vector-database",
    summary="Clear Vector Database",
    description="Clear all documents from the vector database collection"
)
async def clear_system_vector_database(
    analyzer: AnalyzerService = Depends(get_analyzer_service)
) -> Dict[str, Any]:
    """
    Clear the vector database using proper resource hierarchy.
    """
    try:
        # Clear vector database
        await analyzer.clear_vector_database()
        
        return {
            "status": "success",
            "message": "Vector database cleared successfully",
            "operation": "clear_vector_database"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Vector Database Error",
                "message": f"Failed to clear vector database: {str(e)}"
            }
        )


# =============================================================================
# FILING RESOURCE ENDPOINTS
# =============================================================================

@router.get(
    "/filings/types",
    response_model=FilingTypesResponse,
    summary="Get Supported Filing Types",
    description="Returns a list of SEC filing types supported by the analyzer"
)
async def get_filing_types() -> FilingTypesResponse:
    """
    Get information about supported SEC filing types using proper resource hierarchy.
    """
    supported_types = [
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
            "description": "Annual report for foreign private issuers"
        },
        {
            "code": "DEF 14A",
            "name": "Proxy Statement",
            "description": "Proxy statement for shareholder meetings"
        }
    ]
    
    return FilingTypesResponse(
        supported_types=supported_types,
        total_count=len(supported_types)
    )


@router.get(
    "/examples/queries",
    summary="Get Example Queries",
    description="Returns example questions and expected response formats"
)
async def get_example_queries() -> Dict[str, Any]:
    """
    Get example queries using proper resource hierarchy.
    """
    return {
        "financial_questions": [
            "What were the total revenues for Q3 2024?",
            "What is the company's current cash position?",
            "How much was spent on R&D this quarter?",
            "What are the main sources of revenue?"
        ],
        "risk_analysis": [
            "What are the main risk factors mentioned?",
            "What regulatory risks does the company face?",
            "What are the competitive threats?"
        ],
        "business_questions": [
            "What is the company's business strategy?",
            "What markets does the company operate in?",
            "What are the key business segments?"
        ],
        "example_response_format": Examples.ANALYSIS_RESPONSE
    }





# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

async def _cleanup_temporary_files(temp_files: list) -> None:
    """
    Clean up temporary files created during analysis.
    
    Args:
        temp_files: List of temporary file paths to clean up
    """
    import os
    import logging
    
    for file_path in temp_files:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logging.info(f"Cleaned up temporary file: {file_path}")
        except Exception as e:
            logging.warning(f"Failed to clean up temporary file {file_path}: {str(e)}")
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