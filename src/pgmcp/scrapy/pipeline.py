import re

from typing import Awaitable, Callable

from pgmcp.models.crawl_item import CrawlItem
from pgmcp.scrapy.item import Item
from pgmcp.scrapy.spider import Spider


class Pipeline:
    """Items come out of spiders"""

    # == Custom Pipeline Methods (prefixed for deterministic ordering of map execution)

    async def _0001_update_job_item_logs(self, item: Item, spider: Spider) -> Item:
        await item.info("Starting pipeline processing")
        return item


    async def _0002_update_job_item_record_with_request_and_response_info(self, item: Item, spider: Spider) -> Item:
        await item.info("Updating with request and response info")
        await item.sync_to_db()
        return item
    
    
    # == Scrapy Pipeline Methods =================================================

    @classmethod
    def from_crawler(cls, crawler):
        """Hook called by Scrapy to create pipeline instance."""
        return cls()

    async def open_spider(self, spider: Spider):
        """Hook called when spider is opened - setup/initialization."""
        await spider.job.info("Spider opened")

    async def process_item(self, item : Item, spider: Spider) -> Item:
        """Hook called for every scraped item - main processing method."""
        return await self._run_pipeline_over_item(item, spider)

    async def close_spider(self, spider: Spider):
        """Hook called when spider is closed - cleanup/finalization."""
        await spider.job.info("Spider closed")  
        

    
    
    # == Internal Methods =====================================================

    async def _run_pipeline_over_item(self, item: Item, spider: Spider) -> Item:
        """Run the pipeline functions over the item based on their numeric prefix ascending order."""
        pipeline_functions = self._get_ordered_pipeline_callables()
        
        for pipeline_func in pipeline_functions:
            item = await pipeline_func(item, spider)
            
        return item
    
    
    def _get_ordered_pipeline_callables(self) -> list[Callable[[Item, Spider], Awaitable[Item]]]:
        """Get ordered list of pipeline callable methods based on their numeric prefix."""
        methods = [method for method in dir(self) if re.match(r"^_[0-9]{4}_.+?$", method)]
        methods.sort(key=lambda method: int(method.split("_")[1])) 
        return [getattr(self, method) for method in methods]
