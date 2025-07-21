from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Self, Tuple  # Added Dict, Tuple
from urllib.parse import urlparse

import blinker

from pgvector.sqlalchemy import Vector
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Integer, String, Text  # Added Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pgmcp.models.base import Base
from pgmcp.models.mixin import IsContentableMixin


if TYPE_CHECKING:
    from pgmcp.models.content import Content
    from pgmcp.models.crawl_item import CrawlItem  # Added missing import
    from pgmcp.models.crawl_log import CrawlLog, LogLevel
    from pgmcp.models.question import Question
    from pgmcp.scrapy.item import Item
    from pgmcp.scrapy.job import Job

class CrawlJobStatus(Enum):
    """Enumeration for the status of a scrapy crawl job.
                                                             
       ┌────────────┬─────────────┬──────────────┬─────────────┐
       │            │             │              │             │
    ┌──┴───┐    ┌───┴───┐    ┌────┴────┐    ┌────┴────┐    ┌───▼────┐
    │ IDLE │────▶ READY │────▶ RUNNING ◀────▶ PAUSED  │─┐  │ FAILED │
    └──┬───┘    └───┬───┘    └────┬────┘    └────┬────┘ │  └───┬────┘
       │            │             │              │      │      │
       │            │             │              │      │      │
       │            │             │              │      │      │      ┌───────────┐
       │            └────┐  ┌─────┘              │      └─────────────▶ SUCCEEDED │
       │                 │  │  ┌─────────────────┘             │      └───────────┘
       │                 │  │  │                               │
       │              ┌──▼──▼──▼──┐                            │ 
       └──────────────▶ CANCELLED ◀────────────────────────────┘
                      └───────────┘

    All are past tense.
    """
    
    
    IDLE       = 1      # Job has not been placed into any other state
    READY      = 2      # Job is ready to be run
    RUNNING    = 4      # Job is in the process of running
    PAUSED     = 8      # Job has been manually paused
    FAILED     = 16     # Job has failed for some reason
    CANCELLED  = 32     # Job has been manually cancelled
    SUCCEEDED  = 64     # Job has completed successfully

    MEANINGS = {
        IDLE       : "Job is being configured, has not been placed into any other state",
        READY      : "Job is ready to be run",
        RUNNING    : "Job is in the process of running",
        PAUSED     : "Job has been manually paused",
        FAILED     : "Job has failed for some reason",
        CANCELLED  : "Job has been manually cancelled",
        SUCCEEDED  : "Job has completed successfully",
    }

    TRANSITIONS = {
        IDLE        : [READY,CANCELLED,FAILED],               # Actions: enqueue, cancel, fail
        READY       : [RUNNING, CANCELLED,FAILED],            # Actions: run, cancel, fail
        RUNNING     : [PAUSED, SUCCEEDED, FAILED, CANCELLED], # Actions: pause, succeed, fail, cancel
        PAUSED      : [RUNNING, CANCELLED, FAILED],           # Actions: resume, cancel, fail
        FAILED      : [READY, CANCELLED],                     # Actions: retry, cancel
        SUCCEEDED   : [], 
        CANCELLED   : [],
    }
    
    async def can_transition_to(self, destination: Self) -> bool:
        """Check if the current status can transition to the destination status."""
        return destination in self.__class__.TRANSITIONS.get(self, []) if isinstance(self.__class__.TRANSITIONS, dict) else False
    
    async def get_allowed_transitions(self) -> List[CrawlJobStatus]:
        """Get the list of allowed transitions from the current status."""
        return self.__class__.TRANSITIONS.get(self, []) if isinstance(self.__class__.TRANSITIONS, dict) else []

