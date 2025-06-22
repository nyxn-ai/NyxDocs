"""Cryptocurrency-specific MCP tools."""

import logging
from typing import List, Optional

from mcp.server.fastmcp import Context, FastMCP
from pydantic import BaseModel, Field

from ..models import (
    BlockchainNetwork,
    DocumentationRequest,
    ProjectCategory,
    ProjectInfoRequest,
    SearchRequest,
    UpdateCheckRequest,
)
from ..services.crypto_service import CryptoService

logger = logging.getLogger(__name__)


class SearchProjectsParams(BaseModel):
    """Parameters for searching crypto projects."""
    
    query: str = Field(..., description="Search query for cryptocurrency projects")
    blockchain: Optional[str] = Field(None, description="Filter by blockchain (e.g., 'ethereum', 'binance-smart-chain')")
    category: Optional[str] = Field(None, description="Filter by category (e.g., 'DeFi', 'NFT', 'DAO')")
    limit: int = Field(10, ge=1, le=50, description="Maximum number of results to return")


class GetProjectInfoParams(BaseModel):
    """Parameters for getting project information."""
    
    project_name: str = Field(..., description="Name or symbol of the cryptocurrency project")
    include_documentation: bool = Field(True, description="Include documentation list")
    include_blockchain_info: bool = Field(True, description="Include blockchain information")


class GetDocumentationParams(BaseModel):
    """Parameters for getting documentation content."""
    
    project_name: str = Field(..., description="Name or symbol of the cryptocurrency project")
    doc_title: Optional[str] = Field(None, description="Specific document title to retrieve")
    format: str = Field("markdown", description="Output format (markdown, html, text)")


class CheckUpdatesParams(BaseModel):
    """Parameters for checking documentation updates."""
    
    project_name: Optional[str] = Field(None, description="Specific project to check (optional)")
    since_days: int = Field(7, ge=1, le=30, description="Check updates from this many days ago")
    limit: int = Field(20, ge=1, le=100, description="Maximum number of updates to return")


