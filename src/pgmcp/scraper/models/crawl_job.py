from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Self  # Added Dict, Tuple
from urllib.parse import urlparse

from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSON, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pgmcp.scraper.models.base import Base

from .log_level import LogLevel


if TYPE_CHECKING:
    from pgmcp.scraper.job import Job
    from pgmcp.scraper.models.crawl_item import CrawlItem
    from pgmcp.scraper.models.crawl_log import CrawlLog


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
        
    def all_transitions(self) -> Dict[CrawlJobStatus, List[CrawlJobStatus]]:
        return {
            self.IDLE        : [self.READY,self.CANCELLED,self.FAILED],                     # Actions: enqueue, cancel, fail
            self.READY       : [self.RUNNING, self.CANCELLED,self.FAILED],                  # Actions: run, cancel, fail
            self.RUNNING     : [self.PAUSED, self.SUCCEEDED, self.FAILED, self.CANCELLED],  # Actions: pause, succeed, fail, cancel
            self.PAUSED      : [self.RUNNING, self.CANCELLED, self.FAILED],                 # Actions: resume, cancel, fail
            self.FAILED      : [self.READY, self.CANCELLED],                                # Actions: retry, cancel
            self.SUCCEEDED   : [],
            self.CANCELLED   : [],
        }
        
    def transitions(self) -> List[CrawlJobStatus]:
        """Return the list of allowed transitions from the current status."""
        transitions = self.all_transitions()
        if not isinstance(transitions, dict):
            raise TypeError(f"Transitions must be a dict, got {type(transitions).__name__}.")
        return transitions.get(self, [])
    
    def can_transition_to(self, destination: Self) -> bool:
        return destination in self.transitions()

    
class CrawlJob(Base):
    """Represents a scrapy job that will be given to a spider to perform."""
    __tablename__ = "crawl_jobs"
    
    # == Columns ==============================================================
    start_urls      : Mapped[List[str]]       = mapped_column(JSONB, nullable=False, default=[])
    settings        : Mapped[dict[str, Any]]  = mapped_column(JSONB, nullable=False, default={})
    allowed_domains : Mapped[List[str]]       = mapped_column(JSONB, nullable=False, default=[])
    status          : Mapped[CrawlJobStatus]  = mapped_column( SQLEnum(CrawlJobStatus, name="crawl_job_status"), nullable=False, default=CrawlJobStatus.IDLE )
    stats            : Mapped[dict[str, Any]]  = mapped_column(JSONB, nullable=True, default={})

    # == Relationships ========================================================
    crawl_items           : Mapped[List[CrawlItem]] = relationship("CrawlItem", back_populates="crawl_job", cascade="all, delete-orphan")
    crawl_logs            : Mapped[List[CrawlLog]] = relationship("CrawlLog", back_populates="crawl_job", cascade="all, delete-orphan")

    # == Filters =============================================================
    def _before_save(self):
        super()._before_save()
        self._ensure_allowed_domains_allow_start_urls()
        return self

    def _ensure_allowed_domains_allow_start_urls(self):
        """Ensure allowed_domains contain the domains of the start_urls."""
        self.allowed_domains = list({urlparse(url).netloc for url in self.start_urls}.union(self.allowed_domains))

    # == Methods ==============================================================
    
    
    # == Transition Methods ==================================================
    
    def transition_to(self, new_status: CrawlJobStatus) -> None:
        """Transition the job to a new status if allowed."""
        can_transition = self.status.can_transition_to(new_status)
        if can_transition:
            self.status = new_status
            return self.save()
        allowed = [s.name for s in self.status.transitions()]
        raise ValueError(
            f"Cannot transition from {self.status} to {new_status}. Allowed transitions: {', '.join(allowed)}"
        )

    def enqueue(self) -> None: self.transition_to(CrawlJobStatus.READY)
    def cancel(self)  -> None: self.transition_to(CrawlJobStatus.CANCELLED)
    def fail(self)    -> None: self.transition_to(CrawlJobStatus.FAILED)
    def pause(self)   -> None: self.transition_to(CrawlJobStatus.PAUSED)
    def resume(self)  -> None: self.transition_to(CrawlJobStatus.RUNNING)
    def retry(self)   -> None: self.transition_to(CrawlJobStatus.READY)
    def run(self)     -> None: self.transition_to(CrawlJobStatus.RUNNING)
    def succeed(self) -> None: self.transition_to(CrawlJobStatus.SUCCEEDED)
        

        
    # == Conversion Methods ==================================================
    
    def to_scrapy_job(self) -> Job:
        """Convert this CrawlJob to a ScrapyJob."""
        if not self.id:
            raise ValueError("CrawlJob must be saved before converting to Scrapy Job.")
        from pgmcp.scraper.job import Job  # circular import
        return Job.from_crawl_job(
            id=self.id,
            start_urls=self.start_urls,
            allowed_domains=self.allowed_domains,
            settings=self.settings
        )

    # == Logging Methods =====================================================

    def log(self, message: str, level: LogLevel | None = None, context: Dict[str, Any] | None = None) -> CrawlLog:
        """Create and save a log entry for this crawl job."""
        from pgmcp.scraper.models.crawl_log import CrawlLog
        
        if level is None:
            level = LogLevel.INFO

        log_entry = CrawlLog.from_crawl_job(crawl_job=self, message=message, level=level, context=context)
        log_entry.save()
        return log_entry

    def model_dump(self, exclude: List[str] | None = None) -> dict:
        """Serialize the model to a dict, optionally excluding fields and omitting None values."""
        
        data = self.to_dict()
        
        
        for field in (exclude or []):
            if field in data:
                del data[field]

        if "status" in data:
            label = self.status.name if isinstance(self.status, CrawlJobStatus) else self.status
            data["status_label"] = label

        return data
