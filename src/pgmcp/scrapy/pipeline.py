import re

from typing import Awaitable, Callable

from scrapy import signals

from pgmcp.scrapy.item import Item
from pgmcp.scrapy.models.base import Self
from pgmcp.scrapy.models.crawl_item import CrawlItem
from pgmcp.scrapy.spider import Spider
from pgmcp.scrapy.spider_closed_reason import SpiderClosedReason


class Pipeline:
    """Items come out of spiders"""

    # == Custom Pipeline Methods (prefixed for deterministic ordering of map execution)

    def _0001_update_job_item_logs(self, item: Item, spider: Spider) -> Item:
        with CrawlItem.session_context():
            item.info("Starting pipeline processing")
        
        return item


    def _0002_update_job_item_record_with_request_and_response_info(self, item: Item, spider: Spider) -> Item:
        with CrawlItem.session_context():
            item.info("Saving item to database")
            item.sync_to_db()
        return item
    
    
    # == Scrapy Pipeline Methods =================================================

    @classmethod
    def from_crawler(cls, crawler):
        """Hook called by Scrapy to create pipeline instance."""
        return cls()

    
    def open_spider(self, spider: Spider):
        """Hook called when spider is opened - initialization."""
        pass
    
    def close_spider(self, spider: Spider):
        """Hook called when spider is closed - cleanup/finalization."""
        pass
    
    def process_item(self, item : Item, spider: Spider) -> Item:
        """Hook called for every scraped item - main processing method."""
        return self._run_pipeline_over_item(item, spider)

    # == Internal Methods =====================================================

    def get_scheduler_pending_size(self, spider: Spider) -> int:
        """Get the size of the scheduler's pending queue."""
        scheduler = getattr(getattr(getattr(spider, "crawler", None), "engine", None), "slot", None)
        if scheduler and hasattr(scheduler, "scheduler"):
            queue = getattr(scheduler.scheduler, "pending", None)
            if queue is not None:
                return len(queue)
        return 0
    
    def get_scheduler_processed_size(self, spider: Spider) -> int:
        """Get the size of the scheduler's processed queue."""
        scheduler = getattr(getattr(getattr(spider, "crawler", None), "engine", None), "slot", None)
        if scheduler and hasattr(scheduler, "scheduler"):
            queue = getattr(scheduler.scheduler, "processed", None)
            if queue is not None:
                return len(queue)
        return 0

    def _run_pipeline_over_item(self, item: Item, spider: Spider) -> Item:
        """Run the pipeline functions over the item based on their numeric prefix ascending order."""
        pipeline_functions = self._get_ordered_pipeline_callables()
        
        for pipeline_func in pipeline_functions:
            item = pipeline_func(item, spider)
            
        return item
    
    
    def _get_ordered_pipeline_callables(self) -> list[Callable[[Item, Spider], Item]]:
        """Get ordered list of pipeline callable methods based on their numeric prefix."""
        methods = [method for method in dir(self) if re.match(r"^_[0-9]{4}_.+?$", method)]
        methods.sort(key=lambda method: int(method.split("_")[1])) 
        return [getattr(self, method) for method in methods]
