"""Configuration management for NyxDocs."""

import os
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API Keys
    coingecko_api_key: Optional[str] = Field(None, description="CoinGecko API key")
    github_token: Optional[str] = Field(None, description="GitHub personal access token")
    defipulse_api_key: Optional[str] = Field(None, description="DeFiPulse API key")

    # Database
    database_url: str = Field("sqlite:///nyxdocs.db", description="Database URL")
    db_pool_size: int = Field(10, description="Database connection pool size")
    db_max_overflow: int = Field(20, description="Database max overflow connections")
    db_pool_timeout: int = Field(30, description="Database pool timeout")

    # Server
    log_level: str = Field("INFO", description="Logging level")
    host: str = Field("localhost", description="Server host")
    port: int = Field(8000, description="Server port")
    mcp_server_name: str = Field("NyxnDocs", description="MCP server name")
    mcp_server_version: str = Field("0.1.6", description="MCP server version")

    # Data Collection
    project_update_interval: int = Field(3600, description="Project update interval (seconds)")
    doc_update_interval: int = Field(7200, description="Documentation update interval (seconds)")
    max_concurrent_scrapes: int = Field(5, description="Maximum concurrent scraping operations")
    request_timeout: int = Field(30, description="Request timeout (seconds)")

    # Rate Limiting
    rate_limit_requests_per_minute: int = Field(60, description="Rate limit requests per minute")
    rate_limit_burst: int = Field(10, description="Rate limit burst")

    # Scraping
    user_agent: str = Field(
        "NyxnDocs-Bot/0.1.6 (+https://github.com/nyxn-ai/NyxnDocs)",
        description="User agent for web scraping"
    )
    max_content_length: int = Field(1000000, description="Maximum content length to scrape")
    scrape_timeout: int = Field(60, description="Scraping timeout (seconds)")
    max_retries: int = Field(3, description="Maximum retry attempts")
    retry_delay: int = Field(5, description="Retry delay (seconds)")

    # Cache
    cache_ttl_projects: int = Field(3600, description="Cache TTL for projects (seconds)")
    cache_ttl_docs: int = Field(1800, description="Cache TTL for docs (seconds)")
    cache_ttl_search: int = Field(300, description="Cache TTL for search (seconds)")
    cache_max_size: int = Field(1000, description="Maximum cache size")

    # Feature Flags
    enable_auto_discovery: bool = Field(True, description="Enable automatic project discovery")
    enable_update_monitoring: bool = Field(True, description="Enable update monitoring")
    enable_content_caching: bool = Field(True, description="Enable content caching")
    enable_metrics: bool = Field(False, description="Enable metrics collection")

    # Data Sources
    enable_coingecko: bool = Field(True, description="Enable CoinGecko data source")
    enable_github: bool = Field(True, description="Enable GitHub data source")
    enable_defipulse: bool = Field(False, description="Enable DeFiPulse data source")

    # Development
    debug: bool = Field(False, description="Enable debug mode")
    sql_debug: bool = Field(False, description="Enable SQL debug logging")
    http_debug: bool = Field(False, description="Enable HTTP debug logging")
    test_database_url: str = Field("sqlite:///test_nyxdocs.db", description="Test database URL")

    # Monitoring
    sentry_dsn: Optional[str] = Field(None, description="Sentry DSN for error tracking")
    metrics_enabled: bool = Field(False, description="Enable Prometheus metrics")
    metrics_port: int = Field(9090, description="Metrics server port")
    health_check_interval: int = Field(60, description="Health check interval (seconds)")

    # Security
    cors_origins: List[str] = Field(
        ["http://localhost:3000", "http://localhost:8080"],
        description="CORS allowed origins"
    )
    api_rate_limit: int = Field(100, description="API rate limit")
    max_request_size: int = Field(10485760, description="Maximum request size (bytes)")

    # Blockchain Networks
    default_blockchains: List[str] = Field(
        ["ethereum", "binance-smart-chain", "polygon-pos", "solana"],
        description="Default blockchain networks to monitor"
    )
    ethereum_rpc_url: Optional[str] = Field(None, description="Ethereum RPC URL")
    bsc_rpc_url: Optional[str] = Field(None, description="BSC RPC URL")
    polygon_rpc_url: Optional[str] = Field(None, description="Polygon RPC URL")
    solana_rpc_url: Optional[str] = Field(None, description="Solana RPC URL")

    # Documentation Sources
    enable_github_docs: bool = Field(True, description="Enable GitHub documentation")
    enable_gitbook_docs: bool = Field(True, description="Enable GitBook documentation")
    enable_notion_docs: bool = Field(True, description="Enable Notion documentation")
    enable_website_docs: bool = Field(True, description="Enable website documentation")
    custom_doc_patterns: List[str] = Field(
        ["docs/", "documentation/", "wiki/"],
        description="Custom documentation patterns"
    )

    # Performance
    worker_processes: int = Field(1, description="Number of worker processes")
    worker_connections: int = Field(1000, description="Worker connections")
    max_memory_usage: str = Field("512MB", description="Maximum memory usage")
    async_pool_size: int = Field(100, description="Async pool size")
    async_timeout: int = Field(30, description="Async timeout (seconds)")

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.debug or os.getenv("ENVIRONMENT") == "development"

    @property
    def is_testing(self) -> bool:
        """Check if running in testing mode."""
        return os.getenv("ENVIRONMENT") == "testing"

    def get_database_url(self) -> str:
        """Get the appropriate database URL based on environment."""
        if self.is_testing:
            return self.test_database_url
        return self.database_url


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings
