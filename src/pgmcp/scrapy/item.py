from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Generator, List, Optional

import scrapy


if TYPE_CHECKING:
    from pgmcp.models.crawl_item import CrawlItem
    from pgmcp.models.crawl_job import CrawlJob

class Item(scrapy.Item):
    crawl_item_id    = scrapy.Field(description="ID representing this item in the database")
    crawl_job_id     = scrapy.Field(description="ID of the job this item belongs to")
    body             = scrapy.Field(description="HTML content of the crawled page")
    url              = scrapy.Field(description="The URL that was crawled")
    status           = scrapy.Field(description="HTTP status code of the response")
    request_headers  = scrapy.Field(description="Headers from the request that fetched this page")
    response_headers = scrapy.Field(description="Headers from the response")
    depth            = scrapy.Field(description="Depth of the URL in the crawl tree, starting from 0 for start URLs")
    referer          = scrapy.Field(description="The URL of the page that linked to this page")

    async def sync_to_db(self) -> None:
        """Sync the item data to the database."""
        crawl_item = await self.crawl_item()
        if not crawl_item: raise ValueError("CrawlItem ID is missing an crawl_item_id")
        
        crawl_item.body             = self["body"]
        crawl_item.url              = self["url"]
        crawl_item.status           = self["status"]
        crawl_item.request_headers  = self.get("request_headers", {})
        crawl_item.response_headers = self.get("response_headers", {})
        crawl_item.depth            = self.get("depth", 0)
        crawl_item.referer          = self.get("referer", None)
        
        await crawl_item.save()

    async def crawl_item(self) -> Optional[CrawlItem]:
        if not self.get('crawl_item_id'): return None
        from pgmcp.models.crawl_item import CrawlItem
        return await CrawlItem.find(int(self['crawl_item_id']))

    async def crawl_job(self) -> Optional[CrawlJob]:
        if not self.get('crawl_job_id'): return None
        from pgmcp.models.crawl_job import CrawlJob
        return await CrawlJob.find(int(self['crawl_job_id']))
    
    async def log(self, message: str, level: str = "INFO", context: Dict[str, Any] | None = None) -> None:
        """Log a message related to this item and job it's associated with."""
        from pgmcp.models.crawl_log import LogLevel

        # Convert string level to enum
        log_level = getattr(LogLevel, level.upper(), LogLevel.INFO)
        
        if crawl_item := await self.crawl_item():
            await crawl_item.log(message, log_level, context)
        elif crawl_job := await self.crawl_job():
            await crawl_job.log(message, log_level, context)

    async def info(self, message: str, context: Dict[str, Any] | None = None) -> None:
        await self.log(message, level="INFO", context=context)
    
    async def debug(self, message: str, context: Dict[str, Any] | None = None) -> None:
        await self.log(message, level="DEBUG", context=context)
        
    async def warning(self, message: str, context: Dict[str, Any] | None = None) -> None:
        await self.log(message, level="WARNING", context=context)
        
    async def error(self, message: str, context: Dict[str, Any] | None = None) -> None:
        await self.log(message, level="ERROR", context=context)
