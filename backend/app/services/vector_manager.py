"""
Vector Database Manager for SEC Filing Analysis.

This service manages vector embeddings generation, storage, and similarity search
using ChromaDB and Hugging Face sentence transformers.
"""

import os
import logging
from typing import List, Dict, Any, Optional, Tuple
import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
from langchain.schema import Document

from app.utils.exceptions import AIServiceError
from app.core.config import Settings


class VectorManager:
    """
    Service for managing vector embeddings and similarity search.
    
    Handles embedding generation, vector storage in ChromaDB,
    and retrieval for RAG-based question answering.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize vector manager.
        
        Args:
            settings: Application configuration
        """
        self.settings = settings
        self.embedding_model = None
        self.chroma_client = None
        self.collection = None
        
    async def initialize(self):
        """
        Initialize embedding model and vector database.
        
        This is called separately from __init__ to handle async initialization.
        """
        try:
            # Initialize embedding model
            self.embedding_model = SentenceTransformer(self.settings.hf_model_name)
            
            # Initialize ChromaDB
            os.makedirs(self.settings.vector_db_path, exist_ok=True)
            
            self.chroma_client = chromadb.PersistentClient(
                path=self.settings.vector_db_path,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Get or create collection
            self.collection = self.chroma_client.get_or_create_collection(
                name=self.settings.collection_name,
                metadata={"description": "SEC Filing Analysis Embeddings"}
            )
            
            logging.info(f"Vector manager initialized with model: {self.settings.hf_model_name}")
            
        except Exception as e:
            raise AIServiceError(f"Failed to initialize vector manager: {str(e)}")
    
    async def add_documents(self, documents: List[Document]) -> List[str]:
        """
        Add documents to vector database with embeddings.
        
        Args:
            documents: List of documents to add
            
        Returns:
            List of document IDs
            
        Raises:
            AIServiceError: If embeddings generation or storage fails
        """
        if not self.embedding_model or not self.collection:
            await self.initialize()
            
        try:
            # Extract text content for embedding
            texts = [doc.page_content for doc in documents]
            
            # Generate embeddings
            embeddings = self.embedding_model.encode(
                texts,
                show_progress_bar=False,
                normalize_embeddings=True
            ).tolist()
            
            # Prepare metadata for storage
            metadatas = []
            ids = []
            
            for i, doc in enumerate(documents):
                # Create unique ID
                doc_id = f"doc_{hash(doc.page_content + str(doc.metadata))}_{i}"
                ids.append(doc_id)
                
                # Prepare metadata (ChromaDB requires string values)
                metadata = {}
                for key, value in doc.metadata.items():
                    metadata[key] = str(value)
                
                metadatas.append(metadata)
            
            # Add to collection
            self.collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            
            logging.info(f"Added {len(documents)} documents to vector database")
            return ids
            
        except Exception as e:
            raise AIServiceError(f"Failed to add documents to vector database: {str(e)}")
    
    async def similarity_search(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, str]] = None
    ) -> List[Tuple[Document, float]]:
        """
        Perform similarity search for relevant document chunks.
        
        Args:
            query: Search query
            top_k: Number of top results to return
            filter_metadata: Optional metadata filters
            
        Returns:
            List of (document, similarity_score) tuples
            
        Raises:
            AIServiceError: If search fails
        """
        if not self.embedding_model or not self.collection:
            await self.initialize()
            
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode(
                [query],
                normalize_embeddings=True
            ).tolist()[0]
            
            # Perform search
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filter_metadata
            )
            
            # Convert results to Document objects with scores
            documents_with_scores = []
            
            if results['documents'] and results['documents'][0]:
                for i in range(len(results['documents'][0])):
                    # Reconstruct document
                    doc = Document(
                        page_content=results['documents'][0][i],
                        metadata=results['metadatas'][0][i] if results['metadatas'] else {}
                    )
                    
                    # Calculate similarity score (ChromaDB returns distances, convert to similarity)
                    distance = results['distances'][0][i] if results['distances'] else 1.0
                    similarity_score = 1.0 - distance  # Convert distance to similarity
                    
                    documents_with_scores.append((doc, similarity_score))
            
            # Sort by similarity score (highest first)
            documents_with_scores.sort(key=lambda x: x[1], reverse=True)
            
            logging.info(f"Found {len(documents_with_scores)} relevant documents for query")
            return documents_with_scores
            
        except Exception as e:
            raise AIServiceError(f"Failed to perform similarity search: {str(e)}")
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector database collection.
        
        Returns:
            Dictionary with collection statistics
        """
        if not self.collection:
            await self.initialize()
            
        try:
            count = self.collection.count()
            
            return {
                "total_documents": count,
                "collection_name": self.settings.collection_name,
                "embedding_model": self.settings.hf_model_name,
                "embedding_dimension": self.embedding_model.get_sentence_embedding_dimension() if self.embedding_model else None
            }
            
        except Exception as e:
            logging.warning(f"Failed to get collection stats: {str(e)}")
            return {"error": str(e)}
    
    async def clear_collection(self):
        """
        Clear all documents from the collection.
        
        Useful for testing or starting fresh.
        """
        if not self.collection:
            await self.initialize()
            
        try:
            # Get all IDs and delete them
            all_results = self.collection.get()
            if all_results['ids']:
                self.collection.delete(ids=all_results['ids'])
            
            logging.info("Cleared vector database collection")
            
        except Exception as e:
            logging.warning(f"Failed to clear collection: {str(e)}")
    
    def get_embedding_model_info(self) -> Dict[str, Any]:
        """
        Get information about the embedding model.
        
        Returns:
            Dictionary with model information
        """
        if not self.embedding_model:
            return {"error": "Model not initialized"}
            
        try:
            return {
                "model_name": self.settings.hf_model_name,
                "embedding_dimension": self.embedding_model.get_sentence_embedding_dimension(),
                "max_sequence_length": getattr(self.embedding_model, 'max_seq_length', None),
                "model_type": type(self.embedding_model).__name__
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on vector database components.
        
        Returns:
            Health status dictionary
        """
        status = {
            "embedding_model": "unknown",
            "vector_database": "unknown",
            "collection": "unknown"
        }
        
        try:
            # Check embedding model
            if self.embedding_model:
                # Test embedding generation
                test_embedding = self.embedding_model.encode(["test"], normalize_embeddings=True)
                if len(test_embedding) > 0:
                    status["embedding_model"] = "healthy"
                else:
                    status["embedding_model"] = "error"
            else:
                status["embedding_model"] = "not_initialized"
                
            # Check vector database
            if self.chroma_client:
                collections = self.chroma_client.list_collections()
                status["vector_database"] = "healthy"
            else:
                status["vector_database"] = "not_initialized"
                
            # Check collection
            if self.collection:
                count = self.collection.count()
                status["collection"] = f"healthy ({count} documents)"
            else:
                status["collection"] = "not_initialized"
                
        except Exception as e:
            status["error"] = str(e)
            
        return status 