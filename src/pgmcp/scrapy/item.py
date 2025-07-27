from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Generator, List, Optional

import scrapy

from sqlalchemy import select

from pgmcp.scrapy.models.log_level import LogLevel


if TYPE_CHECKING:
    from pgmcp.scrapy.models.crawl_item import CrawlItem
    from pgmcp.scrapy.models.crawl_job import CrawlJob

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

    def sync_to_db(self) -> None:
        """Sync the item data to the database."""
        crawl_item = self.crawl_item()
        if not crawl_item: 
            from pgmcp.scrapy.models.crawl_item import CrawlItem
            crawl_item = CrawlItem()

        def decode_headers(headers):
            if not headers:
                return {}
            # Scrapy headers are {bytes: [bytes]}
            def sanitize(val):
                sval = val.decode() if isinstance(val, bytes) else str(val)
                if '\x00' in sval:
                    raise ValueError("Header value contains NUL (0x00) character, which is not allowed in DB fields.")
                return sval
            return {
                sanitize(k): [sanitize(v) for v in vs]
                for k, vs in headers.items()
            }

        def sanitize_field(val, field_name):
            if val is None:
                return val
            sval = val if isinstance(val, str) else str(val)
            if '\x00' in sval:
                raise ValueError(f"Field '{field_name}' contains NUL (0x00) character, which is not allowed in DB fields.")
            return sval

        # Validate crawl_job_id presence and non-None
        if "crawl_job_id" not in self or self["crawl_job_id"] is None:
            raise ValueError("crawl_job_id is required and cannot be None")

        crawl_item.crawl_job_id     = self["crawl_job_id"]
        crawl_item.body             = sanitize_field(self["body"], "body")
        crawl_item.url              = sanitize_field(self["url"], "url")
        crawl_item.status           = self["status"]
        crawl_item.request_headers  = decode_headers(self.get("request_headers", {}))
        crawl_item.response_headers = decode_headers(self.get("response_headers", {}))
        crawl_item.depth            = self.get("depth", 0)
        crawl_item.referer          = sanitize_field(self.get("referer", None), "referer")

        crawl_item.save()
        
        self["crawl_item_id"] = crawl_item.id

    def crawl_item(self) -> Optional[CrawlItem]:
        if not self.get('crawl_item_id'): return None
        from pgmcp.scrapy.models.crawl_item import CrawlItem
        
        return CrawlItem.find(int(self['crawl_item_id']))

    def crawl_job(self) -> Optional[CrawlJob]:
        if not self.get('crawl_job_id'): return None
        from pgmcp.scrapy.models.crawl_job import CrawlJob
        return CrawlJob.find(int(self['crawl_job_id']))

    def log(self, message: str, level: LogLevel = LogLevel.INFO, context: Dict[str, Any] | None = None) -> None:
        """Log a message related to this item and job it's associated with."""
        if crawl_item := self.crawl_item():
            crawl_item.log(message, level, context)
        elif crawl_job := self.crawl_job():
            crawl_job.log(message, level, context)

    def info(self, message: str, context: Dict[str, Any] | None = None) -> None: self.log(message, level=LogLevel.INFO, context=context)
    def debug(self, message: str, context: Dict[str, Any] | None = None) -> None: self.log(message, level=LogLevel.DEBUG, context=context)
    def warning(self, message: str, context: Dict[str, Any] | None = None) -> None: self.log(message, level=LogLevel.WARNING, context=context)
    def error(self, message: str, context: Dict[str, Any] | None = None) -> None: self.log(message, level=LogLevel.ERROR, context=context)
    def critical(self, message: str, context: Dict[str, Any] | None = None) -> None: self.log(message, level=LogLevel.CRITICAL, context=context)
