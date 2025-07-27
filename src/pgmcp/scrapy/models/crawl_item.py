from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Integer, String, Text  # Added Text and ForeignKey
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pgmcp.scrapy.models.base import Base

from .log_level import LogLevel


if TYPE_CHECKING:
    from pgmcp.scrapy.models.crawl_job import CrawlJob
    from pgmcp.scrapy.models.crawl_log import CrawlLog

class CrawlItem(Base):
    """Represents a web crawling job."""
    __tablename__ = "crawl_items"

    # == Columns ============================================================== 
    
    crawl_job_id     : Mapped[int]            = mapped_column(ForeignKey("crawl_jobs.id"), nullable=False)
    body             : Mapped[str]            = mapped_column(Text,         nullable=False)
    url              : Mapped[str]            = mapped_column(String(2048), nullable=False)
    status           : Mapped[int]            = mapped_column(Integer,      nullable=False)  # http status code
    request_headers  : Mapped[Dict[str, Any]] = mapped_column(JSON,         nullable=False)
    response_headers : Mapped[Dict[str, Any]] = mapped_column(JSON,         nullable=False)
    depth            : Mapped[int]            = mapped_column(Integer,      nullable=False)
    referer          : Mapped[str | None]     = mapped_column(String(2048), nullable=True)

    # == Relationships ========================================================
    
    # belongs_to CrawlJob (Many-to-One relationship)
    crawl_job : Mapped[CrawlJob] = relationship("CrawlJob", back_populates="crawl_items")
    
    # has_many (One-to-Many relationship)
    crawl_logs : Mapped[List[CrawlLog]] = relationship("CrawlLog", back_populates="crawl_item", cascade="all, delete-orphan")
    
    # == Methods ==============================================================
    
    def log(self, message: str, level: LogLevel | None = None, context: Dict[str, Any] | None = None) -> CrawlLog:
        """Create and save a log entry for this crawl item."""
        from pgmcp.scrapy.models.crawl_log import CrawlLog
        
        if level is None:
            level = LogLevel.INFO  # Default to INFO if no level is provided

        log_entry = CrawlLog.from_crawl_item( crawl_item=self, message=message, level=level, context=context )
        log_entry.save()
        return log_entry


    def info(self, message: str, context: Dict[str, Any] | None = None) -> None: self.log(message, level=LogLevel.INFO, context=context)
    def debug(self, message: str, context: Dict[str, Any] | None = None) -> None: self.log(message, level=LogLevel.DEBUG, context=context)
    def warning(self, message: str, context: Dict[str, Any] | None = None) -> None: self.log(message, level=LogLevel.WARNING, context=context)
    def error(self, message: str, context: Dict[str, Any] | None = None) -> None: self.log(message, level=LogLevel.ERROR, context=context)
    def critical(self, message: str, context: Dict[str, Any] | None = None) -> None: self.log(message, level=LogLevel.CRITICAL, context=context)
