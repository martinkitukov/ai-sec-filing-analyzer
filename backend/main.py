from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .db.database import engine, Base
from .routes import edgar

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="SEC Insight AI")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(edgar.router, prefix="/api/v1", tags=["edgar"])

@app.get("/")
async def root():
    return {
        "message": "SEC Insight AI API",
        "version": "1.0.0",
        "docs_url": "/docs"
    } 