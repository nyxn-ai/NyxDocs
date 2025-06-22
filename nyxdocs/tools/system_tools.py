"""System and utility MCP tools."""

import logging
from typing import List

from mcp.server.fastmcp import Context, FastMCP
from pydantic import BaseModel, Field

from ..models import BlockchainNetwork, ProjectCategory
from ..services.crypto_service import CryptoService

logger = logging.getLogger(__name__)


def register_system_tools(server: FastMCP) -> None:
    """Register system and utility MCP tools."""
    
    @server.tool(
        name="list_blockchains",
        description="List all supported blockchain networks with project counts and information."
    )
    async def list_blockchains(ctx: Context) -> str:
        """List supported blockchain networks."""
        try:
            # Get services from context
            lifespan_context = ctx.request_context.lifespan_context
            crypto_service = CryptoService(lifespan_context["db_manager"])
            
            # Get blockchain information
            blockchains = await crypto_service.get_supported_blockchains()
            
            if not blockchains:
                return "No blockchain networks configured"
            
            # Format response
            blockchain_text = "**Supported Blockchain Networks:**\n\n"
            
            for blockchain in blockchains:
                blockchain_text += f"**{blockchain.name}**\n"
                blockchain_text += f"- Symbol: {blockchain.symbol}\n"
                blockchain_text += f"- Projects: {blockchain.project_count}\n"
                if blockchain.chain_id:
                    blockchain_text += f"- Chain ID: {blockchain.chain_id}\n"
                if blockchain.explorer_url:
                    blockchain_text += f"- Explorer: {blockchain.explorer_url}\n"
                blockchain_text += "\n"
            
            return blockchain_text.strip()
            
        except Exception as e:
            logger.error(f"Error listing blockchains: {e}")
            return f"Error retrieving blockchain information: {str(e)}"
    
    @server.tool(
        name="list_categories",
        description="List all supported project categories with descriptions and project counts."
    )
    async def list_categories(ctx: Context) -> str:
        """List supported project categories."""
        try:
            # Get services from context
            lifespan_context = ctx.request_context.lifespan_context
            crypto_service = CryptoService(lifespan_context["db_manager"])
            
            # Get category information
            categories = await crypto_service.get_project_categories()
            
            # Format response
            category_text = "**Supported Project Categories:**\n\n"
            
            category_descriptions = {
                "DeFi": "Decentralized Finance protocols and applications",
                "NFT": "Non-Fungible Token platforms and marketplaces",
                "DAO": "Decentralized Autonomous Organizations",
                "DEX": "Decentralized Exchanges",
                "Lending": "Lending and borrowing protocols",
                "Yield Farming": "Yield farming and liquidity mining platforms",
                "Staking": "Staking protocols and validators",
                "Bridge": "Cross-chain bridges and interoperability",
                "Oracle": "Oracle networks and data providers",
                "Wallet": "Cryptocurrency wallets and custody solutions",
                "Infrastructure": "Blockchain infrastructure and tooling",
                "Gaming": "Blockchain gaming and GameFi",
                "Metaverse": "Metaverse and virtual world platforms",
                "Other": "Other cryptocurrency projects"
            }
            
            for category in categories:
                category_text += f"**{category['name']}**\n"
                category_text += f"- Projects: {category['count']}\n"
                if category['name'] in category_descriptions:
                    category_text += f"- Description: {category_descriptions[category['name']]}\n"
                category_text += "\n"
            
            return category_text.strip()
            
        except Exception as e:
            logger.error(f"Error listing categories: {e}")
            return f"Error retrieving category information: {str(e)}"
    
    @server.tool(
        name="get_system_stats",
        description="Get system statistics including total projects, documentation counts, and health status."
    )
    async def get_system_stats(ctx: Context) -> str:
        """Get system statistics."""
        try:
            # Get services from context
            lifespan_context = ctx.request_context.lifespan_context
            crypto_service = CryptoService(lifespan_context["db_manager"])
            
            # Get system statistics
            stats = await crypto_service.get_system_stats()
            
            # Format response
            stats_text = "**NyxDocs System Statistics:**\n\n"
            stats_text += f"**Projects:**\n"
            stats_text += f"- Total Projects: {stats.total_projects:,}\n"
            stats_text += f"- Active Projects: {stats.active_projects:,}\n"
            stats_text += f"- Total Documentation: {stats.total_documents:,}\n"
            stats_text += "\n"
            
            stats_text += f"**Documentation Status:**\n"
            stats_text += f"- Successful Scrapes: {stats.successful_scrapes:,}\n"
            stats_text += f"- Failed Scrapes: {stats.failed_scrapes:,}\n"
            if stats.total_documents > 0:
                success_rate = (stats.successful_scrapes / stats.total_documents) * 100
                stats_text += f"- Success Rate: {success_rate:.1f}%\n"
            stats_text += "\n"
            
            if stats.last_update:
                stats_text += f"**Last System Update:** {stats.last_update.strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
            
            stats_text += f"**Supported Blockchains:** {len(stats.supported_blockchains)}\n"
            for blockchain in stats.supported_blockchains[:5]:  # Show top 5
                stats_text += f"- {blockchain.name}: {blockchain.project_count} projects\n"
            
            if len(stats.supported_blockchains) > 5:
                stats_text += f"- ... and {len(stats.supported_blockchains) - 5} more\n"
            
            return stats_text.strip()
            
        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            return f"Error retrieving system statistics: {str(e)}"
    
    @server.tool(
        name="search_help",
        description="Get help and examples for using NyxDocs search and query features."
    )
    async def search_help(ctx: Context) -> str:
        """Provide help for using NyxDocs."""
        help_text = """**NyxDocs - Cryptocurrency Documentation MCP Server**

**Available Tools:**

1. **search_crypto_projects** - Search for cryptocurrency projects
   - Parameters: query (required), blockchain (optional), category (optional), limit (optional)
   - Example: search_crypto_projects(query="uniswap", blockchain="ethereum", category="DeFi")

2. **get_project_info** - Get detailed project information
   - Parameters: project_name (required), include_documentation, include_blockchain_info
   - Example: get_project_info(project_name="Uniswap")

3. **get_documentation** - Retrieve project documentation content
   - Parameters: project_name (required), doc_title (optional), format (optional)
   - Example: get_documentation(project_name="Uniswap", format="markdown")

4. **check_updates** - Check for recent documentation updates
   - Parameters: project_name (optional), since_days, limit
   - Example: check_updates(since_days=7, limit=10)

5. **list_blockchains** - List supported blockchain networks
   - No parameters required

6. **list_categories** - List supported project categories
   - No parameters required

7. **get_system_stats** - Get system statistics and health info
   - No parameters required

**Supported Blockchains:**
- Ethereum, Binance Smart Chain, Polygon, Arbitrum, Optimism
- Avalanche, Solana, Cardano, Polkadot, Cosmos

**Supported Categories:**
- DeFi, NFT, DAO, DEX, Lending, Yield Farming, Staking
- Bridge, Oracle, Wallet, Infrastructure, Gaming, Metaverse

**Search Tips:**
- Use project names, symbols, or keywords in queries
- Combine blockchain and category filters for precise results
- Check documentation updates regularly for latest information
- Use get_documentation for full content access

**Example Workflows:**
1. Find DeFi projects: search_crypto_projects(query="", category="DeFi", limit=20)
2. Get Ethereum projects: search_crypto_projects(query="", blockchain="ethereum")
3. Research specific project: get_project_info(project_name="Compound") → get_documentation(project_name="Compound")
4. Monitor updates: check_updates(since_days=1) for daily updates
"""
        return help_text
