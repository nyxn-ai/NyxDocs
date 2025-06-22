"""Command-line interface for NyxDocs."""

import asyncio
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .config import get_settings
from .database.session import DatabaseManager, set_db_manager
from .server import create_server
from .utils.logging import setup_logging

app = typer.Typer(
    name="nyxndocs",
    help="NyxnDocs - Cryptocurrency Documentation MCP Server",
    add_completion=False,
)

console = Console()


@app.command()
def server(
    host: str = typer.Option("localhost", help="Host to bind to"),
    port: int = typer.Option(8000, help="Port to bind to"),
    log_level: str = typer.Option("INFO", help="Log level"),
) -> None:
    """Start the NyxDocs MCP server."""
    settings = get_settings()
    
    # Override settings with CLI arguments
    settings.host = host
    settings.port = port
    settings.log_level = log_level
    
    # Setup logging
    setup_logging(settings.log_level)
    
    console.print(f"[bold green]Starting NyxnDocs MCP Server[/bold green]")
    console.print(f"Host: {host}")
    console.print(f"Port: {port}")
    console.print(f"Log Level: {log_level}")
    
    # Create and run server
    server_instance = create_server()
    
    try:
        asyncio.run(server_instance.run())
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Server error: {e}[/red]")
        sys.exit(1)


@app.command()
def init_db(
    database_url: Optional[str] = typer.Option(None, help="Database URL"),
    force: bool = typer.Option(False, help="Force recreate tables"),
) -> None:
    """Initialize the database."""
    settings = get_settings()
    
    if database_url:
        db_url = database_url
    else:
        db_url = settings.get_database_url()
    
    console.print(f"[bold blue]Initializing database[/bold blue]")
    console.print(f"Database URL: {db_url}")
    
    async def _init_db():
        db_manager = DatabaseManager(db_url)
        
        if force:
            console.print("[yellow]Force recreating tables...[/yellow]")
            # TODO: Add table dropping logic if needed
        
        await db_manager.initialize()
        await db_manager.close()
        
        console.print("[green]Database initialized successfully![/green]")
    
    try:
        asyncio.run(_init_db())
    except Exception as e:
        console.print(f"[red]Database initialization failed: {e}[/red]")
        sys.exit(1)


@app.command()
def config(
    show_all: bool = typer.Option(False, help="Show all configuration values"),
) -> None:
    """Show configuration information."""
    settings = get_settings()
    
    console.print("[bold blue]NyxnDocs Configuration[/bold blue]")
    
    # Create configuration table
    table = Table(title="Configuration Settings")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    table.add_column("Description", style="dim")
    
    # Core settings
    config_items = [
        ("MCP Server Name", settings.mcp_server_name, "MCP server identifier"),
        ("MCP Server Version", settings.mcp_server_version, "Server version"),
        ("Database URL", settings.get_database_url(), "Database connection"),
        ("Log Level", settings.log_level, "Logging verbosity"),
        ("Debug Mode", str(settings.debug), "Development mode"),
    ]
    
    if show_all:
        # Add more detailed settings
        config_items.extend([
            ("CoinGecko API", "Configured" if settings.coingecko_api_key else "Not configured", "CoinGecko API access"),
            ("GitHub Token", "Configured" if settings.github_token else "Not configured", "GitHub API access"),
            ("Auto Discovery", str(settings.enable_auto_discovery), "Automatic project discovery"),
            ("Update Monitoring", str(settings.enable_update_monitoring), "Documentation update monitoring"),
            ("Content Caching", str(settings.enable_content_caching), "Content caching"),
            ("Max Concurrent Scrapes", str(settings.max_concurrent_scrapes), "Scraping concurrency limit"),
            ("Request Timeout", f"{settings.request_timeout}s", "HTTP request timeout"),
        ])
    
    for setting, value, description in config_items:
        table.add_row(setting, value, description)
    
    console.print(table)
    
    # Show environment file status
    env_file = Path(".env")
    if env_file.exists():
        console.print(f"\n[green]Environment file found: {env_file.absolute()}[/green]")
    else:
        console.print(f"\n[yellow]No .env file found. Copy .env.example to .env and configure.[/yellow]")


@app.command()
def status() -> None:
    """Show system status and statistics."""
    console.print("[bold blue]NyxnDocs System Status[/bold blue]")
    
    async def _get_status():
        settings = get_settings()
        
        # Initialize database manager
        db_manager = DatabaseManager(settings.get_database_url())
        set_db_manager(db_manager)
        
        try:
            await db_manager.initialize()
            
            # Import here to avoid circular imports
            from .services.crypto_service import CryptoService
            
            crypto_service = CryptoService(db_manager)
            stats = await crypto_service.get_system_stats()
            
            # Create status table
            table = Table(title="System Statistics")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            
            table.add_row("Total Projects", f"{stats.total_projects:,}")
            table.add_row("Active Projects", f"{stats.active_projects:,}")
            table.add_row("Total Documentation", f"{stats.total_documents:,}")
            table.add_row("Successful Scrapes", f"{stats.successful_scrapes:,}")
            table.add_row("Failed Scrapes", f"{stats.failed_scrapes:,}")
            
            if stats.total_documents > 0:
                success_rate = (stats.successful_scrapes / stats.total_documents) * 100
                table.add_row("Success Rate", f"{success_rate:.1f}%")
            
            if stats.last_update:
                table.add_row("Last Update", stats.last_update.strftime("%Y-%m-%d %H:%M:%S UTC"))
            
            console.print(table)
            
            # Show blockchain distribution
            if stats.supported_blockchains:
                blockchain_table = Table(title="Blockchain Distribution")
                blockchain_table.add_column("Blockchain", style="cyan")
                blockchain_table.add_column("Projects", style="green")
                
                for blockchain in stats.supported_blockchains[:10]:  # Top 10
                    blockchain_table.add_row(blockchain.name, f"{blockchain.project_count:,}")
                
                console.print(blockchain_table)
            
        except Exception as e:
            console.print(f"[red]Error getting status: {e}[/red]")
        finally:
            await db_manager.close()
    
    try:
        asyncio.run(_get_status())
    except Exception as e:
        console.print(f"[red]Status check failed: {e}[/red]")
        sys.exit(1)


@app.command()
def version() -> None:
    """Show version information."""
    from . import __version__
    
    console.print(f"[bold green]NyxnDocs[/bold green] version [cyan]{__version__}[/cyan]")
    console.print("Cryptocurrency Documentation MCP Server")
    console.print("Built with Python and FastMCP")


def main() -> None:
    """Main CLI entry point."""
    app()


if __name__ == "__main__":
    main()
