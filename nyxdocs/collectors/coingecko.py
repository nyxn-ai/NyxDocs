"""CoinGecko data collector for cryptocurrency projects."""

import logging
from typing import Any, Dict, List, Optional

from ..models import BlockchainNetwork, ProjectCategory
from .base import BaseCollector

logger = logging.getLogger(__name__)


class CoinGeckoCollector(BaseCollector):
    """Collector for CoinGecko cryptocurrency data."""
    
    BASE_URL = "https://api.coingecko.com/api/v3"
    
    def __init__(self):
        """Initialize CoinGecko collector."""
        super().__init__("CoinGecko")
        self.api_key = self.settings.coingecko_api_key
        
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for CoinGecko API requests."""
        headers = {}
        if self.api_key:
            headers["X-CG-Demo-API-Key"] = self.api_key
        return headers
        
    async def collect_projects(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Collect cryptocurrency projects from CoinGecko."""
        logger.info(f"Collecting {limit} projects from CoinGecko")
        
        projects = []
        per_page = min(250, limit)  # CoinGecko max per page
        pages_needed = (limit + per_page - 1) // per_page
        
        for page in range(1, pages_needed + 1):
            current_limit = min(per_page, limit - len(projects))
            
            try:
                data = await self.make_request(
                    f"{self.BASE_URL}/coins/markets",
                    params={
                        "vs_currency": "usd",
                        "order": "market_cap_desc",
                        "per_page": current_limit,
                        "page": page,
                        "sparkline": False,
                        "price_change_percentage": "24h"
                    },
                    headers=self._get_headers()
                )
                
                for coin in data:
                    project = await self._convert_coin_to_project(coin)
                    if project:
                        projects.append(project)
                
                # Rate limiting
                await self.rate_limit(1.0)
                
            except Exception as e:
                logger.error(f"Error collecting CoinGecko page {page}: {e}")
                break
                
        logger.info(f"Collected {len(projects)} projects from CoinGecko")
        return projects
        
    async def get_project_details(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed project information from CoinGecko."""
        try:
            data = await self.make_request(
                f"{self.BASE_URL}/coins/{project_id}",
                params={
                    "localization": False,
                    "tickers": False,
                    "market_data": True,
                    "community_data": False,
                    "developer_data": False,
                    "sparkline": False
                },
                headers=self._get_headers()
            )
            
            return await self._convert_detailed_coin_to_project(data)
            
        except Exception as e:
            logger.error(f"Error getting CoinGecko details for {project_id}: {e}")
            return None
            
    async def _convert_coin_to_project(self, coin: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert CoinGecko coin data to project format."""
        try:
            # Determine blockchain from platforms
            blockchain = self._determine_blockchain(coin.get("platforms", {}))
            
            # Determine category
            category = self._determine_category(coin.get("name", ""), coin.get("symbol", ""))
            
            return {
                "id": coin["id"],
                "name": coin["name"],
                "symbol": coin["symbol"].upper() if coin.get("symbol") else None,
                "blockchain": blockchain,
                "category": category,
                "description": None,  # Not available in markets endpoint
                "website": None,  # Not available in markets endpoint
                "github_repo": None,  # Not available in markets endpoint
                "market_cap": coin.get("market_cap"),
                "status": "active",
                "source": "coingecko",
                "external_id": coin["id"]
            }
            
        except Exception as e:
            logger.error(f"Error converting coin {coin.get('id', 'unknown')}: {e}")
            return None
            
    async def _convert_detailed_coin_to_project(self, coin: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert detailed CoinGecko coin data to project format."""
        try:
            # Determine blockchain from platforms
            blockchain = self._determine_blockchain(coin.get("platforms", {}))
            
            # Determine category
            category = self._determine_category(coin.get("name", ""), coin.get("symbol", ""))
            
            # Extract links
            links = coin.get("links", {})
            website = None
            github_repo = None
            
            if links.get("homepage") and links["homepage"][0]:
                website = links["homepage"][0]
                
            if links.get("repos_url", {}).get("github") and links["repos_url"]["github"]:
                github_repo = links["repos_url"]["github"][0]
            
            # Extract description
            description = None
            if coin.get("description", {}).get("en"):
                description = coin["description"]["en"]
                # Clean up description (remove HTML tags, limit length)
                if description:
                    import re
                    description = re.sub(r'<[^>]+>', '', description)
                    if len(description) > 1000:
                        description = description[:1000] + "..."
            
            # Extract market cap
            market_cap = None
            if coin.get("market_data", {}).get("market_cap", {}).get("usd"):
                market_cap = coin["market_data"]["market_cap"]["usd"]
            
            return {
                "id": coin["id"],
                "name": coin["name"],
                "symbol": coin["symbol"].upper() if coin.get("symbol") else None,
                "blockchain": blockchain,
                "category": category,
                "description": description,
                "website": website,
                "github_repo": github_repo,
                "market_cap": market_cap,
                "status": "active",
                "source": "coingecko",
                "external_id": coin["id"]
            }
            
        except Exception as e:
            logger.error(f"Error converting detailed coin {coin.get('id', 'unknown')}: {e}")
            return None
            
    def _determine_blockchain(self, platforms: Dict[str, Any]) -> Optional[BlockchainNetwork]:
        """Determine blockchain network from CoinGecko platforms data."""
        # Platform mapping from CoinGecko to our blockchain enum
        platform_mapping = {
            "ethereum": BlockchainNetwork.ETHEREUM,
            "binance-smart-chain": BlockchainNetwork.BINANCE_SMART_CHAIN,
            "polygon-pos": BlockchainNetwork.POLYGON,
            "arbitrum-one": BlockchainNetwork.ARBITRUM,
            "optimistic-ethereum": BlockchainNetwork.OPTIMISM,
            "avalanche": BlockchainNetwork.AVALANCHE,
            "solana": BlockchainNetwork.SOLANA,
            "cardano": BlockchainNetwork.CARDANO,
            "polkadot": BlockchainNetwork.POLKADOT,
            "cosmos": BlockchainNetwork.COSMOS,
        }
        
        # Check platforms for known blockchains
        for platform_id in platforms.keys():
            if platform_id in platform_mapping:
                return platform_mapping[platform_id]
        
        # Default to Ethereum for most tokens
        if platforms:
            return BlockchainNetwork.ETHEREUM
            
        return None
        
    def _determine_category(self, name: str, symbol: str) -> Optional[ProjectCategory]:
        """Determine project category based on name and symbol."""
        name_lower = name.lower()
        symbol_lower = symbol.lower() if symbol else ""
        
        # DeFi keywords
        defi_keywords = [
            "swap", "exchange", "dex", "uniswap", "sushiswap", "pancakeswap",
            "compound", "aave", "maker", "curve", "balancer", "yearn",
            "defi", "finance", "lending", "borrowing", "liquidity"
        ]
        
        # NFT keywords
        nft_keywords = [
            "nft", "collectible", "art", "gaming", "metaverse",
            "opensea", "rarible", "superrare", "foundation"
        ]
        
        # DAO keywords
        dao_keywords = [
            "dao", "governance", "voting", "community"
        ]
        
        # Oracle keywords
        oracle_keywords = [
            "oracle", "chainlink", "band", "tellor", "api3"
        ]
        
        # Bridge keywords
        bridge_keywords = [
            "bridge", "cross-chain", "multichain", "anyswap"
        ]
        
        # Staking keywords
        staking_keywords = [
            "staking", "validator", "stake", "staked"
        ]
        
        # Check categories
        for keyword in defi_keywords:
            if keyword in name_lower or keyword in symbol_lower:
                return ProjectCategory.DEFI
                
        for keyword in nft_keywords:
            if keyword in name_lower or keyword in symbol_lower:
                return ProjectCategory.NFT
                
        for keyword in dao_keywords:
            if keyword in name_lower or keyword in symbol_lower:
                return ProjectCategory.DAO
                
        for keyword in oracle_keywords:
            if keyword in name_lower or keyword in symbol_lower:
                return ProjectCategory.ORACLE
                
        for keyword in bridge_keywords:
            if keyword in name_lower or keyword in symbol_lower:
                return ProjectCategory.BRIDGE
                
        for keyword in staking_keywords:
            if keyword in name_lower or keyword in symbol_lower:
                return ProjectCategory.STAKING
        
        # Default to OTHER
        return ProjectCategory.OTHER
