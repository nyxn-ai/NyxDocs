"""Base collector class for data collection."""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import get_settings

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    """Base class for data collectors."""
    
    def __init__(self, name: str):
        """Initialize the collector."""
        self.name = name
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
        """Start the collector and initialize HTTP client."""
        if self.client is None:
            self.client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.settings.request_timeout),
                headers={"User-Agent": self.settings.user_agent},
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
            )
        logger.info(f"Started {self.name} collector")
        
    async def stop(self) -> None:
        """Stop the collector and cleanup resources."""
        if self.client:
            await self.client.aclose()
            self.client = None
        logger.info(f"Stopped {self.name} collector")
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def make_request(
        self, 
        url: str, 
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Make an HTTP request with retry logic."""
        if not self.client:
            raise RuntimeError("Collector not started")
            
        try:
            response = await self.client.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} for {url}: {e}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error for {url}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error for {url}: {e}")
            raise
            
    async def rate_limit(self, delay: float = 1.0) -> None:
        """Apply rate limiting between requests."""
        await asyncio.sleep(delay)
        
    @abstractmethod
    async def collect_projects(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Collect project data from the source."""
        pass
        
    @abstractmethod
    async def get_project_details(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information for a specific project."""
        pass
