"""
Main FastAPI application entry point for AI SEC Filing Analyzer.

This application demonstrates Generative AI capabilities for analyzing SEC filings,
showcasing skills for Junior Generative AI Developer positions.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import os
from dotenv import load_dotenv

from app.api.routes import analyzer
from app.core.config import get_settings

# Load environment variables
load_dotenv()

# Get application settings
settings = get_settings()

# Create FastAPI application
app = FastAPI(
    title="AI SEC Filing Analyzer",
    description="A demonstration of Generative AI capabilities for SEC filing analysis",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(analyzer.router, prefix="/api/v1", tags=["analyzer"])


@app.get("/", response_class=HTMLResponse)
async def root():
    """
    Root endpoint that provides basic information about the API.
    """
    return """
    <html>
        <head>
            <title>AI SEC Filing Analyzer API</title>
        </head>
        <body>
            <h1>🤖 AI SEC Filing Analyzer API</h1>
            <p>Welcome to the AI SEC Filing Analyzer - demonstrating Generative AI skills!</p>
            <h2>🚀 Features:</h2>
            <ul>
                <li><strong>Google Gemini Integration</strong> - Advanced LLM for text analysis</li>
                <li><strong>Vector Embeddings</strong> - Semantic search with Hugging Face</li>
                <li><strong>SEC Filing Analysis</strong> - Intelligent document processing</li>
                <li><strong>Question Answering</strong> - Natural language queries</li>
            </ul>
            <h2>📚 API Documentation:</h2>
            <ul>
                <li><a href="/docs">Interactive API Docs (Swagger)</a></li>
                <li><a href="/redoc">Alternative API Docs (ReDoc)</a></li>
            </ul>
            <h2>🔧 Example Usage:</h2>
            <pre>
POST /api/v1/analyze
{
    "filing_url": "https://sec.gov/...",
    "question": "What were the Q3 2024 earnings?"
}
            </pre>
        </body>
    </html>
    """


@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring.
    """
    return {
        "status": "healthy",
        "service": "AI SEC Filing Analyzer",
        "version": "1.0.0",
        "ai_providers": {
            "llm": "Google Gemini",
            "embeddings": "Hugging Face Sentence Transformers"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 