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
    description="""
    🤖 **AI-Powered SEC Filing Analysis**
    
    Analyze SEC filings using advanced AI to answer financial questions in plain English.
    
    **🚀 Quick Start:**
    1. Get SEC filing URLs from: https://www.sec.gov/search-filings
    2. Use POST /api/v1/analyses to analyze any filing
    3. Ask questions like "What were Q3 2024 revenues?" or "What are the main risks?"
    
    **🛠 Technology Stack:**
    - **Google Gemini**: Advanced language model for analysis
    - **Hugging Face**: Open-source embeddings for semantic search  
    - **ChromaDB**: Vector database for document retrieval
    - **LangChain**: Document processing and RAG pipeline
    
    **📊 Supported Filing Types:** 10-K, 10-Q, 8-K, 20-F, DEF 14A
    """,
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
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; }
                .highlight { background: #f0f8ff; padding: 15px; border-radius: 8px; margin: 15px 0; }
                pre { background: #f5f5f5; padding: 15px; border-radius: 8px; overflow-x: auto; }
                a { color: #0066cc; text-decoration: none; }
                a:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <h1>🤖 AI SEC Filing Analyzer API</h1>
            <p>Welcome to the AI SEC Filing Analyzer - demonstrating advanced Generative AI capabilities for financial document analysis!</p>
            
            <div class="highlight">
                <h3>🚀 Quick Start Guide:</h3>
                <ol>
                    <li><strong>Get SEC Filing URLs:</strong> Visit <a href="https://www.sec.gov/search-filings" target="_blank">SEC EDGAR Database</a></li>
                    <li><strong>Search</strong> for any public company (Apple, Tesla, Microsoft, etc.)</li>
                    <li><strong>Copy</strong> a recent 10-K, 10-Q, or 8-K filing URL</li>
                    <li><strong>Use the API</strong> to analyze it with AI!</li>
                </ol>
            </div>
            
            <h2>🚀 Key Features:</h2>
            <ul>
                <li><strong>Google Gemini Integration</strong> - State-of-the-art LLM for text analysis</li>
                <li><strong>Vector Embeddings</strong> - Semantic search with Hugging Face transformers</li>
                <li><strong>RAG Pipeline</strong> - Retrieval-Augmented Generation for accurate answers</li>
                <li><strong>Natural Language Queries</strong> - Ask questions in plain English</li>
                <li><strong>ChromaDB Vector Store</strong> - Efficient document storage and retrieval</li>
            </ul>
            
            <h2>📚 API Documentation:</h2>
            <ul>
                <li><a href="/docs">📖 Interactive API Docs (Swagger UI)</a></li>
                <li><a href="/redoc">📋 Alternative API Docs (ReDoc)</a></li>
                <li><a href="/api/v1/system/status">🏥 System Health Check</a></li>
                <li><a href="/api/v1/examples/queries">💡 Example Questions</a></li>
            </ul>
            
            <h2>🔧 Example API Usage:</h2>
            <pre>
POST /api/v1/analyses
{
    "filing_url": "https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/aapl-20240928.htm",
    "question": "What were the total revenues for Q4 2024?"
}

Response:
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "question": "What were the total revenues for Q4 2024?",
    "answer": "Apple's total net sales for Q4 2024 were $94.9 billion...",
    "confidence_score": 0.95,
    "filing_info": {
        "company_name": "Apple Inc.",
        "filing_type": "10-K"
    }
}
            </pre>
            
            <div class="highlight">
                <h3>💡 Try these questions:</h3>
                <ul>
                    <li>"What were the total revenues for the most recent quarter?"</li>
                    <li>"What are the main risk factors mentioned?"</li>
                    <li>"How much cash does the company have?"</li>
                    <li>"What is management's outlook for next year?"</li>
                </ul>
            </div>
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