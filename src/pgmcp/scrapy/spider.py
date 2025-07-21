from collections.abc import AsyncGenerator, Generator
from typing import Any, Dict, Optional

import scrapy

from scrapy.crawler import CrawlerRunner
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule

from pgmcp.scrapy.item import Item
from pgmcp.scrapy.job import Job


class Spider(CrawlSpider):
    name = "pgmcp_spider"
    
    custom_settings = {
        'DEPTH_LIMIT': 3,           # Limit crawl depth to prevent infinite crawling
        'ROBOTSTXT_OBEY': False,    # Disable robots.txt for testing
        'DOWNLOAD_DELAY': 0.5,      # Be respectful with delays
        'ITEM_PIPELINES': {
            'pgmcp.scrapy.spider.Pipeline': 300
        }
    }
    
    rules = (
        Rule(LinkExtractor(), callback="parse_item", follow=True),
    )

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        # Optionally access crawler.settings, signals, stats, etc.
        return spider

    def __init__(self, job: Job, *args, **kwargs):
        self.job = job
        self.start_urls = job.start_urls
        self.allowed_domains = job.allowed_domains


        self.__class__.update_settings(job.to_base_settings())

        super().__init__(*args, **kwargs)


    @classmethod
    def update_settings(cls, settings) -> None:
        super().update_settings(settings)

    async def parse_item(self, response) -> AsyncGenerator[Item|scrapy.Request, None]:
        """This method is called for each response, and it the job of it to create and yield items, and extract links to follow."""
        
        self.logger.debug(f"Parsing response from {response.url}")
        
        # ITEMS - Create and log new item creation
        
        item = Item(
            job_id=self.job.id,
            body=response.text,
            url=response.url,
            status=response.status,
            request_headers=dict(response.request.headers),
            response_headers=dict(response.headers),
            depth=response.meta.get('depth', 0),
            referer=response.meta.get('referer', None)
        )
        
        self.logger.info(f"Created new item for URL: {response.url} (depth: {response.meta.get('depth', 0)})")
        
        yield item
        
        # FOLLOW LINKS - Adding Metadata for depth and referer
        
        discovered_links = response.xpath("//a/@href").getall()
        
        # Log link discovery
        if discovered_links:
            await self.job.info(f"Discovered {len(discovered_links)} links from {response.url} at depth {response.meta.get('depth', 0)}")

        for href in discovered_links:
            full_url = response.urljoin(href)
            request = scrapy.Request(full_url, self.parse_item)
            request.meta['referer'] = response.url
            request.meta['depth'] = response.meta.get('depth', 0) + 1
            
            # Log each new request being queued
            self.logger.debug(f"Queuing new request: {full_url} (depth: {request.meta['depth']})")
            
            yield request

        
        

    async def parse_start_url(self, response):
        """This is the very start of the crawl, where we process the initial URL.
        and yield items and requests from it.
        """
        self.logger.info(f"Parsing start URL: {response.url}")
        async for item_or_request in self.parse_item(response):
            yield item_or_request
