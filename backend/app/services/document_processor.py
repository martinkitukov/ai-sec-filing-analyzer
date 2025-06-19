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
from langchain_core.documents import Document

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
        Fetch and process SEC filing from URL.
        
        Args:
            filing_url: URL to SEC filing
            
        Returns:
            List of processed document chunks
            
        Raises:
            DocumentProcessingError: If processing fails
        """
        try:
            # Validate URL
            self._validate_sec_url(filing_url)
            
            # Try different format strategies
            chunks = await self._try_multiple_formats(filing_url)
            
            if not chunks:
                raise DocumentProcessingError("No content could be extracted from any format")
                
            return chunks
            
        except Exception as e:
            raise DocumentProcessingError(f"Failed to process filing: {str(e)}")

    async def _try_multiple_formats(self, base_url: str) -> List[Document]:
        """
        Try multiple SEC filing formats for best content extraction.
        
        Args:
            base_url: Original filing URL
            
        Returns:
            List of document chunks from best available format
        """
        strategies = [
            ("HTML Direct", self._try_html_format),
            ("Text Format", self._try_text_format), 
            ("Original Format", self._try_original_format)
        ]
        
        best_chunks = []
        best_content_length = 0
        
        for strategy_name, strategy_func in strategies:
            try:
                chunks = await strategy_func(base_url)
                
                if chunks:
                    # Calculate total content length
                    total_length = sum(len(chunk.page_content) for chunk in chunks)
                    
                    if total_length > best_content_length:
                        best_chunks = chunks
                        best_content_length = total_length
                        print(f"✅ Best format so far: {strategy_name} ({total_length} chars)")
                        
                        # If we get substantial content, we can stop
                        if total_length > 5000:
                            break
                            
            except Exception as e:
                print(f"❌ {strategy_name} failed: {str(e)}")
                continue
                
        return best_chunks

    async def _try_html_format(self, url: str) -> List[Document]:
        """Try to get HTML format of the filing."""
        # Convert XBRL URLs to direct HTML
        if "/ix?doc=" in url:
            # Extract the document path and convert to direct HTML
            doc_path = url.split("/ix?doc=")[1]
            # Remove any query parameters
            doc_path = doc_path.split('?')[0]
            html_url = f"https://www.sec.gov{doc_path}"
        else:
            html_url = url
            
        print(f"🔍 Trying HTML direct URL: {html_url}")
        raw_content = await self._fetch_document(html_url)
        
        # Validate we got actual filing content, not XBRL viewer
        if "viewing request" in raw_content.lower() and len(raw_content) < 5000:
            raise DocumentProcessingError("HTML format returned XBRL viewer or insufficient content")
        
        cleaned_text = self._parse_sec_filing(raw_content)
        metadata = self._extract_filing_metadata(raw_content, html_url)
        metadata["format"] = "HTML Direct"
        
        return self._create_chunks(cleaned_text, metadata)

    async def _try_text_format(self, url: str) -> List[Document]:
        """Try to get text format of the filing."""
        # Convert to .txt format with better path handling
        if "/ix?doc=" in url:
            # Extract path from XBRL URL: /ix?doc=/Archives/edgar/...
            doc_path = url.split("/ix?doc=")[1]
            # Remove any query parameters and convert to .txt
            doc_path = doc_path.split('?')[0]  # Remove query params
            if doc_path.endswith('.htm') or doc_path.endswith('.html'):
                doc_path = doc_path.rsplit('.', 1)[0] + '.txt'
            txt_url = f"https://www.sec.gov{doc_path}"
        elif url.endswith('.htm') or url.endswith('.html'):
            txt_url = url.rsplit('.', 1)[0] + '.txt'
        else:
            txt_url = url
            
        print(f"🔍 Trying text format URL: {txt_url}")
        raw_content = await self._fetch_document(txt_url)
        
        # Validate we got actual filing content, not error pages
        if len(raw_content) < 1000 or ("viewing request" in raw_content.lower() and len(raw_content) < 5000):
            raise DocumentProcessingError("Text format returned insufficient content")
        
        # Text format needs minimal processing
        cleaned_text = self._clean_text(raw_content)
        metadata = self._extract_text_filing_metadata(raw_content, txt_url)
        metadata["format"] = "Text Format"
        
        return self._create_chunks(cleaned_text, metadata)

    async def _try_original_format(self, url: str) -> List[Document]:
        """Try the original URL as provided."""
        raw_content = await self._fetch_document(url)
        cleaned_text = self._parse_sec_filing(raw_content)
        metadata = self._extract_filing_metadata(raw_content, url)
        metadata["format"] = "Original"
        
        return self._create_chunks(cleaned_text, metadata)

    def _extract_text_filing_metadata(self, content: str, url: str) -> Dict[str, str]:
        """Extract metadata from text format SEC filing."""
        metadata = {"source_url": url}
        
        try:
            # Text format has structured headers
            lines = content.split('\n')[:50]  # Check first 50 lines
            
            for line in lines:
                line = line.strip()
                
                if line.startswith("COMPANY CONFORMED NAME:"):
                    metadata["company_name"] = line.split(":", 1)[1].strip()
                elif line.startswith("FORM TYPE:"):
                    metadata["form_type"] = line.split(":", 1)[1].strip()
                elif line.startswith("FILED AS OF DATE:"):
                    metadata["filing_date"] = line.split(":", 1)[1].strip()
                elif line.startswith("PERIOD OF REPORT:"):
                    metadata["period_end_date"] = line.split(":", 1)[1].strip()
                    
        except Exception:
            pass
            
        return metadata
    
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
        url_string = str(url).lower()
        if not any(path.lower() in url_string for path in valid_paths):
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
            "User-Agent": "AI SEC Filing Analyzer v1.0 Educational Research Tool - Contact: developer@example.com",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "From": "developer@example.com"
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
        # Parse HTML/XML content (suppress warnings for mixed content)
        import warnings
        from bs4 import XMLParsedAsHTMLWarning
        warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
        
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
        # Suppress XML warnings for metadata parsing too
        import warnings
        from bs4 import XMLParsedAsHTMLWarning
        warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
        
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