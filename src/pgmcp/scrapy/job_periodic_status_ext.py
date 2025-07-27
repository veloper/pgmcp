from datetime import datetime, timezone
from typing import Any, Dict

from scrapy import signals
from scrapy.crawler import Crawler
from twisted.internet.task import LoopingCall

from pgmcp.scrapy.models.crawl_job import CrawlJob
from pgmcp.scrapy.models.log_level import LogLevel
from pgmcp.scrapy.spider import Spider


class JobPeriodicStatusExt:
    """Scrapy extension for periodic job status and stats updates."""



    def __init__(self):
        self.spider: Spider | None = None
        self.crawl_job_id: int | None = None
        self.stats: Any | None = None
        self.time_prev: datetime | None = None
        self.delta_prev: Dict[str, float] = {}
        self.stats_prev: Dict[str, Any] = {}
        self.interval: int = 2000  # Default interval in milliseconds for periodic updates

    # ---------------------------------------------------------------------------
    # LoopingCall every X seconds to generate periodic data and then save it to the 
    # CrawlJob that we get from the spider.
    # ---------------------------------------------------------------------------
   
    def on_tick(self, message="Periodic Stats") -> None:
        """Called periodically to collect stats and update the job."""
        if not self.crawl_job_id:
            return
        
        with CrawlJob.session_context():
            if crawl_job := CrawlJob.find(self.crawl_job_id):
                data = self.get_periodic_data()
                crawl_job.stats = data
                crawl_job.save()

                crawl_job.log(message, LogLevel.INFO, data)
            else:
                raise ValueError(f"CrawlJob with ID {self.crawl_job_id} not found.")

   
    # ---------------------------------------------------------------------------
    # Extension Initialization & Lifecycle
    # ---------------------------------------------------------------------------

    @classmethod
    def from_crawler(cls, crawler: Crawler):
        ext = cls()
        crawler.signals.connect(ext.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(ext.spider_closed, signal=signals.spider_closed)
        ext.stats = getattr(crawler, "stats", None)
        return ext
    
    def spider_opened(self, spider: Spider):
        self.spider = spider
        self.crawl_job_id = spider.job.id
        self.time_prev = datetime.now(tz=timezone.utc)
        self.delta_prev = {}
        self.stats_prev = {}
        
        self.on_tick("Initial Stats")
        
        # Periodic updates using Twisted's LoopingCall
        self.looping_call = LoopingCall(self.on_tick)
        self.looping_call.start(self.interval / 1000.0)
        

    def spider_closed(self, spider, reason):
        self.on_tick("Final Stats")

    # ---------------------------------------------------------------------------
    # Stats Collection Methods
    # ---------------------------------------------------------------------------
    def collect_stats(self) -> Dict[str, Any]:
        # Collect current stats, converting datetime objects to ISO strings for JSON serialization
        if self.stats and hasattr(self.stats, "_stats") and isinstance(self.stats._stats, dict):
            stats = {}
            for k, v in self.stats._stats.items():
                if isinstance(v, datetime):
                    stats[k] = v.isoformat()
                else:
                    stats[k] = v
            return stats
        return {}

    def collect_delta(self) -> Dict[str, float]:
        # Collect deltas for numeric stats
        if self.stats and hasattr(self.stats, "_stats") and isinstance(self.stats._stats, dict):
            num_stats = {k: float(v) for k, v in self.stats._stats.items() if isinstance(v, (int, float))}
            delta = {k: num_stats[k] - self.delta_prev.get(k, 0.0) for k in num_stats}
            self.delta_prev = num_stats
            return delta
        return {}

# ---------------------------------------------------------------------------
# Timing & Aggregation Methods
# ---------------------------------------------------------------------------
    def collect_timing(self) -> Dict[str, Any]:
        now = datetime.now(tz=timezone.utc)
        start_time = now
        if self.stats and hasattr(self.stats, "_stats") and isinstance(self.stats._stats, dict):
            start_time = self.stats._stats.get("start_time", now)
        timing = {
            "log_interval": None,  # You can set this if you want periodic
            "start_time": start_time.isoformat() if isinstance(start_time, datetime) else start_time,
            "utcnow": now.isoformat(),
            "log_interval_real": (now - self.time_prev).total_seconds() if self.time_prev else None,
            "elapsed": (now - start_time).total_seconds() if start_time else None,
        }
        self.time_prev = now
        return timing

    def get_periodic_data(self) -> Dict[str, Any]:
        """Aggregate stats, delta, and timing for encoding/saving."""
        data = {
            "stats": self.collect_stats(),
            "delta": self.collect_delta(),
            "time": self.collect_timing(),
        }
        return data


