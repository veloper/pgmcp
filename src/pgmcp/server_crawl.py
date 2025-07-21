from typing import Annotated, Any, Dict, List, Literal, Tuple

from fastmcp import Context, FastMCP
from pydantic import Field
from sqlalchemy import distinct, func

from pgmcp.models.crawl_item import CrawlItem  # Import to ensure SQLAlchemy registration
from pgmcp.models.crawl_job import CrawlJob
from pgmcp.models.crawl_log import CrawlLog  # Import to ensure SQLAlchemy registration
from pgmcp.payload import Payload
from pgmcp.settings import get_settings


OVERVIEW = """
# Crawl MCP Module
This module implements a Machine Control Protocol (MCP) interface for orchestrating web crawling operations using Scrapy and PostgreSQL.

## Key Features:
- Defines, manages, and executes web crawling jobs as discrete entities.
- Provides tools for job creation, initiation, pausing, listing, and retrieval.
- Ensures all job metadata and crawl results are persisted in a PostgreSQL database, enabling decoupled pipeline operations and robust state management.
- Enforces domain boundaries: crawled URLs are restricted to the domains specified in the initial start_urls.
- Deduplication: All URLs are deduplicated at the run layer to prevent redundant crawling.

This interface abstracts the crawling workflow, allowing external agents (including LLMs) to interact with and control the lifecycle of 
Scrapy jobs programmatically, while maintaining strict operational constraints and data integrity.

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

    
@mcp.tool(tags={"scrapy", "spider", "crawler", "job", "define", "create"})
async def create_job(ctx: Context, 
    start_urls: Annotated[List[str], Field(description="List of URLs to start crawling from")],
    depth: Annotated[int, Field(description="Maximum depth to crawl")] = 3,
) -> Dict[str, Any]:
    """Define a new Scrapy job that will not run until explicitly started using `start_job` tool."""
    
    job = CrawlJob(
        start_urls=start_urls,
        settings={"DEPTH_LIMIT": depth},
        allowed_domains=[url.split("//")[-1].split("/")[0] for url in start_urls],
    )
    
    await job.save()
    
    return Payload.create(
        job.model_dump(), message="Job defined successfully"
    ).model_dump()


@mcp.tool(tags={"scrapy", "spider", "crawler", "job", "control"})
async def control_job(ctx: Context, 
    job_ids : Annotated[List[int], Field(description="List of job IDs to control")],
    action  : Annotated[Literal["enqueue", "pause", "resume", "cancel", "retry"], Field(
        description="Attempt to perform one of the following actions: enqueue, pause, resume, cancel, or retry",
        pattern= r"^(enqueue|pause|resume|cancel|retry)$"
    )]
) -> Dict[str, Any]:
    """Control a set of Scrapy jobs by specifying their IDs and the action to perform on them.
    
    Allowed Transitions by Action:
    - `enqueue`: [([IDLE], [READY])]
    - `pause`: [([RUNNING], [PAUSED])]
    - `resume`: [([PAUSED], [RUNNING])]
    - `cancel`: [([IDLE, READY, RUNNING, PAUSED], [CANCELLED])]
    - `retry`: [([FAILED], [READY])]    
        
    """
    crawl_jobs = await CrawlJob.query().where(id=job_ids).all()
    if not crawl_jobs:
        raise ValueError(f"CrawlJobs with IDs {job_ids} do not exist.")
    
    errors: List[Tuple[CrawlJob, str]] = []
    
    for crawl_job in crawl_jobs:
        try:
            if action == "enqueue":
                await crawl_job.enqueue()
            elif action == "pause":
                await crawl_job.pause()
            elif action == "resume":
                await crawl_job.resume()
            elif action == "cancel":
                await crawl_job.cancel()
            elif action == "retry":
                await crawl_job.retry()
        except ValueError as e:
            errors.append((crawl_job, f"Transition Error: {e!r}"))

    # Prep Response
    current_crawl_jobs = await CrawlJob.query().where(id=job_ids).all()
    payload_collection = [job.model_dump() for job in current_crawl_jobs]

    if errors:
        error_messages = "\n".join([f"CrawlJob({job.id}) encountered an error while trying to {action} it: {error}" for job, error in errors])
        error_messages += "\n\nOther CrawlJobs not mentioned were successfully processed."

        return Payload.create(payload_collection, error=error_messages).model_dump()

    return Payload.create(payload_collection, message=f"Job {action}d successfully").model_dump()
    
    
@mcp.tool(tags={"scrapy", "spider", "crawler", "job", "get"})
async def get_job(ctx: Context, job_id: int) -> Dict:
    """Get extra information about a specific Scrapy job by its ID."""
    crawl_job = await CrawlJob.find(job_id)
    if not crawl_job:
        raise ValueError(f"CrawlJob with ID {job_id} does not exist.")
    
    return Payload.create(crawl_job, message="Job retrieved successfully").model_dump()



    
@mcp.tool(tags={"scrapy", "spider", "crawler", "job", "start"})
async def list_jobs(
    ctx: Context,
    per_page : Annotated[int, Field(description="Number of jobs per page", ge=1, lt=100)] = 15, 
    page     : Annotated[int, Field(description="Page number to retrieve", ge=1)] = 1,
    sort     : Annotated[str, Field(description="Attribute to sort jobs by", pattern=r"^(id|created_at|updated_at|status)$")] = "id", 
    order    : Annotated[str, Field(description="Sort order: asc or desc", pattern=r"^(asc|desc)$")] = "desc"
) -> Dict[str, Any]:
    """List all Scrapy jobs."""
    async with CrawlJob.transaction() as async_session:
        payload = Payload()
        
        # Build base query
        qb = CrawlJob.query()
        
        # Apply sorting
        if sort not in ["created_at", "updated_at", "status", "id"]: raise ValueError(f"Invalid sort attribute: {sort}")
        if order not in ["asc", "desc"]: raise ValueError(f"Invalid sort order: {order}")
        qb = qb.order(sort, order)  # type: ignore

        # Count the logs and items associated with each job - efficient single query
        qb = qb.select(
            "crawl_jobs.*",
            "COUNT(DISTINCT crawl_logs.id) AS log_count",
            "COUNT(DISTINCT crawl_items.id) AS item_count"
        )
        qb = qb.left_joins("crawl_items")
        qb = qb.left_joins("crawl_logs")
        qb = qb.group_by("crawl_jobs.id")

        # Apply pagination
        offset = (page - 1) * per_page
        qb = qb.limit(per_page).offset(offset)

        # Count total records
        payload.metadata.count = await CrawlJob.count()
        payload.metadata.page = page
        payload.metadata.per_page = per_page
        
        # Get results - QueryBuilder will handle model reconstruction with aggregates
        models = await qb.all()
        
        for model in models:
            # model_dump now automatically includes aggregate fields from _row_data
            model_data = model.model_dump(exclude_none=True)
            payload.collection.append(model_data)

        return payload.model_dump()


@mcp.tool(tags={"scrapy", "spider", "crawler", "job", "enqueue"})
async def start_job(ctx: Context, crawl_job_id: int) -> Dict[str, Any]:
    """Enqueue a Scrapy job by its ID to be run by the Scrapy engine asap."""
    crawl_job = await CrawlJob.find(crawl_job_id)
    if not crawl_job:
        raise ValueError(f"CrawlJob with ID {crawl_job_id} does not exist.")

    await crawl_job.enqueue()
    
    return Payload.create(crawl_job, message="Job enqueued successfully").model_dump()

# @mcp.tool
# async def job_pause(ctx: Context, job_id: str) -> str:
#     """Pause a Scrapy job by its ID."""
#     return f"Job {job_id} paused"
