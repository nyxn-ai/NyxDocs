"""Base scraper class for documentation extraction."""

import hashlib
import logging
from abc import ABC, abstractmethod
from typing import Optional, Tuple

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import get_settings
from ..models import DocumentationType

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Base class for documentation scrapers."""
    
    def __init__(self, name: str, doc_type: DocumentationType):
        """Initialize the scraper."""
        self.name = name
        self.doc_type = doc_type
        self.settings = get_settings()
        self.client: Optional[httpx.AsyncClient] = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
        
    async def start(self) -> None:
        """Start the scraper and initialize HTTP client."""
        if self.client is None:
            self.client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.settings.scrape_timeout),
                headers={"User-Agent": self.settings.user_agent},
                limits=httpx.Limits(max_connections=5, max_keepalive_connections=2),
                follow_redirects=True
            )
        logger.info(f"Started {self.name} scraper")
        
    async def stop(self) -> None:
        """Stop the scraper and cleanup resources."""
        if self.client:
            await self.client.aclose()
            self.client = None
        logger.info(f"Stopped {self.name} scraper")
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8)
    )
    async def fetch_content(self, url: str) -> str:
        """Fetch content from URL with retry logic."""
        if not self.client:
            raise RuntimeError("Scraper not started")
            
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            return response.text
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} for {url}: {e}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error for {url}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error for {url}: {e}")
            raise
            
    def calculate_content_hash(self, content: str) -> str:
        """Calculate SHA-256 hash of content for change detection."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
        
    def clean_content(self, content: str) -> str:
        """Clean and normalize content."""
        if not content:
            return ""
            
        # Remove excessive whitespace
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Strip whitespace from each line
            cleaned_line = line.strip()
            cleaned_lines.append(cleaned_line)
        
        # Join lines and remove excessive empty lines
        cleaned_content = '\n'.join(cleaned_lines)
        
        # Remove more than 2 consecutive newlines
        import re
        cleaned_content = re.sub(r'\n{3,}', '\n\n', cleaned_content)
        
        # Limit content length
        if len(cleaned_content) > self.settings.max_content_length:
            cleaned_content = cleaned_content[:self.settings.max_content_length] + "\n\n[Content truncated]"
        
        return cleaned_content.strip()
        
    @abstractmethod
    async def can_scrape(self, url: str) -> bool:
        """Check if this scraper can handle the given URL."""
        pass
        
    @abstractmethod
    async def scrape(self, url: str) -> Tuple[str, str]:
        """
        Scrape documentation from URL.
        
        Returns:
            Tuple of (title, content)
        """
        pass
        
    @abstractmethod
    async def discover_docs(self, project_url: str) -> list[dict]:
        """
        Discover documentation URLs for a project.
        
        Returns:
            List of dicts with 'url', 'title', and 'type' keys
        """
        pass
