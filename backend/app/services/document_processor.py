"""
Document Processing Service for SEC Filing Analysis.

This service handles fetching, parsing, and chunking SEC filings
for AI analysis and vector embedding generation.
"""

import re
import tempfile
import aiofiles
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

from app.utils.exceptions import DocumentProcessingError
from app.core.config import Settings


class DocumentProcessor:
    """
    Service for processing SEC filing documents.
    
    Handles document fetching, parsing, cleaning, and chunking
    for optimal AI analysis and vector embedding generation.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize document processor.
        
        Args:
            settings: Application configuration
        """
        self.settings = settings
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            separators=["\n\n", "\n", ".", "!", "?", ";", " ", ""]
        )
        
    async def fetch_and_process_filing(self, filing_url: str) -> List[Document]:
        """
        Fetch SEC filing and process into chunks for analysis.
        
        Args:
            filing_url: URL to SEC filing document
            
        Returns:
            List of processed document chunks
            
        Raises:
            DocumentProcessingError: If document cannot be fetched or processed
        """
        try:
            # Validate URL
            self._validate_sec_url(filing_url)
            
            # Fetch document content
            raw_content = await self._fetch_document(filing_url)
            
            # Parse and clean content
            cleaned_text = self._parse_sec_filing(raw_content)
            
            # Extract metadata
            metadata = self._extract_filing_metadata(raw_content, filing_url)
            
            # Split into chunks
            chunks = self._create_chunks(cleaned_text, metadata)
            
            return chunks
            
        except Exception as e:
            raise DocumentProcessingError(f"Failed to process filing: {str(e)}")
    
    def _validate_sec_url(self, url: str) -> None:
        """
        Validate that URL is a valid SEC filing URL.
        
        Args:
            url: URL to validate
            
        Raises:
            DocumentProcessingError: If URL is invalid
        """
        parsed = urlparse(url)
        
        if not parsed.scheme or not parsed.netloc:
            raise DocumentProcessingError("Invalid URL format")
            
        # Check if it's an SEC domain
        valid_domains = ["sec.gov", "www.sec.gov"]
        if parsed.netloc.lower() not in valid_domains:
            raise DocumentProcessingError("URL must be from sec.gov domain")
            
        # Check for common SEC filing paths
        valid_paths = ["/Archives/edgar/", "/ix?doc="]
        if not any(path in parsed.path for path in valid_paths):
            raise DocumentProcessingError("URL does not appear to be a SEC filing")
    
    async def _fetch_document(self, url: str) -> str:
        """
        Fetch document content from URL.
        
        Args:
            url: Document URL
            
        Returns:
            Raw document content
            
        Raises:
            DocumentProcessingError: If document cannot be fetched
        """
        headers = {
            "User-Agent": "AI SEC Filing Analyzer 1.0 (https://github.com/your-repo)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive"
        }
        
        try:
            async with httpx.AsyncClient(
                timeout=self.settings.request_timeout,
                follow_redirects=True
            ) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                
                # Handle different content types
                content_type = response.headers.get("content-type", "").lower()
                
                if "text/html" in content_type or "text/xml" in content_type:
                    return response.text
                elif "text/plain" in content_type:
                    return response.text
                else:
                    # Try to decode as text anyway
                    try:
                        return response.text
                    except:
                        raise DocumentProcessingError(f"Unsupported content type: {content_type}")
                        
        except httpx.TimeoutException:
            raise DocumentProcessingError("Request timeout while fetching document")
        except httpx.HTTPStatusError as e:
            raise DocumentProcessingError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            raise DocumentProcessingError(f"Failed to fetch document: {str(e)}")
    
    def _parse_sec_filing(self, content: str) -> str:
        """
        Parse and clean SEC filing content.
        
        Args:
            content: Raw filing content
            
        Returns:
            Cleaned text content
        """
        # Parse HTML/XML content
        soup = BeautifulSoup(content, 'lxml')
        
        # Remove unwanted elements
        for tag in soup.find_all(['script', 'style', 'meta', 'link']):
            tag.decompose()
        
        # Extract text content
        text = soup.get_text()
        
        # Clean up the text
        text = self._clean_text(text)
        
        return text
    
    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize text content.
        
        Args:
            text: Raw text
            
        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove control characters
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        
        # Remove repeated punctuation
        text = re.sub(r'([.!?])\1+', r'\1', text)
        
        # Normalize line breaks
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def _extract_filing_metadata(self, content: str, url: str) -> Dict[str, str]:
        """
        Extract metadata from SEC filing.
        
        Args:
            content: Raw filing content
            url: Filing URL
            
        Returns:
            Metadata dictionary
        """
        soup = BeautifulSoup(content, 'lxml')
        metadata = {"source_url": url}
        
        # Try to extract common SEC filing metadata
        try:
            # Look for company name
            company_tag = soup.find(text=re.compile(r"COMPANY\s+CONFORMED\s+NAME:", re.I))
            if company_tag:
                company_line = company_tag.parent.get_text() if company_tag.parent else str(company_tag)
                company_match = re.search(r"COMPANY\s+CONFORMED\s+NAME:\s*(.+)", company_line, re.I)
                if company_match:
                    metadata["company_name"] = company_match.group(1).strip()
            
            # Look for filing type
            form_tag = soup.find(text=re.compile(r"FORM\s+TYPE:", re.I))
            if form_tag:
                form_line = form_tag.parent.get_text() if form_tag.parent else str(form_tag)
                form_match = re.search(r"FORM\s+TYPE:\s*(.+)", form_line, re.I)
                if form_match:
                    metadata["form_type"] = form_match.group(1).strip()
            
            # Look for filing date
            date_tag = soup.find(text=re.compile(r"FILED\s+AS\s+OF\s+DATE:", re.I))
            if date_tag:
                date_line = date_tag.parent.get_text() if date_tag.parent else str(date_tag)
                date_match = re.search(r"FILED\s+AS\s+OF\s+DATE:\s*(.+)", date_line, re.I)
                if date_match:
                    metadata["filing_date"] = date_match.group(1).strip()
                    
        except Exception:
            # If metadata extraction fails, continue with basic metadata
            pass
        
        return metadata
    
    def _create_chunks(self, text: str, metadata: Dict[str, str]) -> List[Document]:
        """
        Split text into chunks for vector embedding.
        
        Args:
            text: Cleaned text content
            metadata: Document metadata
            
        Returns:
            List of document chunks
        """
        # Split text into chunks
        chunks = self.text_splitter.split_text(text)
        
        # Create Document objects with metadata
        documents = []
        for i, chunk in enumerate(chunks):
            if len(chunk.strip()) > 50:  # Skip very short chunks
                chunk_metadata = metadata.copy()
                chunk_metadata.update({
                    "chunk_id": i,
                    "chunk_length": len(chunk),
                    "total_chunks": len(chunks)
                })
                
                documents.append(Document(
                    page_content=chunk,
                    metadata=chunk_metadata
                ))
        
        # Limit number of chunks to prevent memory issues
        if len(documents) > self.settings.max_chunks:
            documents = documents[:self.settings.max_chunks]
        
        return documents
    
    async def save_temp_file(self, content: str, suffix: str = ".txt") -> str:
        """
        Save content to temporary file.
        
        Args:
            content: Content to save
            suffix: File suffix
            
        Returns:
            Path to temporary file
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False) as f:
            f.write(content)
            return f.name 