def register_crypto_tools(server: FastMCP) -> None:
    """Register cryptocurrency-specific MCP tools."""
    
    @server.tool(
        name="search_crypto_projects",
        description="Search for cryptocurrency projects by name, blockchain, or category. "
                   "Returns project information including available documentation."
    )
    async def search_crypto_projects(
        params: SearchProjectsParams,
        ctx: Context
    ) -> str:
        """Search for cryptocurrency projects."""
        try:
            # Get services from context
            lifespan_context = ctx.request_context.lifespan_context
            crypto_service = CryptoService(lifespan_context["db_manager"])
            
            # Convert string parameters to enums if provided
            blockchain = None
            if params.blockchain:
                try:
                    blockchain = BlockchainNetwork(params.blockchain.lower().replace("-", "_"))
                except ValueError:
                    return f"Invalid blockchain: {params.blockchain}. Supported blockchains: {[b.value for b in BlockchainNetwork]}"
            
            category = None
            if params.category:
                try:
                    category = ProjectCategory(params.category)
                except ValueError:
                    return f"Invalid category: {params.category}. Supported categories: {[c.value for c in ProjectCategory]}"
            
            # Create search request
            search_request = SearchRequest(
                query=params.query,
                blockchain=blockchain,
                category=category,
                limit=params.limit
            )
            
            # Perform search
            response = await crypto_service.search_projects(search_request)
            
            if not response.results:
                return f"No cryptocurrency projects found matching '{params.query}'"
            
            # Format results
            results_text = f"Found {response.total} cryptocurrency projects matching '{params.query}':\n\n"
            
            for result in response.results:
                project = result.project
                results_text += f"**{project.name}**"
                if project.symbol:
                    results_text += f" ({project.symbol})"
                results_text += "\n"
                
                if project.blockchain:
                    results_text += f"- Blockchain: {project.blockchain.value}\n"
                if project.category:
                    results_text += f"- Category: {project.category.value}\n"
                if project.market_cap:
                    results_text += f"- Market Cap: ${project.market_cap:,.0f}\n"
                if project.website:
                    results_text += f"- Website: {project.website}\n"
                if project.github_repo:
                    results_text += f"- GitHub: {project.github_repo}\n"
                
                results_text += f"- Documentation: {result.documentation_count} documents available\n"
                
                if project.description:
                    desc = project.description[:200] + "..." if len(project.description) > 200 else project.description
                    results_text += f"- Description: {desc}\n"
                
                results_text += "\n---\n\n"
            
            return results_text.strip()
            
        except Exception as e:
            logger.error(f"Error searching crypto projects: {e}")
            return f"Error searching cryptocurrency projects: {str(e)}"
    
    @server.tool(
        name="get_project_info",
        description="Get detailed information about a specific cryptocurrency project, "
                   "including blockchain details and documentation status."
    )
    async def get_project_info(
        params: GetProjectInfoParams,
        ctx: Context
    ) -> str:
        """Get detailed project information."""
        try:
            # Get services from context
            lifespan_context = ctx.request_context.lifespan_context
            crypto_service = CryptoService(lifespan_context["db_manager"])
            
            # Create request
            request = ProjectInfoRequest(
                project_name=params.project_name,
                include_documentation=params.include_documentation,
                include_blockchain_info=params.include_blockchain_info
            )
            
            # Get project info
            response = await crypto_service.get_project_info(request)
            
            if not response:
                return f"Project '{params.project_name}' not found"
            
            project = response.project
            
            # Format response
            info_text = f"**{project.name}**\n"
            
            if project.symbol:
                info_text += f"Symbol: {project.symbol}\n"
            if project.blockchain:
                info_text += f"Blockchain: {project.blockchain.value}\n"
            if project.category:
                info_text += f"Category: {project.category.value}\n"
            if project.market_cap:
                info_text += f"Market Cap: ${project.market_cap:,.0f}\n"
            if project.website:
                info_text += f"Website: {project.website}\n"
            if project.github_repo:
                info_text += f"GitHub: {project.github_repo}\n"
            
            info_text += f"Status: {project.status.value}\n"
            
            if project.description:
                info_text += f"\n**Description:**\n{project.description}\n"
            
            # Add blockchain info if requested
            if response.blockchain_info and params.include_blockchain_info:
                info_text += f"\n**Blockchain Information:**\n"
                for key, value in response.blockchain_info.items():
                    info_text += f"- {key.replace('_', ' ').title()}: {value}\n"
            
            # Add documentation info if requested
            if response.documentation and params.include_documentation:
                info_text += f"\n**Available Documentation ({len(response.documentation)} documents):**\n"
                for doc in response.documentation:
                    info_text += f"- {doc.title} ({doc.doc_type.value})\n"
                    info_text += f"  URL: {doc.url}\n"
                    info_text += f"  Status: {doc.scrape_status.value}\n"
                    if doc.last_scraped:
                        info_text += f"  Last Updated: {doc.last_scraped.strftime('%Y-%m-%d %H:%M')}\n"
                    info_text += "\n"
            
            return info_text.strip()
            
        except Exception as e:
            logger.error(f"Error getting project info: {e}")
            return f"Error getting project information: {str(e)}"
    
    @server.tool(
        name="get_documentation",
        description="Retrieve actual documentation content for a cryptocurrency project. "
                   "Returns the full text content of available documentation."
    )
    async def get_documentation(
        params: GetDocumentationParams,
        ctx: Context
    ) -> str:
        """Get documentation content."""
        try:
            # Get services from context
            lifespan_context = ctx.request_context.lifespan_context
            crypto_service = CryptoService(lifespan_context["db_manager"])
            
            # Create request
            request = DocumentationRequest(
                project_name=params.project_name,
                doc_title=params.doc_title,
                format=params.format
            )
            
            # Get documentation
            response = await crypto_service.get_documentation(request)
            
            if not response or not response.documents:
                return f"No documentation found for project '{params.project_name}'"
            
            # Format response
            doc_text = f"**Documentation for {response.project_name}**\n\n"
            
            for doc in response.documents:
                doc_text += f"## {doc.title}\n"
                doc_text += f"Source: {doc.url}\n"
                doc_text += f"Type: {doc.doc_type.value}\n"
                if doc.last_scraped:
                    doc_text += f"Last Updated: {doc.last_scraped.strftime('%Y-%m-%d %H:%M')}\n"
                doc_text += "\n"
                
                if doc.content:
                    # Limit content length for display
                    content = doc.content
                    if len(content) > 10000:
                        content = content[:10000] + "\n\n[Content truncated - full documentation available]"
                    doc_text += f"### Content:\n{content}\n"
                else:
                    doc_text += "Content not available or not yet scraped.\n"
                
                doc_text += "\n---\n\n"
            
            return doc_text.strip()
            
        except Exception as e:
            logger.error(f"Error getting documentation: {e}")
            return f"Error retrieving documentation: {str(e)}"
    
    @server.tool(
        name="check_updates",
        description="Check for recent documentation updates across projects or for a specific project. "
                   "Shows what documentation has been updated recently."
    )
    async def check_updates(
        params: CheckUpdatesParams,
        ctx: Context
    ) -> str:
        """Check for documentation updates."""
        try:
            # Get services from context
            lifespan_context = ctx.request_context.lifespan_context
            crypto_service = CryptoService(lifespan_context["db_manager"])
            
            # Create request
            from datetime import datetime, timedelta
            since_date = datetime.utcnow() - timedelta(days=params.since_days)
            
            request = UpdateCheckRequest(
                project_name=params.project_name,
                since=since_date,
                limit=params.limit
            )
            
            # Check updates
            response = await crypto_service.check_updates(request)
            
            if not response.updates:
                time_desc = f"last {params.since_days} days"
                project_desc = f" for {params.project_name}" if params.project_name else ""
                return f"No documentation updates found{project_desc} in the {time_desc}"
            
            # Format response
            updates_text = f"**Documentation Updates** ({response.total} total)\n"
            if params.project_name:
                updates_text += f"Project: {params.project_name}\n"
            updates_text += f"Period: Last {params.since_days} days\n\n"
            
            for update in response.updates:
                updates_text += f"• **Update on {update.checked_at.strftime('%Y-%m-%d %H:%M')}**\n"
                updates_text += f"  Changes Detected: {'Yes' if update.changes_detected else 'No'}\n"
                if update.old_hash and update.new_hash:
                    updates_text += f"  Hash: {update.old_hash[:8]}... → {update.new_hash[:8]}...\n"
                updates_text += "\n"
            
            return updates_text.strip()
            
        except Exception as e:
            logger.error(f"Error checking updates: {e}")
            return f"Error checking documentation updates: {str(e)}"
