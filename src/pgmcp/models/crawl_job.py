from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Self, Tuple  # Added Dict, Tuple
from urllib.parse import urlparse

from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSON, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pgmcp.models.base import Base
from pgmcp.models.crawl_log import CrawlLog

from .log_level import LogLevel


if TYPE_CHECKING:
    from pgmcp.models.crawl_item import CrawlItem
    from pgmcp.scraper.job import Job


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
        
    async def all_transitions(self) -> Dict[CrawlJobStatus, List[CrawlJobStatus]]:
        return {
            self.IDLE        : [self.READY,self.CANCELLED,self.FAILED],                     # Actions: enqueue, cancel, fail
            self.READY       : [self.RUNNING, self.CANCELLED,self.FAILED],                  # Actions: run, cancel, fail
            self.RUNNING     : [self.PAUSED, self.SUCCEEDED, self.FAILED, self.CANCELLED],  # Actions: pause, succeed, fail, cancel
            self.PAUSED      : [self.RUNNING, self.CANCELLED, self.FAILED],                 # Actions: resume, cancel, fail
            self.FAILED      : [self.READY, self.CANCELLED],                                # Actions: retry, cancel
            self.SUCCEEDED   : [],
            self.CANCELLED   : [],
        }
        
    async def transitions(self) -> List[CrawlJobStatus]:
        """Return the list of allowed transitions from the current status."""
        transitions = await self.all_transitions()
        if not isinstance(transitions, dict):
            raise TypeError(f"Transitions must be a dict, got {type(transitions).__name__}.")
        return transitions.get(self, [])
    
    async def can_transition_to(self, destination: Self) -> bool:
        return destination in await self.transitions()

    
