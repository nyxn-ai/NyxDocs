"""Basic tests for NyxnDocs functionality."""

import pytest

from nyxdocs import __version__
from nyxdocs.config import get_settings
from nyxdocs.models import BlockchainNetwork, ProjectCategory


def test_version():
    """Test that version is defined."""
    assert __version__ == "0.1.6"


def test_settings():
    """Test settings configuration."""
    settings = get_settings()
    assert settings.mcp_server_name == "NyxnDocs"
    assert settings.mcp_server_version == "0.1.6"
    assert settings.database_url.startswith("sqlite://")


def test_blockchain_networks():
    """Test blockchain network enum."""
    assert BlockchainNetwork.ETHEREUM == "ethereum"
    assert BlockchainNetwork.BINANCE_SMART_CHAIN == "binance-smart-chain"
    assert BlockchainNetwork.POLYGON == "polygon-pos"


def test_project_categories():
    """Test project category enum."""
    assert ProjectCategory.DEFI == "DeFi"
    assert ProjectCategory.NFT == "NFT"
    assert ProjectCategory.DAO == "DAO"


@pytest.mark.asyncio
async def test_database_models():
    """Test database model imports."""
    from nyxdocs.database.models import ProjectTable, DocumentationTable
    
    # Test that models can be imported without errors
    assert ProjectTable.__tablename__ == "projects"
    assert DocumentationTable.__tablename__ == "documentation"


@pytest.mark.asyncio
async def test_collectors():
    """Test collector imports."""
    from nyxdocs.collectors import CoinGeckoCollector, GitHubCollector
    
    # Test that collectors can be instantiated
    coingecko = CoinGeckoCollector()
    github = GitHubCollector()
    
    assert coingecko.name == "CoinGecko"
    assert github.name == "GitHub"


@pytest.mark.asyncio
async def test_scrapers():
    """Test scraper imports."""
    from nyxdocs.scrapers import GitHubScraper, WebScraper
    
    # Test that scrapers can be instantiated
    github_scraper = GitHubScraper()
    web_scraper = WebScraper()
    
    assert github_scraper.name == "GitHub"
    assert web_scraper.name == "Web"
    
    # Test URL detection
    assert await github_scraper.can_scrape("https://github.com/user/repo")
    assert not await github_scraper.can_scrape("https://example.com")
    
    assert await web_scraper.can_scrape("https://example.com")
    assert not await web_scraper.can_scrape("https://github.com/user/repo")
