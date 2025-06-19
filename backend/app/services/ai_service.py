"""
AI Service for Google Gemini Integration.

This service handles interactions with Google's Gemini AI model
for SEC filing analysis and question answering.
"""

import logging
from typing import Dict, Any, List, Optional
import google.genai as genai
from langchain_core.documents import Document

from app.utils.exceptions import AIServiceError
from app.core.config import Settings


class AIService:
    """
    Service for interacting with Google Gemini AI model.
    
    Handles prompt engineering, context preparation, and
    response generation for SEC filing analysis.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize AI service.
        
        Args:
            settings: Application configuration
        """
        self.settings = settings
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """
        Initialize Google Gemini client.
        
        Raises:
            AIServiceError: If client initialization fails
        """
        try:
            if not self.settings.google_api_key:
                raise AIServiceError("Google API key is required but not provided")
            
            # Configure the client
            genai.configure(api_key=self.settings.google_api_key)
            self.client = genai.GenerativeModel(self.settings.gemini_model)
            
            logging.info(f"AI service initialized with model: {self.settings.gemini_model}")
            
        except Exception as e:
            raise AIServiceError(f"Failed to initialize Google Gemini client: {str(e)}")
    
    async def analyze_with_context(
        self,
        question: str,
        context_documents: List[Document],
        filing_metadata: Dict[str, Any],
        max_response_length: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Analyze question with document context using Gemini.
        
        Args:
            question: User's question about the filing
            context_documents: Relevant document chunks
            filing_metadata: Metadata about the filing
            max_response_length: Maximum response length
            
        Returns:
            Dictionary with analysis results
            
        Raises:
            AIServiceError: If analysis fails
        """
        try:
            # Prepare context from documents
            context = self._prepare_context(context_documents, filing_metadata)
            
            # Create prompt
            prompt = self._create_analysis_prompt(question, context, max_response_length)
            
            # Generate response
            response = await self._generate_response(prompt)
            
            # Parse and structure response
            result = self._parse_response(response, context_documents)
            
            return result
            
        except Exception as e:
            raise AIServiceError(f"Failed to analyze with context: {str(e)}")
    
    def _prepare_context(
        self, 
        documents: List[Document], 
        metadata: Dict[str, Any]
    ) -> str:
        """
        Prepare context string from relevant documents.
        
        Args:
            documents: List of relevant document chunks
            metadata: Filing metadata
            
        Returns:
            Formatted context string
        """
        context_parts = []
        
        # Add filing metadata
        if metadata:
            context_parts.append("FILING INFORMATION:")
            for key, value in metadata.items():
                if value and key in ['company_name', 'form_type', 'filing_date', 'source_url']:
                    context_parts.append(f"- {key.replace('_', ' ').title()}: {value}")
            context_parts.append("")
        
        # Add document chunks
        context_parts.append("RELEVANT EXCERPTS:")
        for i, doc in enumerate(documents[:10], 1):  # Limit to top 10 chunks
            chunk_text = doc.page_content.strip()
            if len(chunk_text) > 50:  # Skip very short chunks
                context_parts.append(f"\nExcerpt {i}:")
                context_parts.append(chunk_text)
        
        return "\n".join(context_parts)
    
    def _create_analysis_prompt(
        self,
        question: str,
        context: str,
        max_response_length: Optional[int] = None
    ) -> str:
        """
        Create optimized prompt for SEC filing analysis.
        
        Args:
            question: User's question
            context: Prepared context
            max_response_length: Maximum response length
            
        Returns:
            Formatted prompt
        """
        length_instruction = ""
        if max_response_length:
            length_instruction = f"Keep your response under {max_response_length} characters. "
        
        prompt = f"""You are an expert financial analyst specializing in SEC filings. You help investors and analysts understand complex financial documents by providing accurate, detailed, and insightful analysis.

CONTEXT:
{context}

QUESTION: {question}

INSTRUCTIONS:
1. Analyze the provided SEC filing excerpts carefully
2. Answer the question based ONLY on the information provided in the context
3. If the information isn't available in the context, clearly state that
4. Provide specific details, numbers, and quotes when available
5. Be precise and professional in your response
6. {length_instruction}Structure your response clearly with relevant headings if needed

IMPORTANT GUIDELINES:
- Only use information from the provided context
- Quote specific excerpts when making claims
- If asking about financial numbers, provide exact figures when available
- Explain financial terminology when necessary
- Highlight any limitations in the available data

RESPONSE:"""
        
        return prompt
    
    async def _generate_response(self, prompt: str) -> str:
        """
        Generate response using Google Gemini.
        
        Args:
            prompt: Formatted prompt
            
        Returns:
            Generated response text
            
        Raises:
            AIServiceError: If generation fails
        """
        try:
            # Generate content using Gemini
            response = self.client.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.1,  # Low temperature for factual responses
                    top_p=0.8,
                    top_k=40,
                    max_output_tokens=self.settings.max_response_length or 4000,
                )
            )
            
            if not response.text:
                raise AIServiceError("Empty response from Gemini API")
            
            return response.text.strip()
            
        except Exception as e:
            raise AIServiceError(f"Failed to generate response: {str(e)}")
    
    def _parse_response(
        self, 
        response_text: str, 
        context_docs: List[Document]
    ) -> Dict[str, Any]:
        """
        Parse and structure the AI response.
        
        Args:
            response_text: Raw response from Gemini
            context_docs: Context documents used
            
        Returns:
            Structured response dictionary
        """
        # Calculate confidence score based on response characteristics
        confidence_score = self._calculate_confidence_score(response_text, context_docs)
        
        # Extract context information
        context_info = []
        for doc in context_docs[:5]:  # Top 5 for response
            context_info.append({
                "chunk_id": doc.metadata.get("chunk_id", 0),
                "source": doc.metadata.get("source_url", ""),
                "relevance": "high"  # Could be enhanced with scoring
            })
        
        return {
            "answer": response_text,
            "confidence_score": confidence_score,
            "context_used": context_info,
            "model_info": {
                "model": self.settings.gemini_model,
                "provider": "Google Gemini"
            }
        }
    
    def _calculate_confidence_score(
        self, 
        response: str, 
        context_docs: List[Document]
    ) -> float:
        """
        Calculate confidence score for the response.
        
        Args:
            response: Generated response
            context_docs: Context documents
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        try:
            score = 0.5  # Base score
            
            # Check if response indicates uncertainty
            uncertainty_phrases = [
                "not available", "not provided", "unclear", "cannot determine",
                "insufficient information", "not specified", "unknown"
            ]
            
            if any(phrase in response.lower() for phrase in uncertainty_phrases):
                score -= 0.2
            
            # Check for specific data/numbers (indicates concrete information)
            import re
            if re.search(r'\$[\d,]+|\d+%|\d{4}-\d{2}-\d{2}', response):
                score += 0.2
            
            # Check context availability
            if len(context_docs) >= 3:
                score += 0.1
            elif len(context_docs) == 0:
                score -= 0.3
            
            # Check response length (very short might indicate lack of info)
            if len(response) < 100:
                score -= 0.1
            elif len(response) > 300:
                score += 0.1
            
            # Ensure score is within bounds
            return max(0.0, min(1.0, score))
            
        except Exception:
            return 0.5  # Default score if calculation fails
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on AI service.
        
        Returns:
            Health status dictionary
        """
        try:
            # Test with simple prompt
            test_prompt = "Respond with 'OK' if you can process this request."
            response = self.client.generate_content(test_prompt)
            
            if response.text and "OK" in response.text:
                return {
                    "status": "healthy",
                    "model": self.settings.gemini_model,
                    "provider": "Google Gemini"
                }
            else:
                return {
                    "status": "degraded",
                    "model": self.settings.gemini_model,
                    "provider": "Google Gemini",
                    "issue": "Unexpected response format"
                }
                
        except Exception as e:
            return {
                "status": "unhealthy",
                "model": self.settings.gemini_model,
                "provider": "Google Gemini",
                "error": str(e)
            }
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the AI model.
        
        Returns:
            Model information dictionary
        """
        return {
            "model_name": self.settings.gemini_model,
            "provider": "Google Gemini",
            "type": "Large Language Model",
            "capabilities": [
                "Text analysis",
                "Question answering",
                "Financial document understanding",
                "Context-aware responses"
            ],
            "max_tokens": self.settings.max_response_length or 4000
        } 