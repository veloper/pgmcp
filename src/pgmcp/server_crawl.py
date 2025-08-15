import asyncio

from asyncio.tasks import create_task
from textwrap import dedent
from typing import Annotated, Any, Dict, List, Literal, Tuple

from fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field
from sqlalchemy import distinct, func

from pgmcp.models.crawl_item import CrawlItem  # Import to ensure SQLAlchemy registration
from pgmcp.models.crawl_job import CrawlJob
from pgmcp.models.crawl_log import CrawlLog  # Import to ensure SQLAlchemy registration
from pgmcp.payload import Payload
from pgmcp.scraper.job import Job
from pgmcp.settings import get_settings


OVERVIEW = """
# Crawl MCP Module
This module implements a Machine Control Protocol (MCP) interface for orchestrating web crawling operations using Scrapy and PostgreSQL.

## Flow

1. Create a Job using the `create_job` tool, specifying the initial URLs and depth.
2. Start the Job with the `start_job` tool, which enqueues it for execution.
3. Monitor the Job's progress using the `monitor_job` tool, which provides real-time progress updates.
4. Report a visually appealing summary of the Job's progress, including:
    
## Job States

IDLE       = 1      # Job is being configured, has not been placed into any other state
READY      = 2      # Job is ready to be run
RUNNING    = 4      # Job is in the process of running
PAUSED     = 8      # Job has been manually paused
FAILED     = 16     # Job has failed for some reason
CANCELLED  = 32     # Job has been manually cancelled
SUCCEEDED  = 64     # Job has completed successfully

## Job Transitions

IDLE        : [READY, CANCELLED, FAILED],             # Actions: enqueue, cancel, fail
READY       : [RUNNING, CANCELLED, FAILED],           # Actions: run, cancel, fail
RUNNING     : [PAUSED, SUCCEEDED, FAILED, CANCELLED], # Actions: pause, succeed, fail, cancel
PAUSED      : [RUNNING, CANCELLED, FAILED],           # Actions: resume, cancel, fail
FAILED      : [READY, CANCELLED],                     # Actions: retry, cancel
SUCCEEDED   : [], 
CANCELLED   : [],
"""


# =====================================================
# MCP Setup
# =====================================================
mcp = FastMCP(name="crawl", instructions=OVERVIEW)

# =====================================================
# Settings
# =====================================================
settings = get_settings()

# =====================================================
# DB Decorators
# =====================================================

@mcp.tool(tags={"spider", "crawler", "job", "define", "create"}, annotations=ToolAnnotations(
    idempotentHint=False
))
async def create_job(
    ctx: Context, 
    start_urls: Annotated[List[str], Field(description="List of URLs to start crawling from")],
    depth: Annotated[int, Field(description="Maximum depth to crawl")] = 3,
) -> Dict[str, Any]:
    """Define a new crawl job that will not run until explicitly started using `start_job` tool."""
    async with CrawlJob.async_context() as async_session:
        job = CrawlJob(
            start_urls=start_urls,
            settings={"DEPTH_LIMIT": depth},
            allowed_domains=[url.split("//")[-1].split("/")[0] for url in start_urls],
        )
    
        await job.save()
        
        return Payload.create(job.model_dump(), message="Job defined successfully").model_dump()

@mcp.tool(tags={"spider", "crawler", "job", "get"}, annotations=ToolAnnotations(
    readOnlyHint=True,
    idempotentHint=True
))
async def get_job(ctx: Context, job_id: int) -> Dict:
    """Get extra information about a specific crawl job by its ID."""
    async with CrawlJob.async_context() as async_session:
        crawl_job = await CrawlJob.find(job_id)
        if not crawl_job:
            raise ValueError(f"CrawlJob with ID {job_id} does not exist.")

        return Payload.create(crawl_job, message="Job retrieved successfully").model_dump()




@mcp.tool(tags={"spider", "crawler", "job", "start"}, annotations=ToolAnnotations(
    idempotentHint=False
))
async def list_jobs(
    ctx: Context,
    per_page : Annotated[int, Field(description="Number of jobs per page", ge=1, lt=100)] = 15, 
    page     : Annotated[int, Field(description="Page number to retrieve", ge=1)] = 1,
    sort     : Annotated[str, Field(description="Attribute to sort jobs by", pattern=r"^(id|created_at|updated_at|status)$")] = "id", 
    order    : Annotated[str, Field(description="Sort order: asc or desc", pattern=r"^(asc|desc)$")] = "desc"
) -> Dict[str, Any]:
    """List all crawl jobs."""
    async with CrawlJob.async_context():
        payload = Payload()
        
        # Build base query
        qb = CrawlJob.query()
        
        # Apply sorting
        if sort not in ["created_at", "updated_at", "status", "id"]: raise ValueError(f"Invalid sort attribute: {sort}")
        if order not in ["asc", "desc"]: raise ValueError(f"Invalid sort order: {order}")
        qb = qb.order(sort, order)  # type: ignore

        # Apply pagination
        offset = (page - 1) * per_page
        qb = qb.limit(per_page).offset(offset)

        # Count total records
        payload.metadata.count = await CrawlJob.query().count()
        payload.metadata.page = page
        payload.metadata.per_page = per_page
        
        # Get results - QueryBuilder will handle model reconstruction with aggregates
        models = await qb.all()
        
        for model in models:
            # model_dump now automatically includes aggregate fields from _row_data
            model_data = model.model_dump()
            payload.collection.append(model_data)

        return payload.model_dump()

