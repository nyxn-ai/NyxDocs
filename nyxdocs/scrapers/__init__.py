"""Documentation scrapers for NyxDocs."""

from .base import BaseScraper
from .github_scraper import GitHubScraper
from .web_scraper import WebScraper

__all__ = ["BaseScraper", "GitHubScraper", "WebScraper"]
