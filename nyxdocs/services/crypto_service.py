"""Cryptocurrency service for handling project and documentation operations."""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import and_, desc, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database.models import DocumentationTable, ProjectTable, UpdateRecordTable
from ..database.session import DatabaseManager
from ..models import (
    BlockchainInfo,
    BlockchainNetwork,
    Documentation,
    DocumentationRequest,
    DocumentationResponse,
    Project,
    ProjectCategory,
    ProjectInfoRequest,
    ProjectInfoResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
    SystemStats,
    UpdateCheckRequest,
    UpdateCheckResponse,
    UpdateRecord,
)

logger = logging.getLogger(__name__)


class CryptoService:
    """Service for cryptocurrency project and documentation operations."""
    
    def __init__(self, db_manager: DatabaseManager):
        """Initialize the crypto service."""
        self.db_manager = db_manager
    
    async def search_projects(self, request: SearchRequest) -> SearchResponse:
        """Search for cryptocurrency projects."""
        async with self.db_manager.get_session() as session:
            # Build query
            query = session.query(ProjectTable).options(
                selectinload(ProjectTable.documentation)
            )
            
            # Apply filters
            filters = []
            
            if request.query:
                # Search in name, symbol, and description
                search_term = f"%{request.query}%"
                filters.append(
                    or_(
                        ProjectTable.name.ilike(search_term),
                        ProjectTable.symbol.ilike(search_term),
                        ProjectTable.description.ilike(search_term)
                    )
                )
            
            if request.blockchain:
                filters.append(ProjectTable.blockchain == request.blockchain)
            
            if request.category:
                filters.append(ProjectTable.category == request.category)
            
            # Only active projects
            filters.append(ProjectTable.status == "active")
            
            if filters:
                query = query.filter(and_(*filters))
            
            # Order by market cap (descending) and name
            query = query.order_by(
                desc(ProjectTable.market_cap),
                ProjectTable.name
            )
            
            # Apply limit
            query = query.limit(request.limit)
            
            # Execute query
            result = await session.execute(query)
            projects = result.scalars().all()
            
            # Convert to response format
            search_results = []
            for project in projects:
                # Count documentation
                doc_count = len([doc for doc in project.documentation if doc.scrape_status == "success"])
                
                # Get last update time
                last_updated = None
                if project.documentation:
                    last_updated = max(
                        (doc.updated_at for doc in project.documentation if doc.updated_at),
                        default=None
                    )
                
                search_results.append(SearchResult(
                    project=self._convert_project(project),
                    documentation_count=doc_count,
                    last_updated=last_updated
                ))
            
            return SearchResponse(
                results=search_results,
                total=len(search_results),
                query=request.query
            )
    
    async def get_project_info(self, request: ProjectInfoRequest) -> Optional[ProjectInfoResponse]:
        """Get detailed project information."""
        async with self.db_manager.get_session() as session:
            # Search for project by name or symbol
            query = session.query(ProjectTable).options(
                selectinload(ProjectTable.documentation)
            ).filter(
                or_(
                    ProjectTable.name.ilike(f"%{request.project_name}%"),
                    ProjectTable.symbol.ilike(f"%{request.project_name}%")
                )
            ).order_by(
                desc(ProjectTable.market_cap)
            )
            
            result = await session.execute(query)
            project = result.scalars().first()
            
            if not project:
                return None
            
            # Convert project
            project_model = self._convert_project(project)
            
            # Prepare response
            response = ProjectInfoResponse(project=project_model)
            
            # Add documentation if requested
            if request.include_documentation:
                response.documentation = [
                    self._convert_documentation(doc) for doc in project.documentation
                ]
            
            # Add blockchain info if requested
            if request.include_blockchain_info and project.blockchain:
                response.blockchain_info = await self._get_blockchain_info(project.blockchain)
            
            return response
    
    async def get_documentation(self, request: DocumentationRequest) -> Optional[DocumentationResponse]:
        """Get documentation content for a project."""
        async with self.db_manager.get_session() as session:
            # Find project
            project_query = session.query(ProjectTable).filter(
                or_(
                    ProjectTable.name.ilike(f"%{request.project_name}%"),
                    ProjectTable.symbol.ilike(f"%{request.project_name}%")
                )
            ).order_by(desc(ProjectTable.market_cap))
            
            project_result = await session.execute(project_query)
            project = project_result.scalars().first()
            
            if not project:
                return None
            
            # Get documentation
            doc_query = session.query(DocumentationTable).filter(
                and_(
                    DocumentationTable.project_id == project.id,
                    DocumentationTable.scrape_status == "success",
                    DocumentationTable.content.isnot(None)
                )
            )
            
            # Filter by title if specified
            if request.doc_title:
                doc_query = doc_query.filter(
                    DocumentationTable.title.ilike(f"%{request.doc_title}%")
                )
            
            doc_query = doc_query.order_by(desc(DocumentationTable.last_scraped))
            
            doc_result = await session.execute(doc_query)
            documents = doc_result.scalars().all()
            
            if not documents:
                return None
            
            return DocumentationResponse(
                project_name=project.name,
                documents=[self._convert_documentation(doc) for doc in documents]
            )
    
    async def check_updates(self, request: UpdateCheckRequest) -> UpdateCheckResponse:
        """Check for documentation updates."""
        async with self.db_manager.get_session() as session:
            # Build query for update records
            query = session.query(UpdateRecordTable).join(
                DocumentationTable
            ).join(ProjectTable)
            
            filters = []
            
            # Filter by project name if specified
            if request.project_name:
                filters.append(
                    or_(
                        ProjectTable.name.ilike(f"%{request.project_name}%"),
                        ProjectTable.symbol.ilike(f"%{request.project_name}%")
                    )
                )
            
            # Filter by date if specified
            if request.since:
                filters.append(UpdateRecordTable.checked_at >= request.since)
            
            if filters:
                query = query.filter(and_(*filters))
            
            # Order by check time (most recent first)
            query = query.order_by(desc(UpdateRecordTable.checked_at))
            
            # Apply limit
            query = query.limit(request.limit)
            
            # Execute query
            result = await session.execute(query)
            update_records = result.scalars().all()
            
            # Convert to response format
            updates = [self._convert_update_record(record) for record in update_records]
            
            return UpdateCheckResponse(
                updates=updates,
                total=len(updates)
            )
    
    async def get_supported_blockchains(self) -> List[BlockchainInfo]:
        """Get list of supported blockchain networks with project counts."""
        async with self.db_manager.get_session() as session:
            # Get project counts by blockchain
            query = session.query(
                ProjectTable.blockchain,
                func.count(ProjectTable.id).label("project_count")
            ).filter(
                ProjectTable.status == "active"
            ).group_by(ProjectTable.blockchain)
            
            result = await session.execute(query)
            blockchain_counts = dict(result.all())
            
            # Create blockchain info list
            blockchains = []
            for blockchain in BlockchainNetwork:
                count = blockchain_counts.get(blockchain, 0)
                
                # Get blockchain metadata
                blockchain_info = self._get_blockchain_metadata(blockchain)
                blockchain_info.project_count = count
                
                blockchains.append(blockchain_info)
            
            # Sort by project count (descending)
            blockchains.sort(key=lambda x: x.project_count, reverse=True)
            
            return blockchains
    
    async def get_project_categories(self) -> List[Dict[str, any]]:
        """Get project categories with counts."""
        async with self.db_manager.get_session() as session:
            # Get project counts by category
            query = session.query(
                ProjectTable.category,
                func.count(ProjectTable.id).label("project_count")
            ).filter(
                ProjectTable.status == "active"
            ).group_by(ProjectTable.category)
            
            result = await session.execute(query)
            category_data = result.all()
            
            # Convert to list format
            categories = []
            for category, count in category_data:
                if category:  # Skip None categories
                    categories.append({
                        "name": category.value,
                        "count": count
                    })
            
            # Sort by count (descending)
            categories.sort(key=lambda x: x["count"], reverse=True)
            
            return categories
    
    async def get_system_stats(self) -> SystemStats:
        """Get system statistics."""
        async with self.db_manager.get_session() as session:
            # Get project counts
            total_projects = await session.scalar(
                session.query(func.count(ProjectTable.id))
            )
            
            active_projects = await session.scalar(
                session.query(func.count(ProjectTable.id)).filter(
                    ProjectTable.status == "active"
                )
            )
            
            # Get documentation counts
            total_documents = await session.scalar(
                session.query(func.count(DocumentationTable.id))
            )
            
            successful_scrapes = await session.scalar(
                session.query(func.count(DocumentationTable.id)).filter(
                    DocumentationTable.scrape_status == "success"
                )
            )
            
            failed_scrapes = await session.scalar(
                session.query(func.count(DocumentationTable.id)).filter(
                    DocumentationTable.scrape_status == "failed"
                )
            )
            
            # Get last update time
            last_update = await session.scalar(
                session.query(func.max(ProjectTable.updated_at))
            )
            
            # Get blockchain info
            supported_blockchains = await self.get_supported_blockchains()
            
            return SystemStats(
                total_projects=total_projects or 0,
                total_documents=total_documents or 0,
                active_projects=active_projects or 0,
                successful_scrapes=successful_scrapes or 0,
                failed_scrapes=failed_scrapes or 0,
                last_update=last_update,
                supported_blockchains=supported_blockchains
            )
    
    def _convert_project(self, project: ProjectTable) -> Project:
        """Convert database project to model."""
        return Project(
            id=project.id,
            name=project.name,
            symbol=project.symbol,
            blockchain=project.blockchain,
            category=project.category,
            description=project.description,
            website=project.website,
            github_repo=project.github_repo,
            market_cap=project.market_cap,
            status=project.status,
            created_at=project.created_at,
            updated_at=project.updated_at
        )
    
    def _convert_documentation(self, doc: DocumentationTable) -> Documentation:
        """Convert database documentation to model."""
        return Documentation(
            id=doc.id,
            project_id=doc.project_id,
            title=doc.title,
            url=doc.url,
            doc_type=doc.doc_type,
            content=doc.content,
            content_hash=doc.content_hash,
            scrape_status=doc.scrape_status,
            last_scraped=doc.last_scraped,
            error_message=doc.error_message,
            created_at=doc.created_at,
            updated_at=doc.updated_at
        )
    
    def _convert_update_record(self, record: UpdateRecordTable) -> UpdateRecord:
        """Convert database update record to model."""
        return UpdateRecord(
            id=record.id,
            documentation_id=record.documentation_id,
            old_hash=record.old_hash,
            new_hash=record.new_hash,
            changes_detected=record.changes_detected,
            checked_at=record.checked_at
        )
    
    def _get_blockchain_metadata(self, blockchain: BlockchainNetwork) -> BlockchainInfo:
        """Get blockchain metadata."""
        metadata = {
            BlockchainNetwork.ETHEREUM: {
                "name": "Ethereum",
                "symbol": "ETH",
                "chain_id": 1,
                "explorer_url": "https://etherscan.io"
            },
            BlockchainNetwork.BINANCE_SMART_CHAIN: {
                "name": "Binance Smart Chain",
                "symbol": "BNB",
                "chain_id": 56,
                "explorer_url": "https://bscscan.com"
            },
            BlockchainNetwork.POLYGON: {
                "name": "Polygon",
                "symbol": "MATIC",
                "chain_id": 137,
                "explorer_url": "https://polygonscan.com"
            },
            BlockchainNetwork.ARBITRUM: {
                "name": "Arbitrum One",
                "symbol": "ETH",
                "chain_id": 42161,
                "explorer_url": "https://arbiscan.io"
            },
            BlockchainNetwork.OPTIMISM: {
                "name": "Optimism",
                "symbol": "ETH",
                "chain_id": 10,
                "explorer_url": "https://optimistic.etherscan.io"
            },
            BlockchainNetwork.AVALANCHE: {
                "name": "Avalanche",
                "symbol": "AVAX",
                "chain_id": 43114,
                "explorer_url": "https://snowtrace.io"
            },
            BlockchainNetwork.SOLANA: {
                "name": "Solana",
                "symbol": "SOL",
                "explorer_url": "https://explorer.solana.com"
            },
            BlockchainNetwork.CARDANO: {
                "name": "Cardano",
                "symbol": "ADA",
                "explorer_url": "https://cardanoscan.io"
            },
            BlockchainNetwork.POLKADOT: {
                "name": "Polkadot",
                "symbol": "DOT",
                "explorer_url": "https://polkadot.subscan.io"
            },
            BlockchainNetwork.COSMOS: {
                "name": "Cosmos",
                "symbol": "ATOM",
                "explorer_url": "https://www.mintscan.io/cosmos"
            }
        }
        
        info = metadata.get(blockchain, {
            "name": blockchain.value.replace("-", " ").title(),
            "symbol": "UNKNOWN"
        })
        
        return BlockchainInfo(
            name=info["name"],
            symbol=info["symbol"],
            chain_id=info.get("chain_id"),
            rpc_url=info.get("rpc_url"),
            explorer_url=info.get("explorer_url"),
            project_count=0  # Will be set by caller
        )
    
    async def _get_blockchain_info(self, blockchain: BlockchainNetwork) -> Dict[str, any]:
        """Get blockchain information as dictionary."""
        blockchain_info = self._get_blockchain_metadata(blockchain)
        return {
            "name": blockchain_info.name,
            "symbol": blockchain_info.symbol,
            "chain_id": blockchain_info.chain_id,
            "explorer_url": blockchain_info.explorer_url
        }