@mcp.tool(tags={"spider", "crawler", "job", "start"}, annotations=ToolAnnotations(
    idempotentHint=False
))
async def start_job(ctx: Context, crawl_job_id: int) -> Dict[str, Any]:
    """Enqueue a crawl job by its ID to be run by the Scrapy engine asap."""
    async with CrawlJob.async_context():
        crawl_job = await CrawlJob.find(crawl_job_id)
        if not crawl_job:
            raise ValueError(f"CrawlJob with ID {crawl_job_id} does not exist.")

        # Ensure job is in READY state before running it.
        await crawl_job.enqueue()
        
        # Get the job
        job = crawl_job.to_scrapy_job()
            
        # Start the job in the background while polling for updates
        await job.run(background=True)
        
        # At this point the job is done.
        await crawl_job.refresh() # make sure we have the latest state

        instructions = dedent(f"""
        # AI Instructions
        
        - **Result:** 
            - The job with **ID:{crawl_job_id}** has been started and is running in the background.
        - **Next Steps:** 
            - You can monitor the job's progress and status using the `get_job` tool with the job ID:{crawl_job_id}.
            - Use `get_job` at least three times to get a sense of how fast the job is running and provide the user with an analysis of the job's progress.
        """)

        return Payload.create(crawl_job, message=instructions).model_dump()

@mcp.tool(tags={"spider", "crawler", "job", "monitor"}, annotations=ToolAnnotations(
    idempotentHint=True,
    readOnlyHint=True
))
async def monitor_job(
    ctx: Context, 
    crawl_job_id: int, 
    timeout: Annotated[float, Field(description="Seconds to wait for job completion", ge=5, le=60*10)] = 30
) -> Dict[str, Any]:
    """Follow a crawl job by its ID and return its current status."""
    async with CrawlJob.async_context():
        crawl_job = await CrawlJob.find(crawl_job_id)
        if not crawl_job:
            raise ValueError(f"CrawlJob with ID {crawl_job_id} does not exist.")

        async def reporter():
            while True:
                await asyncio.sleep(0.250)
                await crawl_job.refresh()

                progress, total, ratio = crawl_job.stats_progress_and_total_and_ratio
                message = crawl_job.stats_message_line

                await ctx.report_progress(progress=progress, total=total, message=message)
                
                if crawl_job.is_done:
                    await ctx.report_progress(progress=total, total=total, message=message)
                    break

        try:
            await asyncio.wait_for(reporter(), timeout=timeout)
        except asyncio.TimeoutError:
            pass # suppress as expected.
                
        # Get the job status
        return Payload.create(crawl_job).model_dump()

@mcp.tool(tags={"spider", "crawler", "job", "logs"}, annotations=ToolAnnotations(
    idempotentHint=True,
    readOnlyHint=True
))
async def get_job_logs(
    ctx: Context,
    crawl_job_id: int, 
    per_page: Annotated[int, Field(description="Number of logs to retrieve", ge=1, le=100)] = 25,
    page: Annotated[int, Field(description="Page number to retrieve", ge=1)] = 1
) -> Dict[str, Any]:
    """Get detailed logs for a specific crawl job by its ID."""
    async with CrawlJob.async_context() as async_session:
        crawl_job = await CrawlJob.find(crawl_job_id)
        
        if not crawl_job:
            raise ValueError(f"CrawlJob with ID {crawl_job_id} does not exist.")
        
        # Build the query
        qb = CrawlLog.query().where(crawl_job_id=crawl_job_id).order("id", "asc")

        # Apply pagination
        offset = (page - 1) * per_page
        qb = qb.limit(per_page).offset(offset)

        # Get results
        logs = await qb.all()

        return Payload.create(
            list(logs), 
            count=await CrawlLog.query().where(crawl_job_id=crawl_job_id).count(),
            page=page,
            per_page=per_page,
        ).model_dump()

