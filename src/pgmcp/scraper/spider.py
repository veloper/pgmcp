from __future__ import annotations

import re

from typing import Any, Dict, Generator, Optional

import scrapy

from scrapy.crawler import CrawlerRunner
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule

from pgmcp.scraper.item import Item
from pgmcp.scraper.job import Job


class Spider(CrawlSpider):
    name = "pgmcp_spider"
    
    custom_settings = {}
    
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
        
        # Populate the start_urls        
        if not job.start_urls:
            raise ValueError("Job must have at least one start URL.")
        self.start_urls = job.start_urls
        
        # Populate the allowed_domains
        self.allowed_domains = job.allowed_domains
        

        # Populate AND UPDATE the settings (requires special update_settings method call)
        self.__class__.update_settings(job.to_base_settings())

        # Populate Boilerplate Patterns
        self.boilerplate_patterns = [
            r"terms.+?service", 
            r"sign.?up", 
            r"sign.?in", 
            r"(un)?subscribe",
            r"log.?in", 
            r"log.?out"
        ]
        self.boilerplate_substrings = [
            "about", "advertising", "blog", "careers", "contact", "cookie",
            "disclaimer", "help", "imprint", "impress", "jobs", "legal",
            "media", "news", "policy", "press", "privacy", "register",
            "license", "mailto:", "javascript:", "#"
        ]

        super().__init__(*args, **kwargs)


    @classmethod
    def update_settings(cls, settings) -> None:
        super().update_settings(settings)

    def is_url_boilerplate(self, url: str) -> bool:
        """Check if a URL matches any boilerplate patterns."""
        for pattern in self.boilerplate_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        for substring in self.boilerplate_substrings:
            if substring in url:
                return True
        return False


    def extract_followable_links(self, response) -> list[str]:
        """Extracts links from the response that are followable by the spider."""
        
        # Use XPath to extract all anchor tags' href attributes
        discovered_links = response.xpath("//a/@href").getall()
        
        followable_links = [
            link for link in discovered_links if link and not self.is_url_boilerplate(link)
        ]
        
        return followable_links
        
    
    def parse_item(self, response) -> Generator[Item|scrapy.Request, None]:
        """This method is called for each response, and it the job of it to create and yield items, and extract links to follow."""
        
        self.logger.debug(f"Parsing response from {response.url}")
        
        # Utility: Remove NUL bytes from response text
        def strip_nul_bytes(text: str) -> str:
            return text.replace('\x00', '')
        
        # ITEMS - Create and log new item creation
        
        item = Item(
            crawl_job_id=self.job.id,  
            body=strip_nul_bytes(response.text),
            url=response.url,
            status=response.status,
            request_headers=dict(response.request.headers),
            response_headers=dict(response.headers),
            depth=response.meta.get('depth', 0),
            referer=response.meta.get('referer', None)
        )
        
        self.logger.info(f"Created new item for URL: {response.url} (depth: {response.meta.get('depth', 0)})")
        
        yield item
        
        followable_links = self.extract_followable_links(response)
        
        # Log link discovery
        if followable_links:
            self.job.info(f"Discovered {len(followable_links)} followable links from {response.url} at depth {response.meta.get('depth', 0)}")

        for href in followable_links:
            full_url = response.urljoin(href)
            request = scrapy.Request(full_url, self.parse_item)
            request.meta['referer'] = response.url
            request.meta['depth'] = response.meta.get('depth', 0) + 1
            # Queue the request            
            yield request


    def parse_start_url(self, response):
        """This is the very start of the crawl, where we process the initial URL.
        and yield items and requests from it.
        """
        self.logger.info(f"Parsing start URLs: {response.url}")
        for item_or_request in self.parse_item(response):
            yield item_or_request
