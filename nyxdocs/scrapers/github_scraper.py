"""GitHub documentation scraper."""

import logging
import re
from typing import List, Tuple
from urllib.parse import urljoin, urlparse

from ..models import DocumentationType
from .base import BaseScraper

logger = logging.getLogger(__name__)


class GitHubScraper(BaseScraper):
    """Scraper for GitHub repository documentation."""
    
    def __init__(self):
        """Initialize GitHub scraper."""
        super().__init__("GitHub", DocumentationType.GITHUB)
        self.github_token = self.settings.github_token
        
    async def can_scrape(self, url: str) -> bool:
        """Check if URL is a GitHub repository or documentation."""
        return "github.com" in url
        
    async def scrape(self, url: str) -> Tuple[str, str]:
        """Scrape documentation from GitHub URL."""
        try:
            # Convert GitHub URL to raw content URL if needed
            raw_url = self._convert_to_raw_url(url)
            
            # Fetch content
            content = await self.fetch_content(raw_url)
            
            # Extract title from URL or content
            title = self._extract_title(url, content)
            
            # Clean content
            cleaned_content = self.clean_content(content)
            
            return title, cleaned_content
            
        except Exception as e:
            logger.error(f"Error scraping GitHub URL {url}: {e}")
            raise
            
    async def discover_docs(self, project_url: str) -> List[dict]:
        """Discover documentation in a GitHub repository."""
        docs = []
        
        try:
            # Extract owner and repo from URL
            owner, repo = self._extract_owner_repo(project_url)
            if not owner or not repo:
                return docs
            
            # Check for README files
            readme_docs = await self._find_readme_files(owner, repo)
            docs.extend(readme_docs)
            
            # Check for docs directory
            docs_dir = await self._find_docs_directory(owner, repo)
            docs.extend(docs_dir)
            
            # Check for wiki
            wiki_docs = await self._check_wiki(owner, repo)
            docs.extend(wiki_docs)
            
        except Exception as e:
            logger.error(f"Error discovering docs for {project_url}: {e}")
            
        return docs
        
    def _convert_to_raw_url(self, url: str) -> str:
        """Convert GitHub URL to raw content URL."""
        if "raw.githubusercontent.com" in url:
            return url
            
        if "github.com" in url and "/blob/" in url:
            # Convert blob URL to raw URL
            return url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
        
        return url
        
    def _extract_title(self, url: str, content: str) -> str:
        """Extract title from URL or content."""
        # Try to get title from URL path
        path_parts = urlparse(url).path.strip('/').split('/')
        if len(path_parts) >= 2:
            filename = path_parts[-1]
            if filename:
                return filename
        
        # Try to extract title from markdown content
        if content:
            lines = content.split('\n')
            for line in lines[:10]:  # Check first 10 lines
                line = line.strip()
                if line.startswith('# '):
                    return line[2:].strip()
                elif line.startswith('## '):
                    return line[3:].strip()
        
        return "Documentation"
        
    def _extract_owner_repo(self, url: str) -> Tuple[str, str]:
        """Extract owner and repository name from GitHub URL."""
        try:
            path = urlparse(url).path.strip('/')
            parts = path.split('/')
            if len(parts) >= 2:
                return parts[0], parts[1]
        except Exception:
            pass
        return "", ""
        
    async def _find_readme_files(self, owner: str, repo: str) -> List[dict]:
        """Find README files in the repository."""
        docs = []
        
        readme_names = ["README.md", "README.rst", "README.txt", "README"]
        
        for readme_name in readme_names:
            try:
                url = f"https://api.github.com/repos/{owner}/{repo}/contents/{readme_name}"
                headers = {}
                if self.github_token:
                    headers["Authorization"] = f"token {self.github_token}"
                
                response = await self.client.get(url, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    docs.append({
                        "url": data["download_url"],
                        "title": readme_name,
                        "type": "readme"
                    })
                    break  # Only take the first README found
                    
            except Exception as e:
                logger.debug(f"README {readme_name} not found for {owner}/{repo}: {e}")
                continue
                
        return docs
        
    async def _find_docs_directory(self, owner: str, repo: str) -> List[dict]:
        """Find documentation directory and files."""
        docs = []
        
        doc_dirs = ["docs", "documentation", "doc", "wiki"]
        
        for doc_dir in doc_dirs:
            try:
                url = f"https://api.github.com/repos/{owner}/{repo}/contents/{doc_dir}"
                headers = {}
                if self.github_token:
                    headers["Authorization"] = f"token {self.github_token}"
                
                response = await self.client.get(url, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    
                    if isinstance(data, list):
                        # Directory listing
                        for item in data:
                            if item["type"] == "file" and self._is_doc_file(item["name"]):
                                docs.append({
                                    "url": item["download_url"],
                                    "title": f"{doc_dir}/{item['name']}",
                                    "type": "docs"
                                })
                    break  # Only check the first docs directory found
                    
            except Exception as e:
                logger.debug(f"Docs directory {doc_dir} not found for {owner}/{repo}: {e}")
                continue
                
        return docs
        
    async def _check_wiki(self, owner: str, repo: str) -> List[dict]:
        """Check if repository has a wiki."""
        docs = []
        
        try:
            # Check if wiki exists by trying to access it
            wiki_url = f"https://github.com/{owner}/{repo}/wiki"
            response = await self.client.head(wiki_url)
            
            if response.status_code == 200:
                docs.append({
                    "url": wiki_url,
                    "title": "Wiki",
                    "type": "wiki"
                })
                
        except Exception as e:
            logger.debug(f"Wiki not found for {owner}/{repo}: {e}")
            
        return docs
        
    def _is_doc_file(self, filename: str) -> bool:
        """Check if file is a documentation file."""
        doc_extensions = [".md", ".rst", ".txt", ".adoc", ".asciidoc"]
        doc_names = ["readme", "changelog", "contributing", "license", "install", "usage", "api"]
        
        filename_lower = filename.lower()
        
        # Check extension
        for ext in doc_extensions:
            if filename_lower.endswith(ext):
                return True
        
        # Check common doc file names
        name_without_ext = filename_lower.split('.')[0]
        return name_without_ext in doc_names
