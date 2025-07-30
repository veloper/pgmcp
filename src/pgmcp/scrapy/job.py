import asyncio, json

from pathlib import Path
from sys import stderr, stdout
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, List, Self
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator
from scrapy.crawler import CrawlerProcess
from scrapy.settings import SETTINGS_PRIORITIES, BaseSettings

from pgmcp.scrapy.models.crawl_job import CrawlJob, CrawlJobStatus
from pgmcp.scrapy.models.log_level import LogLevel
from pgmcp.scrapy.settings import CustomSettings, Settings
from pgmcp.settings import get_settings


if TYPE_CHECKING:
    from pgmcp.scrapy.spider import Spider

class Job(BaseModel):
    """Represents a web scraping job configuration decoupled from the database."""
    
    id              : int                  = Field(description="Unique identifier for the job")
    start_urls      : List[str]            = Field(default_factory=list, description="Initial URLs to start crawling")
    settings        : Settings             = Field(default_factory=CustomSettings, description="Custom settings for the spider")
    allowed_domains : List[str]            = Field(default_factory=list, description="Domains to restrict crawling to")
    

    @field_validator("settings" , mode="before")
    @classmethod
    def validate_settings(cls, value: dict[str, Any]) -> Settings:
        # Coerce to CustomScrapySettings
        return CustomSettings.model_validate(value)

    def reload(self) -> None:
        crawl_job_model = self.crawl_job_model()
        if crawl_job_model:
            self.start_urls = crawl_job_model.start_urls
            self.allowed_domains = crawl_job_model.allowed_domains
            self.settings = CustomSettings.model_validate(crawl_job_model.settings)

    async def run(self, background: bool = False) -> None:
        """Run the spider with the provided configuration in the background.

        Done via a subprocess to avoid the hassle of asyncio conflicts.
        """
        root_path         : Path = get_settings().app.root_path
        pkg_path          : Path = get_settings().app.package_path.resolve()
        executable_path   : Path = pkg_path / "scrapy" / "cli.py"
        working_dir_path  : Path = root_path
        
        python_executable : Path = root_path / ".venv" / "bin" / "python"

        
        if not executable_path.exists():
            raise FileNotFoundError(f"Scrapy executable not found at {executable_path}")
        cmd = [str(python_executable), str(executable_path), "run", str(self.id)]
        
        if background:
            cmd.append("--detach")
        
        proc = await asyncio.create_subprocess_exec( *cmd, cwd=working_dir_path, stdout=stdout, stderr=stderr )

        if background:
            asyncio.create_task(proc.wait())
        else:
            await proc.wait()

    async def run_with_polling_loop(self, coro: Callable[[Self, Dict[str, Any]], Awaitable[None]], interval: int) -> None:
        """Same as run, but you can provide an async coro that will be called every x milliseconds."""
        memo = {}
        async def polling_loop():
            try:
                while True:
                    await coro(self, memo) # externally bound memo dict
                    await asyncio.sleep(float(interval / 1000))
            except asyncio.CancelledError:
                pass # complete
                
        polling_task = asyncio.create_task(polling_loop())
        running_task = asyncio.create_task(self.run(background=False))
        
        # wait for the running task to complete
        await running_task
        # cancel the polling task
        polling_task.cancel()
        try:
            await polling_task # wait for it to finish
        except asyncio.CancelledError:
            pass

    def crawl_job_model(self) -> CrawlJob:
        """Get the CrawlJob instance associated with this job."""
        from pgmcp.scrapy.models.crawl_job import CrawlJob
        if model := CrawlJob.find(self.id):
            return model
        raise ValueError(f"CrawlJob with id {self.id} not found.")


    def log(self, message: str, level: LogLevel, context: Dict[str, Any] | None = None) -> None:
        if crawl_job := self.crawl_job_model():
            crawl_job.log(message, level=level, context=context)

    def info(self, message: str, context: Dict[str, Any] | None = None)     -> None: self.log(message, level=LogLevel.INFO, context=context)
    def debug(self, message: str, context: Dict[str, Any] | None = None)    -> None: self.log(message, level=LogLevel.DEBUG, context=context)
    def warning(self, message: str, context: Dict[str, Any] | None = None)  -> None: self.log(message, level=LogLevel.WARNING, context=context)
    def error(self, message: str, context: Dict[str, Any] | None = None)    -> None: self.log(message, level=LogLevel.ERROR, context=context)
    def critical(self, message: str, context: Dict[str, Any] | None = None) -> None: self.log(message, level=LogLevel.CRITICAL, context=context)

    @classmethod
    def from_crawl_job(cls, id: int, start_urls: List[str] = [], allowed_domains: List[str] = [], settings: Dict[str, Any] | None = None) -> Self:
        return cls.model_validate({
            "id": id,
            "start_urls": start_urls,
            "allowed_domains": allowed_domains,
            "settings": CustomSettings.model_validate(settings) if settings else None
        })

    def to_base_settings(self) -> BaseSettings:
        """Convert the job settings to a scrapy.settings.BaseSettings instance."""
        base_settings = BaseSettings()
        base_settings.setdict(self.settings.model_dump(), priority=SETTINGS_PRIORITIES["spider"])
        return base_settings