class CrawlJob(Base):
    """Represents a scrapy job that will be given to a spider to perform."""
    
    # == Model Metadata =======================================================
    __tablename__ = "crawl_jobs"
    
    # == Columns ==============================================================
    start_urls      : Mapped[List[str]]       = mapped_column(JSON, nullable=False, default=[])
    settings        : Mapped[dict[str, Any]]  = mapped_column(JSON, nullable=False, default={})
    allowed_domains : Mapped[List[str]]       = mapped_column(JSON, nullable=False, default=[])
    status          : Mapped[CrawlJobStatus]  = mapped_column( SQLEnum(CrawlJobStatus, name="crawl_job_status"), nullable=False, default=CrawlJobStatus.IDLE )

    # == Relationships ========================================================
    crawl_items           : Mapped[List[CrawlItem]] = relationship("CrawlItem", back_populates="crawl_job", cascade="all, delete-orphan")
    crawl_logs            : Mapped[List[CrawlLog]] = relationship("CrawlLog", back_populates="crawl_job", cascade="all, delete-orphan")

    # == Filters =============================================================
    async def _before_save(self):
        await super()._before_save()
        await self._ensure_allowed_domains_allow_start_urls()
        return self

    async def _ensure_allowed_domains_allow_start_urls(self):
        """Ensure allowed_domains contain the domains of the start_urls."""
        self.allowed_domains = list({urlparse(url).netloc for url in self.start_urls}.union(self.allowed_domains))

    # == Methods ==============================================================
    
    
    # == Transition Methods ==================================================
    
    async def transition_to(self, new_status: CrawlJobStatus) -> None:
        """Transition the job to a new status if allowed."""
        if await self.status.can_transition_to(new_status):
            self.status = new_status
            return await self.save()
        allowed = [s.name for s in await self.status.get_allowed_transitions()]
        raise ValueError(
            f"Cannot transition from {self.status} to {new_status}. Allowed transitions: {', '.join(allowed)}"
        )

    async def enqueue(self) -> None: await self.transition_to(CrawlJobStatus.READY)
    async def cancel(self)  -> None: await self.transition_to(CrawlJobStatus.CANCELLED)
    async def fail(self)    -> None: await self.transition_to(CrawlJobStatus.FAILED)
    async def pause(self)   -> None: await self.transition_to(CrawlJobStatus.PAUSED)
    async def resume(self)  -> None: await self.transition_to(CrawlJobStatus.RUNNING)
    async def retry(self)   -> None: await self.transition_to(CrawlJobStatus.READY)
    async def run(self)     -> None: await self.transition_to(CrawlJobStatus.RUNNING)
    async def succeed(self) -> None: await self.transition_to(CrawlJobStatus.SUCCEEDED)
        
        
    # == Conversion Methods ==================================================
    
    async def create_scrapy_job(self) -> Job:
        """Convert this CrawlJob to a ScrapyJob."""
        if not self.id:
            raise ValueError("CrawlJob must be saved before converting to Scrapy Job.")
        
        return await Job.create(
            start_urls=self.start_urls,
            allowed_domains=self.allowed_domains,
            settings=self.settings
        )

    # == Logging Methods =====================================================

    async def log(self, message: str, level: LogLevel | None = None, context: Dict[str, Any] | None = None) -> CrawlLog:
        """Create and save a log entry for this crawl job."""
        from pgmcp.models.crawl_logs import CrawlLog, LogLevel
        
        if level is None:
            level = LogLevel.INFO
            
        log_entry = CrawlLog.from_crawl_job(crawl_job=self, message=message, level=level, context=context)
        await log_entry.save()
        return log_entry

    def model_dump(self, exclude: List[str] | None = None, exclude_none: bool = False) -> dict:
        """Serialize the model to a dict, optionally excluding fields and omitting None values."""
        exclude_set = set(exclude or [])
        result = {}
        for column in self.__table__.columns:
            name = column.name
            
            if name in exclude_set: continue
            value = getattr(self, name)
            
            if exclude_none and value is None: continue
            
            result[name] = value
            
            if name == "status":
                label = self.status.name if isinstance(self.status, CrawlJobStatus) else self.status
                result["status_label"] = label
        
        # Add any extra fields from _row_data (like aggregates)
        if hasattr(self, '_row_data') and self._row_data:
            # Get model column names to avoid duplicates
            model_columns = {col.name for col in self.__table__.columns}
            for key, value in self._row_data.items():
                if key not in model_columns and key not in exclude_set:
                    if not exclude_none or value is not None:
                        result[key] = value
        
        return result

    def __getitem__(self, key: str) -> Any:
        """Allow dict-style access to row data for aggregates and other extra fields."""
        if hasattr(self, '_row_data') and key in self._row_data:
            return self._row_data[key]
        # Fall back to normal attribute access for model fields
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(f"'{key}' not found in model or row data")

    def __contains__(self, key: str) -> bool:
        """Check if key exists in model fields or row data."""
        if hasattr(self, '_row_data') and key in self._row_data:
            return True
        return hasattr(self, key)
