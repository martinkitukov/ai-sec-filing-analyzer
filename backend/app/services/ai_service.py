"""
AI Service for Google Gemini Integration.

This service handles interactions with Google's Gemini AI model
for SEC filing analysis and question answering.
"""

import logging
from typing import Dict, Any, List, Optional
import google.generativeai as genai
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
            if not self.settings.google_api_key or self.settings.google_api_key == "your_google_api_key_here":
                logging.warning("Google API key not configured - AI features will be limited")
                self.client = None
                return
            
            # Configure the client
            genai.configure(api_key=self.settings.google_api_key)
            self.client = genai.GenerativeModel(self.settings.gemini_model)
            
            logging.info(f"AI service initialized with model: {self.settings.gemini_model}")
            
        except Exception as e:
            logging.error(f"Failed to initialize Google Gemini client: {str(e)}")
            self.client = None
    
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
            if not self.client:
                return {
                    "answer": "AI service is not available. Please configure your Google API key in the .env file.",
                    "confidence_score": 0.0,
                    "context_used": [],
                    "model_info": {
                        "model": "unavailable",
                        "provider": "Google Gemini (not configured)"
                    }
                }
            
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
        Create optimized prompt for SEC filing analysis with enhanced length control.
        
        Args:
            question: User's question
            context: Prepared context
            max_response_length: Maximum response length
            
        Returns:
            Formatted prompt
        """
        # Detect if user wants a very short response
        is_short_request = any(phrase in question.lower() for phrase in [
            "in 1 sentence", "in one sentence", "briefly", "summarize in", 
            "what is this about", "concisely", "in a sentence"
        ])
        
        length_instruction = ""
        if is_short_request:
            length_instruction = "CRITICAL: Provide EXACTLY ONE SENTENCE as requested. Do not exceed one sentence. "
        elif max_response_length:
            length_instruction = f"Keep your response under {max_response_length} characters. "
        
        # Check if this appears to be a financial data question
        is_financial_question = any(term in question.lower() for term in [
            'revenue', 'income', 'profit', 'loss', 'assets', 'liabilities', 'cash', 'debt',
            'earnings', 'sales', 'net income', 'total assets', 'equity', 'balance sheet',
            'financial', 'q1', 'quarter', '2024', '2025', 'fiscal', 'million', 'billion'
        ])
        
        financial_instructions = ""
        if is_financial_question:
            financial_instructions = """
CRITICAL FINANCIAL DATA ANALYSIS INSTRUCTIONS:
- PRIORITIZE 2025 DATA OVER 2024 OR ANY OLDER DATA
- When extracting financial numbers from XBRL/HTML, focus on elements with recent dates
- Look for contextref attributes containing "2025", "Q1 2025", "2025-03-31", or similar recent periods
- If you see both 2024 and 2025 data for the same metric, ALWAYS choose 2025
- Pay special attention to ix:nonfraction tags and similar XBRL elements with current period contexts
- Extract exact financial values with proper scale (millions, billions) when available
- Include the time period/context for any financial figures you report
"""
        
        # Enhanced prompt with better financial context understanding
        prompt = f"""You are an expert financial analyst specializing in SEC filings. You help investors and analysts understand complex financial documents by providing accurate, detailed, and insightful analysis.

DOCUMENT CONTEXT:
{context}

USER QUESTION: {question}

ANALYSIS INSTRUCTIONS:
1. {length_instruction}
2. Analyze the provided SEC filing information carefully{financial_instructions}
3. Answer based ONLY on the information provided in the context
4. If the information isn't available in the context, clearly state that
5. For financial documents, focus on business operations, financial metrics, and corporate purpose
6. Provide specific details, numbers, and quotes when available
7. Be precise and professional in your response

IMPORTANT GUIDELINES:
- Only use information from the provided context
- For XBRL/structured data: Extract financial numbers intelligently from the HTML/XBRL structure
- When you see HTML content with XBRL tags, parse them to find the actual financial values
- Quote specific excerpts when making claims
- If asking about financial numbers, provide exact figures when available with their time periods
- If this is a summary request, prioritize the main business purpose and document type
- Highlight any limitations in the available data
- When analyzing raw HTML/XBRL content, focus on extracting meaningful financial data rather than describing the technical structure

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
            if not self.client:
                raise AIServiceError("Google Gemini client not initialized")
            
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
        
        # Extract context information in DocumentChunk format
        context_info = []
        for i, doc in enumerate(context_docs[:5]):  # Top 5 for response
            context_info.append({
                "content": doc.page_content[:500] + "..." if len(doc.page_content) > 500 else doc.page_content,
                "chunk_id": str(doc.metadata.get("chunk_id", f"chunk_{i}")),
                "similarity_score": 0.8,  # Default high relevance
                "page_number": doc.metadata.get("page_number"),
                "metadata": {
                    "source": doc.metadata.get("source_url", ""),
                    "relevance": "high"
                }
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
            if not self.client:
                return {
                    "status": "not_configured",
                    "model": self.settings.gemini_model,
                    "provider": "Google Gemini",
                    "issue": "API key not configured"
                }
            
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