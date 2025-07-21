from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Integer, String, Text  # Added Text and ForeignKey
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pgmcp.models.base import Base
from pgmcp.models.crawl_log import CrawlLog
from pgmcp.models.mixin import IsEmbeddableMixin


if TYPE_CHECKING:
    from pgmcp.models.content import Content
    from pgmcp.models.crawl_job import CrawlJob
    from pgmcp.models.crawl_log import LogLevel
    from pgmcp.models.question import Question
    from pgmcp.scrapy.item import Item

class CrawlItem(Base):
    """Represents a web crawling job."""
    # == Model Metadata =======================================================
    __tablename__ = "crawl_items"

    # == Columns ============================================================== 
    
    crawl_job_id     : Mapped[int]            = mapped_column(ForeignKey("crawl_jobs.id"), nullable=False)
    body             : Mapped[str]            = mapped_column(Text,         nullable=False)
    url              : Mapped[str]            = mapped_column(String(2048), nullable=False)
    status           : Mapped[int]            = mapped_column(Integer,      nullable=False)  # http status code
    request_headers  : Mapped[Dict[str, str]] = mapped_column(JSON,         nullable=False)
    response_headers : Mapped[Dict[str, str]] = mapped_column(JSON,         nullable=False)
    depth            : Mapped[int]            = mapped_column(Integer,      nullable=False)
    referer          : Mapped[str]            = mapped_column(String(2048), nullable=True)
    
    # == Relationships ========================================================
    
    # belongs_to CrawlJob (Many-to-One relationship)
    crawl_job : Mapped[CrawlJob] = relationship("CrawlJob", back_populates="crawl_items")
    
    # has_many (One-to-Many relationship)
    crawl_logs : Mapped[List[CrawlLog]] = relationship("CrawlLog", back_populates="crawl_item", cascade="all, delete-orphan")
    
    # == Methods ==============================================================
    
    async def log(self, message: str, level: LogLevel | None = None, context: Dict[str, Any] | None = None) -> CrawlLog:
        """Create and save a log entry for this crawl item."""
        from pgmcp.models.crawl_log import CrawlLog, LogLevel
        
        if level is None:
            level = LogLevel.INFO
            
        log_entry = CrawlLog.from_crawl_item(
            crawl_item=self,
            message=message,
            level=level,
            context=context
        )
        await log_entry.save()
        return log_entry


    async def info(self, message: str, context: Dict[str, Any] | None = None) -> None: await self.log(message, level=LogLevel.INFO, context=context)
    async def debug(self, message: str, context: Dict[str, Any] | None = None) -> None: await self.log(message, level=LogLevel.DEBUG, context=context)
    async def warning(self, message: str, context: Dict[str, Any] | None = None) -> None: await self.log(message, level=LogLevel.WARNING, context=context)
    async def error(self, message: str, context: Dict[str, Any] | None = None) -> None: await self.log(message, level=LogLevel.ERROR, context=context)
