#!/usr/bin/env python3

from types import SimpleNamespace

import click

from scrapy.crawler import CrawlerProcess

import pgmcp.scrapy.models

from pgmcp.scrapy.models.crawl_job import CrawlJob
from pgmcp.scrapy.spider import Spider
from pgmcp.settings import get_settings


# ===================================================
# PGMCP Bootstrap + Database Setup
# ===================================================
settings = get_settings()

class JobContext(SimpleNamespace):
    @property
    def job_id(self) -> int | None: 
        return getattr(self, '_job_id', None)
    
    @job_id.setter
    def job_id(self, value: int | None):
        if value is not None and not isinstance(value, int):
            raise ValueError("job_id must be an integer or None.")
        self._job_id = value
    
    @property
    def crawl_job(self) -> CrawlJob | None:
        if self.job_id is None: return None
        return CrawlJob.find(self.job_id)

@click.group()
@click.pass_context
def cli(ctx: click.Context):
    """
    Scrapy job CLI.

    Entry point for managing Scrapy jobs via command line.
    """
    # Initialize context object for this CLI invocation
    ctx.obj = JobContext()

@cli.command()
@click.argument('job_id', type=int)
@click.option('--detach', is_flag=True, help="Run in detached (background) mode.", default=False)
@click.pass_obj
def run(ctx: JobContext, job_id: int, detach: bool):
    """Run a Scrapy job.

    Args:
        ctx (JobContext): The CLI context object.
        job_id (int): The ID of the job to run.
        detach (bool): If True, run in detached (background) mode.

    Raises:
        click.ClickException: If the specified CrawlJob is not found.
    """
    ctx.job_id = job_id

    crawl_job = ctx.crawl_job
    if not crawl_job:
        raise click.ClickException(f"CrawlJob with ID {job_id} not found.")

    job = crawl_job.to_scrapy_job()
    process = CrawlerProcess(settings=job.settings.model_dump())
    process.crawl(Spider, job=job)
    
    if detach:
        process.start(stop_after_crawl=False)
        click.echo(f"Job {job_id} started in detached mode.")
    else:
        click.echo(f"Running job {job_id}...")
        process.start(stop_after_crawl=True)

if __name__ == "__main__":
    cli()