class CrawlJob(Base):
    """Represents a scrapy job that will be given to a spider to perform."""
    
    # == Model Metadata =======================================================
    __tablename__ = "crawl_jobs"
    
    # == Columns ==============================================================
    start_urls      : Mapped[List[str]]       = mapped_column(JSONB, nullable=False, default=[])
    settings        : Mapped[dict[str, Any]]  = mapped_column(JSONB, nullable=False, default={})
    allowed_domains : Mapped[List[str]]       = mapped_column(JSONB, nullable=False, default=[])
    status          : Mapped[CrawlJobStatus]  = mapped_column( SQLEnum(CrawlJobStatus, name="crawl_job_status"), nullable=False, default=CrawlJobStatus.IDLE )
    stats           : Mapped[dict[str, Any]]  = mapped_column(JSONB, nullable=True, default={})

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
    
    # get start urls, group by hostname, pick most common, or first if no common, return hostname + path.replace("/", " ")
    def get_name_from_most_common_domain(self) -> str:
        """Get the name of the job based on the most common domain in start_urls.
        
        Example:
            example.com/some/path -> example.com: some path
            example.com -> example.com
        """
        if not self.start_urls:
            return "Unnamed Job"
        
        domain_to_urls: Dict[str, List[str]] = {}
        for url in self.start_urls:
            domain = urlparse(url).netloc
            path = urlparse(url).path.replace("/", " ")
            domain_to_urls.setdefault(domain, []).append(path)

        # Pick the most common domain or the first one if there's a tie
        most_common_domain = max(domain_to_urls, key=lambda k: (len(domain_to_urls[k]), k))
        paths = domain_to_urls[most_common_domain]
        return f"{most_common_domain}: {paths[0]}" if paths else most_common_domain

    @property
    def stats_message_line(self) -> str:
        """Get a message line summarizing the stats"""
        human_minutes = int(self.stats_elapsed_seconds // 60)
        human_seconds = int(self.stats_elapsed_seconds % 60)
        
        line = [
            f"⚡️ {self.stats_items_per_minute:.2f}/m",
            f"🟢 {self.stats_response_status_count_2xx + self.stats_response_status_count_3xx}",
            f"🔴 {self.stats_response_status_count_4xx + self.stats_response_status_count_5xx}",
            f"🗑 {self.stats_filtered_count}",
            f"⏳ {human_minutes:02}:{human_seconds:02}",
        ]
        
        return " ".join(line)
        
    def sum_responses_starting_with(self, prefix: str) -> int:
        """Sum the counts of responses starting with a given prefix."""
        if not isinstance(self.stats, dict):
            return 0
        
        return sum(
            int(value) for key, value in self.stats.get("stats", {}).items()
            if key.startswith(prefix) and isinstance(value, (int, float))
        )
    
    # downloader/response_status_count/200
    @property
    def stats_response_status_count_2xx(self) -> int: return self.sum_responses_starting_with("downloader/response_status_count/2")
    
    @property
    def stats_response_status_count_3xx(self) -> int: return self.sum_responses_starting_with("downloader/response_status_count/3")
    
    @property
    def stats_response_status_count_4xx(self) -> int: return self.sum_responses_starting_with("downloader/response_status_count/4")
    
    @property
    def stats_response_status_count_5xx(self) -> int: return self.sum_responses_starting_with("downloader/response_status_count/5")

    @property
    def stats_filtered_count(self) -> int:
        """Get the number of requests filtered by the dupefilter."""
        if (stats := self.stats.get("stats")) and isinstance(stats, dict):
            if stats.get("dupefilter/filtered") is not None:
                return int(stats["dupefilter/filtered"])
        return 0
    
    @property
    def stats_scheduler_dequeued_count(self) -> int:
        """Get the number of items dequeued by the scheduler."""
        if (stats := self.stats.get("stats")) and isinstance(stats, dict):
            if stats.get("scheduler/dequeued") is not None:
                return int(stats["scheduler/dequeued"])
        return 0
    
    @property
    def stats_scheduler_enqueued_count(self) -> int:
        """Get the number of items enqueued by the scheduler."""
        if (stats := self.stats.get("stats")) and isinstance(stats, dict):
            if stats.get("scheduler/enqueued") is not None:
                return int(stats["scheduler/enqueued"])
        return 0
    
    
    @property
    def stats_progress_and_total_and_ratio(self) -> Tuple[int, int, float]:
        """Get the progress and total number of requests."""
        total = self.stats_scheduler_dequeued_count + self.stats_scheduler_enqueued_count
        progress = self.stats_scheduler_dequeued_count
        if total > 0:
            return progress, total, progress / total
        return progress, total, 0.0 
    
     
    @property
    def stats_items_per_minute(self) -> float:
        """Calculate the number of items processed per minute."""
        return self.stats_items_per_second * 60.0
     
    @property
    def stats_items_per_second(self) -> float:
        """Calculate the number of items processed per second."""
        elapsed_seconds = self.stats_elapsed_seconds
        dequeued_count = self.stats_scheduler_dequeued_count
        return dequeued_count / (elapsed_seconds if elapsed_seconds > 0 else 0.0)
        
    @property
    def stats_elapsed_seconds(self) -> float:
        if (time_stats := self.stats.get("time")) and isinstance(time_stats, dict):
            if time_stats.get("elapsed") is not None:
                return float(time_stats["elapsed"])
        return 0

    # == Testing Methods ==================================================
    @property
    def is_idle(self) -> bool: return self.status == CrawlJobStatus.IDLE
    @property
    def is_ready(self) -> bool: return self.status == CrawlJobStatus.READY
    @property
    def is_running(self) -> bool: return self.status == CrawlJobStatus.RUNNING
    @property      
    def is_paused(self) -> bool: return self.status == CrawlJobStatus.PAUSED
    @property
    def is_failed(self) -> bool: return self.status == CrawlJobStatus.FAILED
    @property
    def is_cancelled(self) -> bool: return self.status == CrawlJobStatus.CANCELLED
    @property
    def is_succeeded(self) -> bool: return self.status == CrawlJobStatus.SUCCEEDED
    
    @property
    def is_done(self) -> bool:
        """Check if the job is in a terminal state (succeeded, failed, or cancelled)."""
        return self.is_succeeded or self.is_failed or self.is_cancelled
        
    # == Transition Methods ==================================================
    
    async def transition_to(self, new_status: CrawlJobStatus) -> None:
        """Transition the job to a new status if allowed."""
        can_transition = await self.status.can_transition_to(new_status)
        if can_transition:
            self.status = new_status
            return await self.save()
        allowed = [s.name for s in await self.status.transitions()]
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

    async def log(self, message: str, level: LogLevel | None = None, context: Dict[str, Any] | None = None) -> CrawlLog:
        """Create and save a log entry for this crawl job."""
        from pgmcp.models.crawl_log import CrawlLog
        
        if level is None:
            level = LogLevel.INFO

        log_entry = CrawlLog.from_crawl_job(crawl_job=self, message=message, level=level, context=context)
        await log_entry.save()
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
