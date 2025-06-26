"""
Document Processing Service for SEC Filing Analysis.

This service handles fetching, parsing, and chunking SEC filings
for AI analysis and vector embedding generation.
"""

import logging
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

logger = logging.getLogger(__name__)


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
        
        # Comprehensive financial tags mapping with priority scores
        self.financial_tags = {
            # Core Financial Metrics (High Priority)
            'Assets': {'label': 'Total Assets', 'priority': 100, 'aliases': ['TotalAssets']},
            'Revenues': {'label': 'Total Revenues', 'priority': 95, 'aliases': ['Revenue', 'SalesRevenueNet', 'RevenueFromContractWithCustomerExcludingAssessedTax']},
            'Revenue': {'label': 'Revenue', 'priority': 95, 'aliases': ['Revenues', 'SalesRevenueNet']},
            'NetIncomeLoss': {'label': 'Net Income', 'priority': 90, 'aliases': ['NetIncomeLossAvailableToCommonStockholdersBasic', 'NetIncomeLossAttributableToParent']},
            'OperatingIncomeLoss': {'label': 'Operating Income', 'priority': 85, 'aliases': ['OperatingIncome', 'IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest']},
            'GrossProfit': {'label': 'Gross Profit', 'priority': 80, 'aliases': ['GrossProfitLoss']},
            
            # Balance Sheet Items (Medium-High Priority)
            'Liabilities': {'label': 'Total Liabilities', 'priority': 75, 'aliases': ['LiabilitiesAndStockholdersEquity']},
            'StockholdersEquity': {'label': 'Stockholders Equity', 'priority': 70, 'aliases': ['StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest']},
            'AssetsCurrent': {'label': 'Current Assets', 'priority': 65, 'aliases': []},
            'LiabilitiesCurrent': {'label': 'Current Liabilities', 'priority': 65, 'aliases': []},
            'CashAndCashEquivalents': {'label': 'Cash and Cash Equivalents', 'priority': 60, 'aliases': ['CashCashEquivalentsAndShortTermInvestments']},
            
            # Income Statement Items (Medium Priority)
            'CostOfRevenue': {'label': 'Cost of Revenue', 'priority': 55, 'aliases': ['CostOfGoodsAndServicesSold', 'CostOfSales']},
            'CostOfGoodsAndServicesSold': {'label': 'Cost of Goods Sold', 'priority': 55, 'aliases': ['CostOfRevenue', 'CostOfSales']},
            'ResearchAndDevelopmentExpense': {'label': 'Research and Development', 'priority': 50, 'aliases': []},
            'SellingGeneralAndAdministrativeExpenses': {'label': 'SG&A Expenses', 'priority': 50, 'aliases': []},
            
            # Cash Flow Items (Medium Priority)
            'NetCashProvidedByUsedInOperatingActivities': {'label': 'Operating Cash Flow', 'priority': 45, 'aliases': []},
            'NetCashProvidedByUsedInInvestingActivities': {'label': 'Investing Cash Flow', 'priority': 40, 'aliases': []},
            'NetCashProvidedByUsedInFinancingActivities': {'label': 'Financing Cash Flow', 'priority': 40, 'aliases': []},
            
            # Per Share Data (Lower Priority)
            'EarningsPerShareBasic': {'label': 'Basic EPS', 'priority': 35, 'aliases': []},
            'EarningsPerShareDiluted': {'label': 'Diluted EPS', 'priority': 35, 'aliases': []},
            'WeightedAverageNumberOfSharesOutstandingBasic': {'label': 'Basic Shares Outstanding', 'priority': 30, 'aliases': []},
            'WeightedAverageNumberOfDilutedSharesOutstanding': {'label': 'Diluted Shares Outstanding', 'priority': 30, 'aliases': []},
        }
        
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
        Try multiple SEC filing formats for best content extraction with improved error handling.
        
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
        last_error = None
        successful_formats = []
        
        for strategy_name, strategy_func in strategies:
            try:
                print(f"🔄 Attempting {strategy_name}...")
                chunks = await strategy_func(base_url)
                
                if chunks:
                    # Calculate total content length
                    total_length = sum(len(chunk.page_content) for chunk in chunks)
                    
                    if total_length > best_content_length:
                        best_chunks = chunks
                        best_content_length = total_length
                        print(f"✅ Best format so far: {strategy_name} ({total_length:,} chars)")
                        
                        # If we get substantial content, we can stop early
                        if total_length > 10000:  # Increased threshold for better content
                            successful_formats.append(strategy_name)
                            break
                    
                    successful_formats.append(strategy_name)
                else:
                    print(f"⚠️ {strategy_name} returned no content")
                    
            except Exception as e:
                error_msg = str(e)
                print(f"❌ {strategy_name} failed: {error_msg}")
                last_error = e
                
                # If it's a rate limiting error, wait before trying next format
                if any(phrase in error_msg.lower() for phrase in ["rate limit", "403", "automated tool"]):
                    print("⏳ SEC rate limiting detected, waiting 5 seconds before next attempt...")
                    import asyncio
                    await asyncio.sleep(5)
                
                continue
        
        # Provide detailed feedback
        if best_chunks:
            print(f"🎯 Final result: {len(best_chunks)} chunks from {successful_formats[0] if successful_formats else 'unknown'}")
            return best_chunks
        else:
            error_msg = f"No content could be extracted from any format. Last error: {last_error}"
            if "rate limit" in str(last_error).lower():
                error_msg += " (SEC rate limiting may be active - try again in a few minutes)"
            raise DocumentProcessingError(error_msg)

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
        Validate that URL is from SEC website.
        
        Args:
            url: URL to validate
            
        Raises:
            DocumentProcessingError: If URL is invalid
        """
        try:
            parsed = urlparse(url)
            if not parsed.netloc.endswith('sec.gov'):
                raise DocumentProcessingError(
                    f"URL must be from SEC website (sec.gov), got: {parsed.netloc}"
                )
            if not parsed.scheme in ['http', 'https']:
                raise DocumentProcessingError(
                    f"URL must use HTTP or HTTPS protocol, got: {parsed.scheme}"
                )
        except Exception as e:
            raise DocumentProcessingError(f"Invalid URL format: {str(e)}")

    async def _fetch_document(self, url: str) -> str:
        """
        Fetch document content from URL with proper SEC compliance.
        
        Args:
            url: Document URL
            
        Returns:
            Raw document content
            
        Raises:
            DocumentProcessingError: If fetch fails
        """
        # SEC-compliant headers per https://www.sec.gov/developer
        headers = {
            'User-Agent': 'AI SEC Filing Analyzer - Educational Research Tool (contact: research@example.com)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,text/plain;q=0.8,*/*;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        
        try:
            # SEC rate limiting: max 10 requests per second
            import asyncio
            await asyncio.sleep(0.2)  # 200ms delay = max 5 requests/second (well under limit)
            
            timeout = httpx.Timeout(45.0, connect=15.0)  # Increased timeout for large filings
            async with httpx.AsyncClient(
                timeout=timeout, 
                headers=headers,
                follow_redirects=True,
                max_redirects=5
            ) as client:
                print(f"🌐 Fetching: {url}")
                response = await client.get(url)
                
                # Handle specific SEC error responses
                if response.status_code == 403:
                    if "rate threshold" in response.text.lower():
                        raise DocumentProcessingError("SEC rate limit exceeded. Please wait before retrying.")
                    elif "automated tool" in response.text.lower():
                        raise DocumentProcessingError("SEC detected automated access. Request may be blocked temporarily.")
                    else:
                        raise DocumentProcessingError(f"SEC access forbidden (403). Content: {response.text[:200]}...")
                
                response.raise_for_status()
                
                # Validate content length and type
                content = response.text
                if len(content) < 100:
                    raise DocumentProcessingError(f"Document too short: {len(content)} characters")
                
                # Check for SEC error pages in content
                content_lower = content.lower()
                if any(error_phrase in content_lower for error_phrase in [
                    "request rate threshold exceeded",
                    "automated tool",
                    "reference id:",
                    "sec.gov privacy policy"
                ]):
                    raise DocumentProcessingError("SEC returned an error page instead of filing content")
                
                print(f"✅ Successfully fetched {len(content)} characters")
                return content
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                raise DocumentProcessingError("SEC access denied - please check rate limits and User-Agent compliance")
            elif e.response.status_code == 404:
                raise DocumentProcessingError("Filing not found at the specified URL")
            elif e.response.status_code >= 500:
                raise DocumentProcessingError("SEC server error - please try again later")
            else:
                raise DocumentProcessingError(f"HTTP error {e.response.status_code}: {e.response.reason_phrase}")
        except httpx.TimeoutException:
            raise DocumentProcessingError("Request timeout - filing may be very large or SEC servers slow")
        except Exception as e:
            raise DocumentProcessingError(f"Failed to fetch document: {str(e)}")

    def _parse_sec_filing(self, content: str) -> str:
        """
        Parse SEC filing content with enhanced XBRL processing.
        
        Args:
            content: Raw filing content
            
        Returns:
            Cleaned and processed text
        """
        # Suppress XML warnings during parsing
        import warnings
        from bs4 import XMLParsedAsHTMLWarning
        warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
        
        soup = BeautifulSoup(content, 'lxml')
        
        # Enhanced XBRL detection and processing
        if self._is_xbrl_document(soup):
            return self._parse_xbrl_content(soup)
        else:
            return self._parse_html_content(soup)

    def _is_xbrl_document(self, soup) -> bool:
        """Enhanced XBRL document detection."""
        # Check for multiple XBRL indicators
        xbrl_indicators = [
            soup.find_all(lambda tag: tag.name and ('ix:' in tag.name or 'xbrl:' in tag.name)),
            soup.find_all(attrs={'name': lambda x: x and 'us-gaap:' in x.lower()}),
            soup.find_all(attrs={'contextref': True}),
            soup.find_all('nonfraction'),
            soup.find('html', attrs={'xmlns:ix': True}),
        ]
        
        return any(indicators for indicators in xbrl_indicators)

    def _parse_xbrl_content(self, soup) -> str:
        """
        Enhanced XBRL content parsing - now passes raw HTML to AI for intelligent analysis.
        
        Args:
            soup: BeautifulSoup parsed content
            
        Returns:
            Structured text with comprehensive content for AI analysis
        """
        sections = []
        
        try:
            # 1. HIGHEST PRIORITY: Extract Financial Statements with Actual Numbers
            financial_statements = self._extract_financial_statements_with_numbers(soup)
            if financial_statements:
                sections.append("=== PRIORITY: FINANCIAL STATEMENTS WITH NUMBERS ===")
                sections.append(financial_statements)
            
            # 2. Document Entity Information (DEI) - keep this for basic metadata
            dei_info = self._extract_dei_information(soup)
            if dei_info:
                sections.append("=== DOCUMENT INFORMATION ===")
                sections.append(dei_info)
            
            # 3. Extract Financial Statement Sections from HTML tables
            financial_tables = self._extract_financial_table_sections(soup)
            if financial_tables:
                sections.append("=== FINANCIAL TABLE SECTIONS ===")
                sections.append(financial_tables)
            
            # 4. Extract XBRL Financial Elements (structured data)
            financial_elements = self._extract_xbrl_financial_elements(soup)
            if financial_elements:
                sections.append("=== XBRL FINANCIAL ELEMENTS ===")
                sections.append(financial_elements)
            
            # 5. Business context and narrative
            business_context = self._extract_business_context(soup)
            if business_context:
                sections.append("=== BUSINESS CONTEXT ===")
                sections.append(business_context)
            
            # 6. Risk factors and important disclosures
            risk_info = self._extract_risk_factors(soup)
            if risk_info:
                sections.append("=== RISK FACTORS ===")
                sections.append(risk_info)
                
            # 7. Add the full HTML for comprehensive AI analysis
            # But limit it to prevent overwhelming the AI
            html_content = str(soup)[:50000]  # Limit to first 50KB
            sections.append("=== FULL DOCUMENT HTML FOR AI ANALYSIS ===")
            sections.append(html_content)
            
            result = '\n\n'.join(sections)
            logger.info(f"📄 XBRL content parsed: {len(result)} characters across {len(sections)} sections")
            return result
            
        except Exception as e:
            logger.error(f"Error parsing XBRL content: {str(e)}")
            # Fallback to basic HTML content
            return soup.get_text()[:10000]

    def _extract_financial_statements_with_numbers(self, soup) -> str:
        """Extract financial statement tables with actual numerical data."""
        financial_data = []
        
        # Look for tables with financial data
        tables = soup.find_all(['table', 'div'], class_=lambda x: x and any(
            term in str(x).lower() for term in ['financial', 'statement', 'consolidated', 'operations', 'income']
        ))
        
        # Also look for XBRL inline elements with actual numbers
        xbrl_elements = soup.find_all(['span', 'ix:nonfraction', 'ix:nonNumeric'], 
                                    attrs={'name': True})
        
        # Process XBRL elements first (most reliable)
        financial_values = {}
        for element in xbrl_elements:
            name = element.get('name', '')
            if any(term in name.lower() for term in [
                'netincome', 'revenue', 'operating', 'earnings', 'assets', 'liabilities'
            ]):
                text = element.get_text(strip=True)
                context = element.get('contextref', '')
                
                # Prioritize 2025 contexts
                if '2025' in context and text and any(c.isdigit() for c in text):
                    financial_values[name] = {
                        'value': text,
                        'context': context,
                        'priority': 100 if 'q1' in context.lower() or '2025-03-31' in context else 50
                    }
        
        if financial_values:
            financial_data.append("=== XBRL FINANCIAL VALUES ===")
            # Sort by priority
            for name, data in sorted(financial_values.items(), 
                                   key=lambda x: x[1]['priority'], reverse=True):
                financial_data.append(f"{name}: {data['value']} (Context: {data['context']})")
        
        # Process tables with numbers
        for table in tables:
            table_text = table.get_text(separator=' ', strip=True)
            
            # Look for patterns that indicate financial statements
            if any(pattern in table_text.lower() for pattern in [
                'consolidated statements of operations',
                'consolidated statements of income',
                'net income',
                'three months ended march 31',
                'q1 2025'
            ]) and any(c.isdigit() for c in table_text):
                
                # Extract rows with numerical data
                rows = table.find_all('tr')
                table_data = []
                
                for row in rows:
                    row_text = row.get_text(separator=' | ', strip=True)
                    # Include rows that have both text and numbers
                    if (any(c.isdigit() for c in row_text) and 
                        any(term in row_text.lower() for term in [
                            'revenue', 'income', 'loss', 'earnings', 'operating'
                        ])):
                        table_data.append(row_text)
                
                if table_data:
                    financial_data.append("=== FINANCIAL STATEMENT TABLE ===")
                    financial_data.extend(table_data[:10])  # Limit to prevent overflow
        
        # Look for specific financial metrics in paragraph text
        paragraphs = soup.find_all(['p', 'div'], string=lambda text: text and any(
            pattern in text.lower() for pattern in [
                'net income', 'net loss', 'total revenue', 'first quarter'
            ]
        ))
        
        for p in paragraphs[:5]:  # Limit to prevent overflow
            text = p.get_text(strip=True)
            if any(c.isdigit() for c in text) and '2025' in text:
                financial_data.append(f"Financial context: {text}")
        
        return '\n'.join(financial_data) if financial_data else ""

    def _extract_xbrl_financial_elements(self, soup) -> str:
        """Extract specific XBRL financial elements."""
        financial_data = []
        
        # Key financial metrics to look for
        financial_tags = [
            'us-gaap:netincomeloss',
            'us-gaap:revenues',
            'us-gaap:revenuefromcontractwithcustomerexcludingassessedtax',
            'us-gaap:operatingincomeloss',
            'us-gaap:assets',
            'us-gaap:liabilities',
            'us-gaap:stockholdersequity',
            'us-gaap:earningspersharebasic',
            'us-gaap:earningspershtarediluted',
            'tsla:automotiverevenues',  # Tesla-specific tags
            'tsla:energygenerationandstoragerevenues'
        ]
        
        for tag_name in financial_tags:
            elements = soup.find_all(tag_name.split(':')[-1])  # Find by tag name without namespace
            if not elements:
                # Try with full namespace
                elements = soup.find_all(tag_name)
            
            for element in elements:
                value = element.get_text(strip=True)
                context = element.get('contextref', 'Unknown')
                if value and len(value) > 0:
                    financial_data.append(f"{tag_name}: {value} (Context: {context})")
        
        return "\n".join(financial_data)

    def _extract_targeted_html_content(self, soup) -> str:
        """Extract targeted HTML content focusing on financial and business sections."""
        # Remove excessive script/style content but keep structure
        for tag in soup.find_all(['script', 'style']):
            tag.decompose()
        
        # Focus on main content areas
        main_content = []
        
        # Look for main content containers
        content_containers = soup.find_all(['div', 'section', 'article', 'main', 'body'])
        
        # Prioritize content with financial keywords
        for container in content_containers:
            text = container.get_text()
            if any(keyword in text.lower() for keyword in 
                   ['income', 'revenue', 'financial', 'statement', 'quarter', 'q1 2025', '2025']):
                # Extract a reasonable amount of content
                content_text = container.get_text(strip=True)
                if 100 < len(content_text) < 5000:  # Reasonable size chunks
                    main_content.append(content_text)
        
        # If no specific containers found, get general content but limit size
        if not main_content:
            full_text = soup.get_text(strip=True)
            # Split into manageable chunks and take the most relevant ones
            chunks = [full_text[i:i+3000] for i in range(0, len(full_text), 3000)]
            main_content = chunks[:10]  # First 10 chunks should contain key info
        
        return "\n\n".join(main_content[:8])  # Limit to 8 sections to avoid overwhelming

    def _extract_dei_information(self, soup) -> str:
        """Extract comprehensive Document Entity Information (DEI)."""
        dei_info = []
        
        # Standard DEI tags to extract
        dei_tags = {
            'EntityRegistrantName': 'Company Name',
            'DocumentType': 'Document Type',
            'DocumentPeriodEndDate': 'Period End Date',
            'DocumentFiscalYearFocus': 'Fiscal Year',
            'DocumentFiscalPeriodFocus': 'Fiscal Period',
            'EntityCentralIndexKey': 'CIK',
            'TradingSymbol': 'Trading Symbol',
            'EntityFilerCategory': 'Filer Category'
        }
        
        for tag_name, label in dei_tags.items():
            # Try multiple tag patterns
            patterns_to_try = [
                f'dei:{tag_name}',
                f'us-gaap:{tag_name}',
                tag_name
            ]
            
            for pattern in patterns_to_try:
                elements = soup.find_all(attrs={'name': lambda x: x and x.lower().endswith(pattern.lower())})
                
                if elements:
                    # Get the best element (most recent/relevant)
                    element = self._get_best_element(elements)
                    text = element.get_text(strip=True)
                    
                    if text:
                        dei_info.append(f"{label}: {text}")
                        break
                if dei_info and dei_info[-1].startswith(label):
                    break
        
        return "\n".join(dei_info)

    def _extract_business_context(self, soup) -> str:
        """Extract enhanced business context and operations description."""
        business_sections = []
        
        # Look for common business description sections
        business_keywords = [
            'business', 'operations', 'products', 'services', 'strategy',
            'overview', 'description', 'activities', 'segments', 'markets'
        ]
        
        # Find sections with business-related content
        business_elements = soup.find_all(
            lambda tag: tag.name in ['p', 'div', 'td', 'span'] and
            tag.get_text() and len(tag.get_text().strip()) > 50 and
            any(keyword in tag.get_text().lower() for keyword in business_keywords)
        )
        
        business_text = []
        seen_content = set()
        
        for element in business_elements[:10]:  # Limit to avoid overwhelming
            text = element.get_text(strip=True)
            if (text not in seen_content and 
                len(text) > 50 and 
                len(text) < 1500 and  # Reasonable length
                text.count('.') > 1):  # Multiple sentences
                business_text.append(text)
                seen_content.add(text)
        
        return "\n\n".join(business_text)

    def _get_best_element(self, elements) -> Optional:
        """Get the best element from a list (most recent/relevant)."""
        if not elements:
            return None
        if len(elements) == 1:
            return elements[0]
        
        # Prefer elements with more specific context or recent dates
        for element in elements:
            context = element.get('contextref', '').lower()
            if any(keyword in context for keyword in ['2025', '2024', 'current', 'q1', 'q2', 'q3', 'q4']):
                return element
        
        # Return first element as fallback
        return elements[0]

    def _parse_html_content(self, soup) -> str:
        """Parse regular HTML content (non-XBRL) with improved cleaning."""
        # Remove unwanted elements
        for tag in soup.find_all(['script', 'style', 'meta', 'link', 'noscript']):
            tag.decompose()
        
        # Extract text content
        text = soup.get_text()
        
        # Clean up the text
        return self._clean_text(text)

    def _clean_text(self, text: str) -> str:
        """
        Enhanced text cleaning and normalization.
        
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
        
        # Clean up common XBRL artifacts
        text = re.sub(r'\s*\|\s*', ' | ', text)  # Clean up table separators
        text = re.sub(r'\$\s+(\d)', r'$\1', text)  # Fix currency formatting
        
        # Normalize line breaks
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        return text

    def _extract_filing_metadata(self, content: str, url: str) -> Dict[str, str]:
        """
        Extract enhanced metadata from SEC filing.
        
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
        
        # Try to extract comprehensive SEC filing metadata
        try:
            # Enhanced metadata extraction with multiple patterns
            metadata_patterns = {
                'company_name': [
                    r"COMPANY\s+CONFORMED\s+NAME:\s*(.+)",
                    r"EntityRegistrantName.*?>\s*(.+?)\s*<",
                ],
                'form_type': [
                    r"FORM\s+TYPE:\s*(.+)",
                    r"DocumentType.*?>\s*(.+?)\s*<",
                ],
                'filing_date': [
                    r"FILED\s+AS\s+OF\s+DATE:\s*(.+)",
                    r"DocumentPeriodEndDate.*?>\s*(.+?)\s*<",
                ],
                'period_end_date': [
                    r"PERIOD\s+OF\s+REPORT:\s*(.+)",
                    r"DocumentPeriodEndDate.*?>\s*(.+?)\s*<",
                ],
                'cik': [
                    r"CENTRAL\s+INDEX\s+KEY:\s*(.+)",
                    r"EntityCentralIndexKey.*?>\s*(.+?)\s*<",
                ],
                'trading_symbol': [
                    r"TRADING\s+SYMBOL:\s*(.+)",
                    r"TradingSymbol.*?>\s*(.+?)\s*<",
                ]
            }
            
            for field, patterns in metadata_patterns.items():
                for pattern in patterns:
                    match = re.search(pattern, content, re.I | re.DOTALL)
                    if match:
                        value = match.group(1).strip()
                        if value and field not in metadata:
                            metadata[field] = value
                            break
                            
        except Exception as e:
            print(f"⚠️ Metadata extraction warning: {str(e)}")
        
        return metadata

    def _create_chunks(self, text: str, metadata: Dict[str, str]) -> List[Document]:
        """
        Split text into chunks for vector embedding with enhanced metadata.
        
        Args:
            text: Cleaned text content
            metadata: Document metadata
            
        Returns:
            List of document chunks
        """
        # Split text into chunks
        chunks = self.text_splitter.split_text(text)
        
        # Create Document objects with enhanced metadata
        documents = []
        for i, chunk in enumerate(chunks):
            if len(chunk.strip()) > 50:  # Skip very short chunks
                chunk_metadata = metadata.copy()
                chunk_metadata.update({
                    "chunk_id": i,
                    "chunk_length": len(chunk),
                    "total_chunks": len(chunks),
                    "chunk_type": self._classify_chunk_content(chunk)
                })
                
                documents.append(Document(
                    page_content=chunk,
                    metadata=chunk_metadata
                ))
        
        # Limit number of chunks to prevent memory issues
        if len(documents) > self.settings.max_chunks:
            documents = documents[:self.settings.max_chunks]
        
        return documents

    def _classify_chunk_content(self, chunk: str) -> str:
        """Classify the type of content in a chunk."""
        chunk_lower = chunk.lower()
        
        # High priority financial terms
        high_priority_financial = ['net income', 'net loss', 'total revenue', 'operating income', 
                                 'earnings per share', 'q1 2025', 'first quarter 2025',
                                 'consolidated statements', 'income statement', 'balance sheet']
        
        # General financial terms
        financial_terms = ['assets', 'revenue', 'income', 'liabilities', '$', 'million', 'billion',
                          'consolidated', 'financial statements', 'operating', 'earnings']
        
        # Business description terms
        business_terms = ['business', 'operations', 'company', 'products', 'services', 'customers',
                         'market', 'strategy', 'manufacturing', 'automotive']
        
        # Risk factor terms
        risk_terms = ['risk', 'uncertainty', 'may', 'could', 'forward-looking', 'factors',
                     'litigation', 'regulation', 'competition']
        
        # Check for high priority financial content first
        if any(term in chunk_lower for term in high_priority_financial):
            return 'high_priority_financial'
        elif any(term in chunk_lower for term in financial_terms):
            return 'financial'
        elif any(term in chunk_lower for term in business_terms):
            return 'business_description'
        elif any(term in chunk_lower for term in risk_terms):
            return 'risk_factors'
        else:
            return 'general'

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

    def _extract_financial_table_sections(self, soup) -> str:
        """Extract financial table sections from HTML."""
        financial_content = []
        
        # Look for tables with financial data
        tables = soup.find_all('table')
        
        for table in tables:
            table_text = table.get_text(strip=True)
            
            # Check if this looks like a financial statement
            if any(pattern in table_text.lower() for pattern in [
                'consolidated statements', 'income statement', 'balance sheet',
                'cash flow', 'three months ended', 'quarterly'
            ]) and any(c.isdigit() for c in table_text):
                
                # Get table headers and some sample data
                headers = table.find_all('th')
                if headers:
                    header_text = ' | '.join([h.get_text(strip=True) for h in headers[:5]])
                    financial_content.append(f"Table Headers: {header_text}")
                
                # Get first few rows with data
                rows = table.find_all('tr')[:5]
                for row in rows:
                    row_text = row.get_text(separator=' | ', strip=True)
                    if any(c.isdigit() for c in row_text):
                        financial_content.append(f"Data Row: {row_text}")
        
        return '\n'.join(financial_content[:15]) if financial_content else ""
    
    def _extract_risk_factors(self, soup) -> str:
        """Extract risk factors and important disclosures."""
        risk_content = []
        
        # Look for risk-related sections
        risk_sections = soup.find_all(['div', 'p', 'section'], 
                                    string=lambda text: text and any(
                                        term in text.lower() for term in [
                                            'risk factors', 'forward-looking', 'uncertainty',
                                            'material adverse', 'significant risk'
                                        ]
                                    ))
        
        for section in risk_sections[:3]:  # Limit to prevent overflow
            parent = section.parent if section.parent else section
            text = parent.get_text(strip=True)
            if len(text) > 100:
                risk_content.append(text[:500])  # Truncate long sections
        
        return '\n\n'.join(risk_content) if risk_content else "" 