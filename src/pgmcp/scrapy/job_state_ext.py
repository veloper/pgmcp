from datetime import datetime, timezone
from typing import Any, Dict

from scrapy import signals
from scrapy.crawler import Crawler

from pgmcp.scrapy.models.crawl_item import CrawlItem
from pgmcp.scrapy.models.crawl_job import CrawlJob
from pgmcp.scrapy.spider import Spider
from pgmcp.scrapy.spider_closed_reason import SpiderClosedReason


class JobStateExt:
    """Scrapy extension for managing job _state_ via signals."""



    def __init__(self):
        self.spider: Spider | None = None
    
   
    # ---------------------------------------------------------------------------
    # Extension Initialization & Lifecycle
    # ---------------------------------------------------------------------------

    @classmethod
    def from_crawler(cls, crawler: Crawler):
        ext = cls()
        crawler.signals.connect(ext.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(ext.spider_closed, signal=signals.spider_closed)
        return ext
    
    def spider_opened(self, spider: Spider):
        if not self.spider:
            self.spider = spider
        
        with CrawlItem.session_context():
            spider.job.info("Spider opened")
            
            # Transition the crawl job to RUNNING status
            spider.job.crawl_job_model().run()
        
    def spider_closed(self, spider: Spider, reported_reason: str | None = None):
        with CrawlItem.session_context():
            reason = SpiderClosedReason.from_reported_reason(reported_reason)
            loggable_reason = reason.get_loggable_reason()
            crawl_job = spider.job.crawl_job_model()
            
            if reason.is_success():
                spider.job.info(f"Spider closed with: {loggable_reason}")
                crawl_job.succeed()
            elif reason.is_failure():
                spider.job.info(f"Spider closed with: {loggable_reason}")
                crawl_job.fail()

