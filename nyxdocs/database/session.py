"""Database session management."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from .models import Base

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Database connection and session manager."""
    
    def __init__(self, database_url: str):
        """Initialize database manager with connection URL."""
        self.database_url = database_url
        self.engine = None
        self.session_factory = None
        
    async def initialize(self) -> None:
        """Initialize database engine and create tables."""
        logger.info(f"Initializing database: {self.database_url}")
        
        # Configure engine based on database type
        if self.database_url.startswith("sqlite"):
            # SQLite configuration
            self.engine = create_async_engine(
                self.database_url.replace("sqlite://", "sqlite+aiosqlite://"),
                echo=False,
                poolclass=StaticPool,
                connect_args={
                    "check_same_thread": False,
                },
            )
        else:
            # PostgreSQL or other databases
            self.engine = create_async_engine(
                self.database_url,
                echo=False,
                pool_size=10,
                max_overflow=20,
                pool_timeout=30,
            )
        
        # Create session factory
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        
        # Create tables
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database initialized successfully")
    
    async def close(self) -> None:
        """Close database connections."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connections closed")
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session."""
        if not self.session_factory:
            raise RuntimeError("Database not initialized")
        
        async with self.session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def set_db_manager(manager: DatabaseManager) -> None:
    """Set the global database manager."""
    global _db_manager
    _db_manager = manager


def get_db_manager() -> DatabaseManager:
    """Get the global database manager."""
    if _db_manager is None:
        raise RuntimeError("Database manager not initialized")
    return _db_manager


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session from the global manager."""
    manager = get_db_manager()
    async with manager.get_session() as session:
        yield session
