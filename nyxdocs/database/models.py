"""SQLAlchemy database models."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..models import (
    BlockchainNetwork,
    DocumentationType,
    ProjectCategory,
    ProjectStatus,
    ScrapeStatus,
)

Base = declarative_base()


class ProjectTable(Base):
    """Project database table."""
    
    __tablename__ = "projects"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, index=True)
    symbol = Column(String, nullable=True, index=True)
    blockchain = Column(Enum(BlockchainNetwork), nullable=True, index=True)
    category = Column(Enum(ProjectCategory), nullable=True, index=True)
    description = Column(Text, nullable=True)
    website = Column(String, nullable=True)
    github_repo = Column(String, nullable=True)
    market_cap = Column(Float, nullable=True)
    status = Column(Enum(ProjectStatus), default=ProjectStatus.ACTIVE, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    documentation = relationship("DocumentationTable", back_populates="project", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("name", "blockchain", name="uq_project_name_blockchain"),
    )


class DocumentationTable(Base):
    """Documentation database table."""
    
    __tablename__ = "documentation"
    
    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    url = Column(String, nullable=False)
    doc_type = Column(Enum(DocumentationType), nullable=False, index=True)
    content = Column(Text, nullable=True)
    content_hash = Column(String, nullable=True, index=True)
    scrape_status = Column(Enum(ScrapeStatus), default=ScrapeStatus.PENDING, index=True)
    last_scraped = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    project = relationship("ProjectTable", back_populates="documentation")
    update_records = relationship("UpdateRecordTable", back_populates="documentation", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("project_id", "url", name="uq_documentation_project_url"),
    )


class UpdateRecordTable(Base):
    """Update record database table."""
    
    __tablename__ = "update_records"
    
    id = Column(String, primary_key=True)
    documentation_id = Column(String, ForeignKey("documentation.id"), nullable=False, index=True)
    old_hash = Column(String, nullable=True)
    new_hash = Column(String, nullable=False)
    changes_detected = Column(Boolean, nullable=False, default=False)
    checked_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    
    # Relationships
    documentation = relationship("DocumentationTable", back_populates="update_records")


class ScrapingJobTable(Base):
    """Scraping job database table for background task management."""
    
    __tablename__ = "scraping_jobs"
    
    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    documentation_id = Column(String, ForeignKey("documentation.id"), nullable=True, index=True)
    job_type = Column(String, nullable=False, index=True)  # 'discovery', 'scrape', 'update'
    status = Column(String, default="pending", index=True)  # 'pending', 'running', 'completed', 'failed'
    priority = Column(Integer, default=5, index=True)
    scheduled_at = Column(DateTime, default=func.now(), nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # Relationships
    project = relationship("ProjectTable")
    documentation = relationship("DocumentationTable")


class CacheTable(Base):
    """Cache table for storing temporary data."""
    
    __tablename__ = "cache"
    
    key = Column(String, primary_key=True)
    value = Column(Text, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)


class MetricsTable(Base):
    """Metrics table for storing system statistics."""
    
    __tablename__ = "metrics"
    
    id = Column(String, primary_key=True)
    metric_name = Column(String, nullable=False, index=True)
    metric_value = Column(Float, nullable=False)
    labels = Column(Text, nullable=True)  # JSON string for metric labels
    timestamp = Column(DateTime, default=func.now(), nullable=False, index=True)
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("metric_name", "timestamp", name="uq_metrics_name_timestamp"),
    )
