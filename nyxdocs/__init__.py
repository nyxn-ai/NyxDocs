"""
NyxnDocs - Cryptocurrency Documentation MCP Server

A specialized Model Context Protocol server for cryptocurrency project documentation.
Provides real-time access to crypto project docs, blockchain info, and development resources.
"""

__version__ = "0.1.6"
__author__ = "nyxn-ai"
__email__ = "info@nyxn.ai"
__license__ = "MIT"

from .server import create_server

__all__ = ["create_server", "__version__"]
