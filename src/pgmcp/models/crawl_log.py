from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Self, Tuple  # Added Dict, Tuple

import blinker

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pgmcp.models.base import Base
from pgmcp.models.log_level import LogLevel


if TYPE_CHECKING:
    from pgmcp.models.crawl_item import CrawlItem
    from pgmcp.models.crawl_job import CrawlJob  


class CrawlLog(Base):
    """Represents a log entry for a crawl job or crawl item of a crawl job.
    
    These are usually emitted from the scrapy spider, processor, or pipeline phases.
    """

    __tablename__ = "crawl_logs"

    # == Columns ==============================================================
    id:              Mapped[int]            = mapped_column(Integer, primary_key=True, autoincrement=True)
    crawl_job_id:    Mapped[int]            = mapped_column(ForeignKey("crawl_jobs.id"), nullable=False)
    crawl_item_id:   Mapped[int | None]     = mapped_column(ForeignKey("crawl_items.id"), nullable=True)

    message:         Mapped[str]            = mapped_column(Text, nullable=False)
    context:         Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)
    level:           Mapped[str]            = mapped_column( Enum(LogLevel, name="log_level", native_enum=True), nullable=False, default=LogLevel.INFO ) 
    occurred_at:     Mapped[datetime]       = mapped_column(DateTime(timezone=True), nullable=False, default=func.now())

    # == Relationships ========================================================
    crawl_job:       Mapped["CrawlJob"]     = relationship("CrawlJob", back_populates="crawl_logs")
    crawl_item:      Mapped["CrawlItem"]    = relationship("CrawlItem", back_populates="crawl_logs", foreign_keys=[crawl_item_id])

    # == Methods ==============================================================
    @classmethod
    def from_crawl_job(cls, crawl_job: CrawlJob, message: str, level: LogLevel = LogLevel.INFO, context: Dict[str, Any] | None = None) -> CrawlLog:
        """Create a CrawlLog from a CrawlJob."""
        return cls( crawl_job_id=crawl_job.id, message=message, level=level, context=context )

    @classmethod
    def from_crawl_item(cls, crawl_item: CrawlItem, message: str, level: LogLevel = LogLevel.INFO, context: Dict[str, Any] | None = None) -> CrawlLog:
        """Create a CrawlLog from a CrawlItem."""
        return cls( crawl_item_id=crawl_item.id, crawl_job_id=crawl_item.crawl_job_id, message=message, level=level, context=context )

    def model_dump(self) -> Dict[str, Any]:
        """Convert the CrawlLog to a dictionary representation."""
        return {
            "id": self.id,
            "crawl_job_id": self.crawl_job_id,
            "crawl_item_id": self.crawl_item_id,
            "message": self.message,
            "context": self.context,
            "level": self.level,
            "occurred_at": self.occurred_at.isoformat() if self.occurred_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
