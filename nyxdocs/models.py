"""Data models for NyxDocs."""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class BlockchainNetwork(str, Enum):
    """Supported blockchain networks."""
    
    ETHEREUM = "ethereum"
    BINANCE_SMART_CHAIN = "binance-smart-chain"
    POLYGON = "polygon-pos"
    ARBITRUM = "arbitrum-one"
    OPTIMISM = "optimistic-ethereum"
    AVALANCHE = "avalanche"
    SOLANA = "solana"
    CARDANO = "cardano"
    POLKADOT = "polkadot"
    COSMOS = "cosmos"


class ProjectCategory(str, Enum):
    """Project categories."""
    
    DEFI = "DeFi"
    NFT = "NFT"
    DAO = "DAO"
    DEX = "DEX"
    LENDING = "Lending"
    YIELD_FARMING = "Yield Farming"
    STAKING = "Staking"
    BRIDGE = "Bridge"
    ORACLE = "Oracle"
    WALLET = "Wallet"
    INFRASTRUCTURE = "Infrastructure"
    GAMING = "Gaming"
    METAVERSE = "Metaverse"
    OTHER = "Other"


class ProjectStatus(str, Enum):
    """Project status."""
    
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"


class DocumentationType(str, Enum):
    """Documentation types."""
    
    GITHUB = "github"
    GITBOOK = "gitbook"
    NOTION = "notion"
    WEBSITE = "website"
    DOCS_SITE = "docs_site"


class ScrapeStatus(str, Enum):
    """Scraping status."""
    
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class Project(BaseModel):
    """Cryptocurrency project model."""
    
    id: Optional[str] = None
    name: str = Field(..., description="Project name")
    symbol: Optional[str] = Field(None, description="Project symbol/ticker")
    blockchain: Optional[BlockchainNetwork] = Field(None, description="Primary blockchain")
    category: Optional[ProjectCategory] = Field(None, description="Project category")
    description: Optional[str] = Field(None, description="Project description")
    website: Optional[str] = Field(None, description="Official website")
    github_repo: Optional[str] = Field(None, description="GitHub repository URL")
    market_cap: Optional[float] = Field(None, description="Market capitalization")
    status: ProjectStatus = Field(ProjectStatus.ACTIVE, description="Project status")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True


class Documentation(BaseModel):
    """Documentation model."""
    
    id: Optional[str] = None
    project_id: str = Field(..., description="Associated project ID")
    title: str = Field(..., description="Documentation title")
    url: str = Field(..., description="Documentation URL")
    doc_type: DocumentationType = Field(..., description="Documentation type")
    content: Optional[str] = Field(None, description="Documentation content")
    content_hash: Optional[str] = Field(None, description="Content hash for change detection")
    scrape_status: ScrapeStatus = Field(ScrapeStatus.PENDING, description="Scraping status")
    last_scraped: Optional[datetime] = Field(None, description="Last scraping time")
    error_message: Optional[str] = Field(None, description="Error message if scraping failed")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True


class UpdateRecord(BaseModel):
    """Documentation update record."""
    
    id: Optional[str] = None
    documentation_id: str = Field(..., description="Documentation ID")
    old_hash: Optional[str] = Field(None, description="Previous content hash")
    new_hash: str = Field(..., description="New content hash")
    changes_detected: bool = Field(..., description="Whether changes were detected")
    checked_at: datetime = Field(..., description="When the check was performed")
    
    class Config:
        use_enum_values = True


class SearchRequest(BaseModel):
    """Search request model."""
    
    query: str = Field(..., description="Search query")
    blockchain: Optional[BlockchainNetwork] = Field(None, description="Filter by blockchain")
    category: Optional[ProjectCategory] = Field(None, description="Filter by category")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of results")
    
    class Config:
        use_enum_values = True


class SearchResult(BaseModel):
    """Search result model."""
    
    project: Project
    documentation_count: int = Field(..., description="Number of available documents")
    last_updated: Optional[datetime] = Field(None, description="Last update time")


class SearchResponse(BaseModel):
    """Search response model."""
    
    results: List[SearchResult] = Field(..., description="Search results")
    total: int = Field(..., description="Total number of results")
    query: str = Field(..., description="Original search query")


class ProjectInfoRequest(BaseModel):
    """Project info request model."""
    
    project_name: str = Field(..., description="Project name or symbol")
    include_documentation: bool = Field(True, description="Include documentation list")
    include_blockchain_info: bool = Field(True, description="Include blockchain information")


class ProjectInfoResponse(BaseModel):
    """Project info response model."""
    
    project: Project
    documentation: Optional[List[Documentation]] = None
    blockchain_info: Optional[dict] = None


class DocumentationRequest(BaseModel):
    """Documentation request model."""
    
    project_name: str = Field(..., description="Project name or symbol")
    doc_title: Optional[str] = Field(None, description="Specific document title")
    format: str = Field("markdown", description="Output format")


class DocumentationResponse(BaseModel):
    """Documentation response model."""
    
    project_name: str = Field(..., description="Project name")
    documents: List[Documentation] = Field(..., description="Documentation list")


class UpdateCheckRequest(BaseModel):
    """Update check request model."""
    
    project_name: Optional[str] = Field(None, description="Specific project to check")
    since: Optional[datetime] = Field(None, description="Check updates since this date")
    limit: int = Field(20, ge=1, le=100, description="Maximum number of updates")


class UpdateCheckResponse(BaseModel):
    """Update check response model."""
    
    updates: List[UpdateRecord] = Field(..., description="Update records")
    total: int = Field(..., description="Total number of updates")


class BlockchainInfo(BaseModel):
    """Blockchain information model."""
    
    name: str = Field(..., description="Blockchain name")
    symbol: str = Field(..., description="Native token symbol")
    chain_id: Optional[int] = Field(None, description="Chain ID")
    rpc_url: Optional[str] = Field(None, description="RPC endpoint")
    explorer_url: Optional[str] = Field(None, description="Block explorer URL")
    project_count: int = Field(0, description="Number of projects on this blockchain")


class SystemStats(BaseModel):
    """System statistics model."""
    
    total_projects: int = Field(..., description="Total number of projects")
    total_documents: int = Field(..., description="Total number of documents")
    active_projects: int = Field(..., description="Number of active projects")
    successful_scrapes: int = Field(..., description="Number of successful scrapes")
    failed_scrapes: int = Field(..., description="Number of failed scrapes")
    last_update: Optional[datetime] = Field(None, description="Last system update")
    supported_blockchains: List[BlockchainInfo] = Field(..., description="Supported blockchains")
