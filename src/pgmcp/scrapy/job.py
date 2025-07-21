from typing import TYPE_CHECKING, Any, Dict, List, Self
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator
from scrapy.crawler import CrawlerProcess
from scrapy.settings import SETTINGS_PRIORITIES, BaseSettings

from pgmcp.models.crawl_job import CrawlJob, CrawlJobStatus
from pgmcp.scrapy.settings import CustomSettings, Settings


if TYPE_CHECKING:
    from pgmcp.scrapy.spider import Spider


class Job(BaseModel):
    """Represents a web scraping job configuration."""
    start_urls      : List[str]            = Field(default_factory=list, description="Initial URLs to start crawling")
    settings        : Settings             = Field(default_factory=CustomSettings, description="Custom settings for the spider")
    allowed_domains : List[str]            = Field(default_factory=list, description="Domains to restrict crawling to")
    id              : int | None           = Field(default=None, description="Unique identifier for the job")
    

    @field_validator("settings" , mode="before")
    @classmethod
    def validate_settings(cls, value: dict[str, Any]) -> Settings:
        # coerce to CustomScrapySettings
        return CustomSettings.model_validate(value)

    async def transition_to_running(self) -> None:
        """Run the spider with the provided configuration."""
        from pgmcp.scrapy.spider import Spider

        job = await self.get_or_create_crawl_job()
        process = CrawlerProcess(settings=self.settings.model_dump())

        process.crawl(Spider, job=self)
        
        process.start()  # This will block until the crawling is finished

    async def pause(self) -> None:
        """Pause the job if supported by the spider."""
        # Implementation depends on how the spider handles pausing
        pass

    async def get_crawl_job(self) -> CrawlJob | None:
        """Get the CrawlJob instance associated with this job."""
        from pgmcp.models.crawl_job import CrawlJob
        if self.id:
            return await CrawlJob.find(self.id)
        return None

    async def get_or_create_crawl_job(self) -> CrawlJob | None:
        """Get the CrawlJob instance or create a new one if it doesn't exist."""
        crawl_job = await self.get_crawl_job()
        if not crawl_job:
            crawl_job = CrawlJob(
                start_urls=self.start_urls,
                allowed_domains= self.allowed_domains,
                settings= self.settings.model_dump()
            )
            await crawl_job.save()
            self.id = crawl_job.id  # Update the job ID after creation
        
        return crawl_job
    
    async def log(self, message: str, level: str = "INFO", context: Dict[str, Any] | None = None) -> None:
        """Log a message related to this item and job it's associated with."""
        if crawl_job := await self.get_or_create_crawl_job():
            await crawl_job.log(message, level=level, context=context)
        raise ValueError("Unable to create or find CrawlJob instance to log message.")
            

    async def info(self, message: str, context: Dict[str, Any] | None = None) -> None:
        await self.log(message, level="INFO", context=context)
    
    async def debug(self, message: str, context: Dict[str, Any] | None = None) -> None:
        await self.log(message, level="DEBUG", context=context)
        
    async def warning(self, message: str, context: Dict[str, Any] | None = None) -> None:
        await self.log(message, level="WARNING", context=context)
        
    async def error(self, message: str, context: Dict[str, Any] | None = None) -> None:
        await self.log(message, level="ERROR", context=context)


    @classmethod
    async def create(cls, start_urls: List[str] = [], *, id: int | None = None, allowed_domains: List[str] = [], settings: dict[str, Any] | None = None) -> Self:
        """Create a new job instance with the provided configuration.

        If `id` is not provided, it will be set by creating a new record in the database.
        If `allowed_domains` is not provided, it defaults to start_urls' domains.
        """
        

        # Automatically extract allowed domains from start_urls if not provided
        if not allowed_domains:
            allowed_domains = [urlparse(url).netloc for url in start_urls]

        # If id is None, it will be set by the database when saving
        if id is None:
            from pgmcp.models.crawl_job import CrawlJob            
            job = CrawlJob(
                start_urls=start_urls,
                allowed_domains=allowed_domains,
                settings=settings or {}
            )
            await job.save()
            id = job.id
            

        return cls.model_validate({
            "start_urls": start_urls,
            "allowed_domains": allowed_domains,
            "settings": settings,
            "id": id
        })

    def to_base_settings(self) -> BaseSettings:
        """Convert the job settings to a scrapy.settings.BaseSettings instance."""
        base_settings = BaseSettings()
        base_settings.setdict(self.settings.model_dump(), priority=SETTINGS_PRIORITIES["spider"])
        return base_settings
