"""
Analyzer Service for AI SEC Filing Analysis.

This service orchestrates the complete analysis pipeline including
document processing, vector embedding, and AI-powered question answering.
"""

import time
import logging
from typing import Optional, List, Dict, Any
from app.core.config import Settings
from app.models.schemas import AnalysisResponse, FilingType
from app.services.document_processor import DocumentProcessor
from app.services.vector_manager import VectorManager
from app.services.ai_service import AIService
from app.utils.exceptions import DocumentProcessingError, AIServiceError


class AnalyzerService:
    """
    Main service class for SEC filing analysis.
    
    This service orchestrates the entire RAG (Retrieval-Augmented Generation) pipeline:
    1. Document fetching and processing
    2. Vector embedding generation and storage
    3. Similarity search for relevant content
    4. AI-powered question answering with context
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize analyzer service with all required components.
        
        Args:
            settings: Application configuration settings
        """
        self.settings = settings
        self._temp_files: List[str] = []
        
        # Initialize component services
        self.doc_processor = DocumentProcessor(settings)
        self.vector_manager = VectorManager(settings)
        self.ai_service = AIService(settings)
        
        # Track initialization status
        self._vector_initialized = False
        
        logging.info("Analyzer service initialized with all AI components")
    
    async def analyze_filing(
        self,
        filing_url: str,
        question: str,
        filing_type: Optional[FilingType] = None,
        include_context: bool = True,
        max_response_length: Optional[int] = None
    ) -> AnalysisResponse:
        """
        Perform complete SEC filing analysis using RAG pipeline.
        
        Args:
            filing_url: URL to the SEC filing document
            question: Question to ask about the filing
            filing_type: Optional filing type specification
            include_context: Whether to include document context
            max_response_length: Maximum response length
            
        Returns:
            AnalysisResponse: Complete analysis results
        """
        start_time = time.time()
        
        try:
            # Step 1: Process the document
            logging.info(f"Processing SEC filing: {filing_url}")
            documents = await self.doc_processor.fetch_and_process_filing(filing_url)
            
            if not documents:
                raise DocumentProcessingError("No content could be extracted from the filing")
            
            # Step 2: Initialize vector database if needed
            if not self._vector_initialized:
                await self.vector_manager.initialize()
                self._vector_initialized = True
            
            # Step 3: Add documents to vector database
            logging.info(f"Adding {len(documents)} document chunks to vector database")
            doc_ids = await self.vector_manager.add_documents(documents)
            
            # Step 4: Perform similarity search for relevant context
            logging.info(f"Searching for relevant context for question: {question}")
            relevant_docs = await self.vector_manager.similarity_search(
                query=question,
                top_k=8,  # Get top 8 most relevant chunks
                filter_metadata=None
            )
            
            # Extract documents and scores
            context_documents = [doc for doc, score in relevant_docs if score > 0.3]  # Filter by relevance
            
            if not context_documents:
                # If no relevant context found, use top documents anyway
                context_documents = documents[:5]
                logging.warning("No highly relevant context found, using top document chunks")
            
            # Step 5: Extract filing metadata
            filing_metadata = self._extract_filing_metadata(documents, filing_url)
            
            # Step 6: Generate AI response with context
            logging.info("Generating AI response with context")
            ai_result = await self.ai_service.analyze_with_context(
                question=question,
                context_documents=context_documents,
                filing_metadata=filing_metadata,
                max_response_length=max_response_length
            )
            
            # Step 7: Prepare comprehensive response
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            response = AnalysisResponse(
                question=question,
                answer=ai_result["answer"],
                confidence_score=ai_result["confidence_score"],
                filing_info={
                    "url": filing_url,
                    "type": filing_type.value if filing_type else "Unknown",
                    "company_name": filing_metadata.get("company_name", "Unknown"),
                    "form_type": filing_metadata.get("form_type", "Unknown"),
                    "filing_date": filing_metadata.get("filing_date", "Unknown"),
                    "chunks_processed": len(documents),
                    "chunks_used_for_context": len(context_documents)
                },
                context_sources=ai_result.get("context_used", []) if include_context else [],
                processing_time_ms=processing_time_ms,
                ai_model_info={
                    "llm": ai_result["model_info"]["model"],
                    "embeddings": self.settings.hf_model_name,
                    "vector_db": "ChromaDB"
                }
            )
            
            logging.info(f"Analysis completed in {processing_time_ms}ms")
            return response
            
        except DocumentProcessingError as e:
            logging.error(f"Document processing failed: {str(e)}")
            raise
            
        except AIServiceError as e:
            logging.error(f"AI service failed: {str(e)}")
            raise
            
        except Exception as e:
            logging.error(f"Unexpected error in analysis: {str(e)}")
            raise AIServiceError(f"Analysis pipeline failed: {str(e)}")
    
    def _extract_filing_metadata(self, documents: List, filing_url: str) -> Dict[str, Any]:
        """
        Extract consolidated metadata from processed documents.
        
        Args:
            documents: List of processed documents
            filing_url: Original filing URL
            
        Returns:
            Consolidated metadata dictionary
        """
        metadata = {"source_url": filing_url}
        
        # Extract metadata from first document (which should have filing-level metadata)
        if documents and hasattr(documents[0], 'metadata'):
            doc_metadata = documents[0].metadata
            
            for key in ['company_name', 'form_type', 'filing_date']:
                if key in doc_metadata:
                    metadata[key] = doc_metadata[key]
        
        return metadata
    
    async def get_system_status(self) -> Dict[str, Any]:
        """
        Get comprehensive status of all AI system components.
        
        Returns:
            System status dictionary
        """
        try:
            # Check vector manager
            vector_status = await self.vector_manager.health_check()
            vector_stats = await self.vector_manager.get_collection_stats()
            
            # Check AI service
            ai_status = await self.ai_service.health_check()
            ai_info = self.ai_service.get_model_info()
            
            # Check embedding model info
            embedding_info = self.vector_manager.get_embedding_model_info()
            
            return {
                "overall_status": "healthy" if all(
                    status.get("status") == "healthy" or "healthy" in str(status)
                    for status in [vector_status, ai_status]
                ) else "degraded",
                "components": {
                    "document_processor": {
                        "status": "healthy",
                        "chunk_size": self.settings.chunk_size,
                        "chunk_overlap": self.settings.chunk_overlap,
                        "max_chunks": self.settings.max_chunks
                    },
                    "vector_database": {
                        **vector_status,
                        "stats": vector_stats
                    },
                    "embedding_model": embedding_info,
                    "ai_service": {
                        **ai_status,
                        "info": ai_info
                    }
                },
                "configuration": {
                    "vector_db_path": self.settings.vector_db_path,
                    "collection_name": self.settings.collection_name,
                    "request_timeout": self.settings.request_timeout
                }
            }
            
        except Exception as e:
            return {
                "overall_status": "error",
                "error": str(e),
                "components": {}
            }
    
    async def clear_vector_database(self):
        """
        Clear the vector database collection.
        
        Useful for testing or when starting fresh with new documents.
        """
        try:
            if not self._vector_initialized:
                await self.vector_manager.initialize()
                self._vector_initialized = True
            
            await self.vector_manager.clear_collection()
            logging.info("Vector database cleared successfully")
            
        except Exception as e:
            logging.error(f"Failed to clear vector database: {str(e)}")
            raise AIServiceError(f"Failed to clear vector database: {str(e)}")
    
    def get_temp_files(self) -> List[str]:
        """
        Get list of temporary files for cleanup.
        
        Returns:
            List of temporary file paths
        """
        return self._temp_files.copy()
    
    async def process_sample_filing(self) -> Dict[str, Any]:
        """
        Process a sample SEC filing for testing purposes.
        
        Returns:
            Processing results for validation
        """
        sample_url = "https://www.sec.gov/Archives/edgar/data/320193/000032019324000006/aapl-20231230.htm"
        sample_question = "What were Apple's total revenues?"
        
        try:
            result = await self.analyze_filing(
                filing_url=sample_url,
                question=sample_question,
                filing_type=FilingType.FORM_10K,
                include_context=True,
                max_response_length=1000
            )
            
            return {
                "status": "success",
                "sample_url": sample_url,
                "sample_question": sample_question,
                "processing_time_ms": result.processing_time_ms,
                "chunks_processed": result.filing_info.get("chunks_processed", 0),
                "confidence_score": result.confidence_score
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "sample_url": sample_url,
                "sample_question": sample_question
            } 