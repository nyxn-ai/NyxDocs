"""Web scraper for general documentation websites."""

import logging
import re
from typing import List, Tuple
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from ..models import DocumentationType
from .base import BaseScraper

logger = logging.getLogger(__name__)


class WebScraper(BaseScraper):
    """Scraper for general web documentation."""
    
    def __init__(self):
        """Initialize web scraper."""
        super().__init__("Web", DocumentationType.WEBSITE)
        
    async def can_scrape(self, url: str) -> bool:
        """Check if URL can be scraped as a web page."""
        # Can scrape any HTTP/HTTPS URL that's not GitHub
        return url.startswith(("http://", "https://")) and "github.com" not in url
        
    async def scrape(self, url: str) -> Tuple[str, str]:
        """Scrape documentation from web URL."""
        try:
            # Fetch HTML content
            html_content = await self.fetch_content(url)
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract title
            title = self._extract_title(soup, url)
            
            # Extract main content
            content = self._extract_content(soup)
            
            # Clean content
            cleaned_content = self.clean_content(content)
            
            return title, cleaned_content
            
        except Exception as e:
            logger.error(f"Error scraping web URL {url}: {e}")
            raise
            
    async def discover_docs(self, project_url: str) -> List[dict]:
        """Discover documentation links on a website."""
        docs = []
        
        try:
            # Fetch the main page
            html_content = await self.fetch_content(project_url)
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find documentation links
            doc_links = self._find_doc_links(soup, project_url)
            docs.extend(doc_links)
            
            # Check common documentation subdomains/paths
            subdomain_docs = await self._check_doc_subdomains(project_url)
            docs.extend(subdomain_docs)
            
        except Exception as e:
            logger.error(f"Error discovering docs for {project_url}: {e}")
            
        return docs
        
    def _extract_title(self, soup: BeautifulSoup, url: str) -> str:
        """Extract title from HTML."""
        # Try different title sources
        title_sources = [
            soup.find('title'),
            soup.find('h1'),
            soup.find('h2'),
            soup.find('meta', {'property': 'og:title'}),
            soup.find('meta', {'name': 'title'})
        ]
        
        for source in title_sources:
            if source:
                if source.name == 'meta':
                    title = source.get('content', '')
                else:
                    title = source.get_text(strip=True)
                
                if title:
                    return title[:100]  # Limit title length
        
        # Fallback to URL path
        path = urlparse(url).path.strip('/')
        if path:
            return path.split('/')[-1] or "Documentation"
        
        return "Documentation"
        
    def _extract_content(self, soup: BeautifulSoup) -> str:
        """Extract main content from HTML."""
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe']):
            element.decompose()
        
        # Try to find main content area
        content_selectors = [
            'main',
            '[role="main"]',
            '.content',
            '.documentation',
            '.docs',
            '.markdown-body',
            '.post-content',
            'article',
            '.container .row .col',
            'body'
        ]
        
        content_element = None
        for selector in content_selectors:
            content_element = soup.select_one(selector)
            if content_element:
                break
        
        if not content_element:
            content_element = soup.find('body') or soup
        
        # Extract text content
        content = content_element.get_text(separator='\n', strip=True)
        
        return content
        
    def _find_doc_links(self, soup: BeautifulSoup, base_url: str) -> List[dict]:
        """Find documentation links on the page."""
        docs = []
        
        # Documentation link patterns
        doc_patterns = [
            r'docs?(?:umentation)?',
            r'guide',
            r'tutorial',
            r'api',
            r'reference',
            r'manual',
            r'help'
        ]
        
        # Find all links
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link['href']
            text = link.get_text(strip=True).lower()
            
            # Check if link text matches documentation patterns
            is_doc_link = any(re.search(pattern, text, re.IGNORECASE) for pattern in doc_patterns)
            
            # Check if href matches documentation patterns
            if not is_doc_link:
                is_doc_link = any(re.search(pattern, href, re.IGNORECASE) for pattern in doc_patterns)
            
            if is_doc_link:
                # Convert relative URLs to absolute
                full_url = urljoin(base_url, href)
                
                docs.append({
                    "url": full_url,
                    "title": link.get_text(strip=True) or "Documentation",
                    "type": "website"
                })
        
        return docs[:10]  # Limit to first 10 documentation links
        
    async def _check_doc_subdomains(self, project_url: str) -> List[dict]:
        """Check common documentation subdomains."""
        docs = []
        
        try:
            parsed_url = urlparse(project_url)
            domain = parsed_url.netloc
            
            # Remove 'www.' if present
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Common documentation subdomains
            doc_subdomains = ['docs', 'documentation', 'dev', 'developers', 'api', 'guide']
            
            for subdomain in doc_subdomains:
                doc_url = f"https://{subdomain}.{domain}"
                
                try:
                    # Check if subdomain exists
                    response = await self.client.head(doc_url)
                    if response.status_code == 200:
                        docs.append({
                            "url": doc_url,
                            "title": f"{subdomain.title()} Documentation",
                            "type": "website"
                        })
                except Exception:
                    continue  # Subdomain doesn't exist
                    
        except Exception as e:
            logger.debug(f"Error checking subdomains for {project_url}: {e}")
            
        return docs
        
    def _is_gitbook_site(self, soup: BeautifulSoup) -> bool:
        """Check if the site is powered by GitBook."""
        # Look for GitBook-specific elements
        gitbook_indicators = [
            soup.find('meta', {'name': 'generator', 'content': re.compile(r'gitbook', re.I)}),
            soup.find('script', src=re.compile(r'gitbook', re.I)),
            soup.find(class_=re.compile(r'gitbook', re.I))
        ]
        
        return any(indicator for indicator in gitbook_indicators)
        
    def _is_notion_site(self, soup: BeautifulSoup) -> bool:
        """Check if the site is a Notion page."""
        # Look for Notion-specific elements
        notion_indicators = [
            soup.find('meta', {'property': 'og:site_name', 'content': 'Notion'}),
            soup.find('script', src=re.compile(r'notion', re.I)),
            soup.find(id=re.compile(r'notion', re.I))
        ]
        
        return any(indicator for indicator in indicators)
