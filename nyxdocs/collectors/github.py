"""GitHub data collector for cryptocurrency projects."""

import logging
from typing import Any, Dict, List, Optional

from ..models import BlockchainNetwork, ProjectCategory
from .base import BaseCollector

logger = logging.getLogger(__name__)


class GitHubCollector(BaseCollector):
    """Collector for GitHub cryptocurrency repositories."""
    
    BASE_URL = "https://api.github.com"
    
    def __init__(self):
        """Initialize GitHub collector."""
        super().__init__("GitHub")
        self.token = self.settings.github_token
        
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for GitHub API requests."""
        headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        return headers
        
    async def collect_projects(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Collect cryptocurrency projects from GitHub."""
        logger.info(f"Collecting {limit} projects from GitHub")
        
        projects = []
        
        # Search queries for different types of crypto projects
        search_queries = [
            "defi ethereum language:solidity",
            "blockchain cryptocurrency language:javascript",
            "smart contracts solidity",
            "web3 dapp",
            "nft marketplace",
            "dao governance",
            "yield farming",
            "dex exchange",
            "bridge cross-chain",
            "oracle chainlink"
        ]
        
        per_query_limit = max(1, limit // len(search_queries))
        
        for query in search_queries:
            if len(projects) >= limit:
                break
                
            try:
                current_limit = min(per_query_limit, limit - len(projects))
                query_projects = await self._search_repositories(query, current_limit)
                projects.extend(query_projects)
                
                # Rate limiting
                await self.rate_limit(2.0)  # GitHub has stricter rate limits
                
            except Exception as e:
                logger.error(f"Error searching GitHub for '{query}': {e}")
                continue
                
        logger.info(f"Collected {len(projects)} projects from GitHub")
        return projects[:limit]
        
    async def get_project_details(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed repository information from GitHub."""
        try:
            # project_id should be in format "owner/repo"
            data = await self.make_request(
                f"{self.BASE_URL}/repos/{project_id}",
                headers=self._get_headers()
            )
            
            return await self._convert_repo_to_project(data, detailed=True)
            
        except Exception as e:
            logger.error(f"Error getting GitHub details for {project_id}: {e}")
            return None
            
    async def _search_repositories(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search GitHub repositories with a specific query."""
        try:
            data = await self.make_request(
                f"{self.BASE_URL}/search/repositories",
                params={
                    "q": query,
                    "sort": "stars",
                    "order": "desc",
                    "per_page": min(100, limit)
                },
                headers=self._get_headers()
            )
            
            projects = []
            for repo in data.get("items", []):
                project = await self._convert_repo_to_project(repo)
                if project:
                    projects.append(project)
                    
            return projects
            
        except Exception as e:
            logger.error(f"Error searching repositories for '{query}': {e}")
            return []
            
    async def _convert_repo_to_project(self, repo: Dict[str, Any], detailed: bool = False) -> Optional[Dict[str, Any]]:
        """Convert GitHub repository data to project format."""
        try:
            # Determine blockchain from repository info
            blockchain = self._determine_blockchain_from_repo(repo)
            
            # Determine category from repository info
            category = self._determine_category_from_repo(repo)
            
            # Skip if not crypto-related
            if not self._is_crypto_related(repo):
                return None
            
            # Extract basic info
            name = repo["name"]
            description = repo.get("description", "")
            website = repo.get("homepage")
            github_repo = repo["html_url"]
            
            # Use stars as a proxy for market cap/popularity
            stars = repo.get("stargazers_count", 0)
            market_cap = stars * 1000 if stars else None  # Rough approximation
            
            return {
                "id": f"github-{repo['id']}",
                "name": name,
                "symbol": None,  # GitHub repos don't have symbols
                "blockchain": blockchain,
                "category": category,
                "description": description,
                "website": website,
                "github_repo": github_repo,
                "market_cap": market_cap,
                "status": "active" if not repo.get("archived", False) else "inactive",
                "source": "github",
                "external_id": repo["full_name"]
            }
            
        except Exception as e:
            logger.error(f"Error converting repo {repo.get('full_name', 'unknown')}: {e}")
            return None
            
    def _is_crypto_related(self, repo: Dict[str, Any]) -> bool:
        """Check if repository is cryptocurrency-related."""
        name = repo.get("name", "").lower()
        description = repo.get("description", "").lower() if repo.get("description") else ""
        topics = [topic.lower() for topic in repo.get("topics", [])]
        language = repo.get("language", "").lower() if repo.get("language") else ""
        
        # Crypto-related keywords
        crypto_keywords = [
            "blockchain", "cryptocurrency", "crypto", "bitcoin", "ethereum",
            "defi", "nft", "dao", "dex", "smart-contract", "solidity",
            "web3", "dapp", "token", "coin", "wallet", "exchange",
            "yield", "farming", "staking", "bridge", "oracle",
            "uniswap", "compound", "aave", "chainlink", "polygon"
        ]
        
        # Check if any crypto keywords are present
        text_to_check = f"{name} {description} {' '.join(topics)}"
        
        for keyword in crypto_keywords:
            if keyword in text_to_check:
                return True
                
        # Check if it's a Solidity project (strong indicator)
        if language == "solidity":
            return True
            
        return False
        
    def _determine_blockchain_from_repo(self, repo: Dict[str, Any]) -> Optional[BlockchainNetwork]:
        """Determine blockchain from repository information."""
        name = repo.get("name", "").lower()
        description = repo.get("description", "").lower() if repo.get("description") else ""
        topics = [topic.lower() for topic in repo.get("topics", [])]
        
        text_to_check = f"{name} {description} {' '.join(topics)}"
        
        # Blockchain-specific keywords
        blockchain_keywords = {
            BlockchainNetwork.ETHEREUM: ["ethereum", "eth", "erc20", "erc721", "mainnet"],
            BlockchainNetwork.BINANCE_SMART_CHAIN: ["bsc", "binance", "bnb", "pancakeswap"],
            BlockchainNetwork.POLYGON: ["polygon", "matic", "pos"],
            BlockchainNetwork.ARBITRUM: ["arbitrum", "arb"],
            BlockchainNetwork.OPTIMISM: ["optimism", "optimistic"],
            BlockchainNetwork.AVALANCHE: ["avalanche", "avax"],
            BlockchainNetwork.SOLANA: ["solana", "sol", "spl"],
            BlockchainNetwork.CARDANO: ["cardano", "ada"],
            BlockchainNetwork.POLKADOT: ["polkadot", "dot", "substrate"],
            BlockchainNetwork.COSMOS: ["cosmos", "atom", "tendermint"]
        }
        
        for blockchain, keywords in blockchain_keywords.items():
            for keyword in keywords:
                if keyword in text_to_check:
                    return blockchain
        
        # Default to Ethereum for Solidity projects
        if repo.get("language", "").lower() == "solidity":
            return BlockchainNetwork.ETHEREUM
            
        return None
        
    def _determine_category_from_repo(self, repo: Dict[str, Any]) -> Optional[ProjectCategory]:
        """Determine project category from repository information."""
        name = repo.get("name", "").lower()
        description = repo.get("description", "").lower() if repo.get("description") else ""
        topics = [topic.lower() for topic in repo.get("topics", [])]
        
        text_to_check = f"{name} {description} {' '.join(topics)}"
        
        # Category-specific keywords
        category_keywords = {
            ProjectCategory.DEFI: [
                "defi", "decentralized-finance", "swap", "exchange", "dex",
                "lending", "borrowing", "yield", "farming", "liquidity",
                "uniswap", "sushiswap", "compound", "aave", "curve"
            ],
            ProjectCategory.NFT: [
                "nft", "non-fungible", "collectible", "art", "erc721",
                "opensea", "marketplace", "gaming", "metaverse"
            ],
            ProjectCategory.DAO: [
                "dao", "governance", "voting", "community", "decentralized-autonomous"
            ],
            ProjectCategory.DEX: [
                "dex", "exchange", "swap", "trading", "amm", "automated-market-maker"
            ],
            ProjectCategory.LENDING: [
                "lending", "borrowing", "loan", "credit", "collateral"
            ],
            ProjectCategory.YIELD_FARMING: [
                "yield", "farming", "staking", "rewards", "incentive"
            ],
            ProjectCategory.STAKING: [
                "staking", "validator", "stake", "pos", "proof-of-stake"
            ],
            ProjectCategory.BRIDGE: [
                "bridge", "cross-chain", "multichain", "interoperability"
            ],
            ProjectCategory.ORACLE: [
                "oracle", "price-feed", "data", "chainlink", "band"
            ],
            ProjectCategory.WALLET: [
                "wallet", "custody", "keys", "metamask", "hardware"
            ],
            ProjectCategory.INFRASTRUCTURE: [
                "infrastructure", "node", "rpc", "indexer", "graph"
            ],
            ProjectCategory.GAMING: [
                "gaming", "game", "play-to-earn", "gamefi"
            ]
        }
        
        for category, keywords in category_keywords.items():
            for keyword in keywords:
                if keyword in text_to_check:
                    return category
        
        return ProjectCategory.OTHER
