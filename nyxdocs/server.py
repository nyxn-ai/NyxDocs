"""Main MCP server implementation for NyxDocs."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from mcp.server.fastmcp import FastMCP

from .config import get_settings
from .database.session import DatabaseManager
from .tools import register_tools
from .utils.logging import setup_logging


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[dict]:
    """Manage application lifecycle with database and background tasks."""
    settings = get_settings()
    
    # Setup logging
    setup_logging(settings.log_level)
    logger = logging.getLogger(__name__)
    
    logger.info("Starting NyxnDocs MCP Server...")
    
    # Initialize database
    db_manager = DatabaseManager(settings.get_database_url())
    await db_manager.initialize()
    
    # Start background tasks if enabled
    background_tasks = []
    
    if settings.enable_auto_discovery:
        logger.info("Auto-discovery is enabled")
        # TODO: Start project discovery task
    
    if settings.enable_update_monitoring:
        logger.info("Update monitoring is enabled")
        # TODO: Start update monitoring task
    
    try:
        yield {
            "db_manager": db_manager,
            "settings": settings,
            "background_tasks": background_tasks,
        }
    finally:
        # Cleanup
        logger.info("Shutting down NyxnDocs MCP Server...")
        
        # Cancel background tasks
        for task in background_tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Close database connections
        await db_manager.close()
        
        logger.info("NyxnDocs MCP Server shutdown complete")


def create_server() -> FastMCP:
    """Create and configure the FastMCP server."""
    settings = get_settings()
    
    # Create server with lifespan management
    server = FastMCP(
        name=settings.mcp_server_name,
        lifespan=app_lifespan,
    )
    
    # Register all MCP tools
    register_tools(server)
    
    return server


async def main():
    """Main entry point for running the server."""
    server = create_server()
    
    # Run the server
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
