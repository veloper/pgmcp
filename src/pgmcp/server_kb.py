from __future__ import annotations

import json, re

from dataclasses import dataclass
from textwrap import dedent
from typing import Annotated, Any, Dict, List, Literal, Self, Tuple, cast

# Signals
from fastmcp import Client, Context, FastMCP
from fastmcp.client.sampling import SamplingMessage
from fastmcp.prompts.prompt import Message
from mcp.types import PromptMessage, TextContent, ToolAnnotations
from pydantic import Field
from sqlalchemy import func

from pgmcp.markdown_document import MdDocument
from pgmcp.models.corpus import Corpus
from pgmcp.models.crawl_item import CrawlItem
from pgmcp.models.crawl_job import CrawlJob
from pgmcp.models.document import Document
from pgmcp.models.library import Library
from pgmcp.models.section import Section
from pgmcp.models.section_item import SectionItem
from pgmcp.settings import get_settings
from pgmcp.utils import convert_sample_message_from_prompt_message


OVERVIEW = """
    This MCP Server toolset provides a set of tools for managing a knowledge base (KB) system.

    ## Data Model Overview:
    
    ### Polymorphic Classes:
    - `SectionItem`: 
        - **Desc:** Represents a polymorphic join table that connects various sectionable types.
        - **Attributes:** 
            - section_id: int,  
            - sectionable_type: str, 
            - sectionable_id: int, 
            - position: int
        - **Relationships:**
            - section: Section (back_populates="section_items") 
            - sectionable: Union[Paragraph, Section, List, Table, CodeBlock]
    - `ListingItem`:
        - **Desc:** Represents an item in a listing, which can be a listing, paragraph, table
        - **Attributes:** 
            - listing_id: int, 
            - position: int, 
            - listable_type: str, 
            - listable_id: int
        - **Relationships:**
            - listing: Listing (back_populates="listing_items")
            - listable: Union[Listing, Paragraph, Table, CodeBlock]
            
    - `Content`: 
        - **Desc:** Represents the content of a document, which can be text, code, or whatever depending on the source.
        - **Important to note:** The content is always the full content of whatever element it is associated with (e.g., a table would have the full table, rows and cells, not just the outer structure).
    

    ### Hierarchical Structure:
    - `Library`
        - corpora: List[Corpus]
            - `Corpus`
                - documents: List[Document]
                    - `Document`
                        - metadata: Dict[str, Any]
                        - content: Content <see above>
                        - sections: List[Section]
                            - `Section`
                                - position: int
                                - title: str | None
                                - content: Content <see above>
                                - section_items: List[SectionItem]
                                    - `SectionItem` <see above>
    
    ### Sectionable Type Hierarchy:
    - `Section` - Recursive structure that allows this to keep going indefinitely.
    - `Paragraph`
        - content: Content <see above>
        - sentences: List[Sentence]
            - `Sentence`
                - content: Content <see above>
    - `List`
        - listing_items: List[ListingItem]
            - `ListingItem`
                - content: Content <see above>
                - listable: Listable <see above>
    - `Table`
        - content: Content <see above>
        - table_rows: List[TableRow]
            - `TableRow`
                - content: Content <see above>
                - table_row_cells: List[TableRowCell]
                    - `TableRowCell`
                        - content: Content <see above>
    - `CodeBlock`
        - content: Content <see above>
                    
    ## Usage
    This toolset provides a set of tools for ingesting, and recalling from the knowledge base.
    
    All tools follow a datamodel naming convention that is consistent with the above structures and akin to RESTful API design.
    
    We're under the knowledge base library, thus leaving control over the corpus, and documents of that knowledge base.
    
    Example:
    
    - `corpora__documents__ingest :library_id, :corpus_id, :document_uri`
    - `corpora__documents__get :library_id, :corpus_id, :document_id`
    - `documents__get :id` # absolute allows simplified access on a root resource
    - `questions__search :query, limit=10` # search for questions similar to a given query etc.
"""

# =====================================================
# Global Prompts
# =====================================================

PROMPT_CURATE_CRAWL_ITEMS = dedent(f"""
    # IDENTITY AND PURPOSE
    You are a world-class technical documentation curator specializing in selecting the most relevant and high-quality technical documentation pages from a list of web page metadata. 

    Your goal is to go through a list of raw webpage metadata, identify the most relevant technical documentation pages, while excluding irrelevant content. You will perform an analysis based on the following criteria:

    ## CONTEXT

    Use the following characteristics to determine if a page is relevant technical documentation:

    ### Characteristics
    - Select only documentation that is accurate and authoritative—information must be correct, up-to-date, and sourced from credible authorities.
    - Prioritize actionable documentation. Favor pages that provide clear, step-by-step instructions, code samples, or reference details that enable users to solve real problems.
    - Choose comprehensive resources. Ensure the documentation covers core concepts, edge cases, and practical usage, not just surface-level overviews.
    - Evaluate structure critically. Prefer content that is well-organized for easy navigation, with logical hierarchy, searchability, and clear sectioning.
    - Require contextual clarity. Select documentation that explains not just the "how," but also the "why" and "when" to use features or APIs.
    - Ensure audience targeting. Only include documentation written for the intended technical audience (developers, admins, etc.), and exclude anything that is marketing or generic in nature.
    - When multiple documentation versions exist, select the most recent and exclude older versions.

    ## INTERACTION

    ### OUTPUT
    You **MUST** output a comma-separated list of **ID**s that represent your final curation that represents the complete and unabridged set of relevant technical documentation pages to add to the knowledge base. (see illustrative example below)

    ### INPUT
    You will be provided with a list of raw webpage metadata from which you will base your curation.  see illustrative example below)


    ## ILLUSTRATIVE EXAMPLE

    In this illustrative example, we you will see how the **INPUT** is presented, and how you (the curator) should respond with the **OUTPUT**. In this particular case, the curator has determined that the pages with IDs 523 and 524 are relevant, while 525 and 526 are not. This determination is based on body size, URL, depth, and referer information combined with known characteristics of high-quality technical material and common sense url inference. Clearly, the pages with IDs 525 and 526 are not relevant technical documentation pages, as they are likely to be legal, privacy, marketing, or other non-technical content content.

    What's more, the output is strictly constrained to a comma-separated list of integer IDs, with no additional text, formatting, or commentary.

    **INPUT Example:**
    ```json
    [
        {
            "id":523,
            "body_size":15000,
            "url":"https://www.tampermonkey.net",
            "depth":1,
            "referer": null,
        },
        {
            "id":524,
            "body_size":20456,
            "url":"https://www.tampermonkey.net/faq.php",
            "depth":2,
            "referer":"https://www.tampermonkey.net/",
        },
        {
            "id":525,
            "body_size":102,
            "url":"https://www.tampermonkey.net/imprint.php",
            "depth":3,
            "referer":"https://www.tampermonkey.net/faq.php",
        },
        {
            "id":526,
            "body_size":5000,
            "url":"https://www.tampermonkey.net/privacy.php",
            "depth":2,
            "referer":"https://www.tampermonkey.net/",
        }
        

    ]
    ```

    **OUTPUT Example:**
    ```text
    523,524
    ```
""")

# =====================================================
# MCP Setup
# =====================================================
mcp = FastMCP(name="Knowledge Base Service", instructions=OVERVIEW)

# =====================================================
# Settings
# =====================================================
settings = get_settings()

# =====================================================
# =====================================================
# Tools
# =====================================================
# =====================================================

@mcp.tool
async def find_corpus(ctx: Context, corpus_name: str) -> List[Corpus]:
    """Find a corpus_id by its name."""
    async with Corpus.async_context():
        results = await Corpus.query().where("name ILIKE :name", name=corpus_name).all()
    return results  





async def _curate_crawl_job_items(ctx: Context, crawl_job_id: int) -> List[PromptMessage]:
    """Prompt the AI to curate a list of CrawlItems to ensure only relevant and topical items are returned as a comma-separated list."""
    prompt = PROMPT_CURATE_CRAWL_ITEMS

    metadata = {}
    
    async with CrawlJob.async_context():
        crawl_job = await CrawlJob.find(crawl_job_id)
        if not crawl_job:
            raise ValueError(f"CrawlJob with ID {crawl_job_id} does not exist.")
           
        crawl_items = await CrawlItem.query().select([
            CrawlItem.id,
            func.length(CrawlItem.body).label("body_size"),
            CrawlItem.url,
            CrawlItem.depth,
            CrawlItem.referer
        ]).where(CrawlItem.crawl_job_id == crawl_job_id).all()
            
        if not crawl_items:
            raise ValueError(f"No CrawlItems found for CrawlJob with ID {crawl_job_id}.")
        
        metadata = [item.model_dump(exclude_none=True) for item in crawl_items]
            
    return [
        Message(prompt, role="user"),
        Message("Understood! From this point forward I am sworn to only output a comma-separated list of IDs that represent the final curation of relevant technical documentation pages."
                "When the user sends me a collection of CrawlItem records I will conduct my analysis internally, and then output my curated list of ids.", role="assistant"),
        Message(f"```json\n{json.dumps(metadata)}\n```")
    ]


async def _ingest_curated_crawl_items(ctx: Context, crawl_job_id: int, curated_crawl_item_ids: List[int]) -> None:
    """Ingest the curated CrawlItems into the knowledge base."""
    async with CrawlItem.async_context() as async_session:
        async with async_session.begin() as txn: 
            # Get CrawlJob 
            crawl_job = await CrawlJob.find(crawl_job_id)
            if not crawl_job:
                raise ValueError(f"CrawlJob with ID {crawl_job_id} does not exist.")
            
            # Get CrawlItems based on curated_crawl_item_ids + CrawlJob.id
            crawl_items = await CrawlItem.query().where(
                CrawlItem.id.in_(curated_crawl_item_ids),
                CrawlItem.crawl_job_id == crawl_job.id
            ).all()
            
            if not crawl_items:
                raise ValueError(f"No valid CrawlItems found for the provided IDs in CrawlJob {crawl_job_id}.")
            

            # LIBRARY
            library = await Library.query().where(Library.name == "knowledge_base").first()
            if not library:
                library = Library(name="knowledge_base")
                library = await library.save()
                if not library:
                    raise ValueError("Failed to create or retrieve the knowledge base library.")
            
                
            # CORPUS
            corpus_name = next(iter(crawl_job.start_urls), None)
            if corpus_name is None:
                raise ValueError(f"CrawlJob {crawl_job_id} has no start URLs to determine corpus name.")
            corpus_name = re.sub(r'\W+', '_', corpus_name) # Replace non-alphanumeric characters with underscores
            corpus_name = re.sub(r'__+', '_', corpus_name) # Ensure no double underscores
            
            corpus = await Corpus.query().where(
                Corpus.name == corpus_name,
                Corpus.library_id == library.id
            ).first()

            if not corpus:
                corpus = Corpus(name=corpus_name, library_id=library.id)
                corpus = await corpus.save()
                if not corpus:
                    raise ValueError("Failed to create or retrieve the corpus.")
                
            
            
            @dataclass(frozen=True)
            class WorkItem:
                crawl_item_id: int
                crawl_item_body: str
                crawl_item_headers: Dict[str, Any]
                crawl_item_url: str
                corpus_id: int
                
                @classmethod
                def from_corpus_and_crawl_item(cls, corpus: Corpus, crawl_item: CrawlItem) -> Self:
                    return cls(
                        crawl_item_id=crawl_item.id,
                        crawl_item_body=crawl_item.body,
                        crawl_item_headers=dict(crawl_item.response_headers or {}),
                        crawl_item_url=crawl_item.url,
                        corpus_id=corpus.id
                    )
                
                    
                
                def get_markdown_document(self) -> MdDocument:
                    """Convert the work item to a markdown document."""
                    return MdDocument.from_str(
                        text=self.crawl_item_body,
                        title=self.crawl_item_headers.get("title", "Untitled Document")
                    )
                    
            work_items = [WorkItem.from_corpus_and_crawl_item(corpus, crawl_item) for crawl_item in crawl_items]

            

@mcp.tool
async def ingest_crawl_job(ctx: Context, crawl_job_id: int) -> None:
    """Ingest a CrawlJob into the knowledge base."""
    
    
    sample_messages = []

    # convert the prompt so it's using SamplingMessage objects and the system prompt is plucked from the first entry.
    prompt_messages: List[PromptMessage] = await _curate_crawl_job_items(ctx, crawl_job_id)
    if not prompt_messages:
        raise ValueError("No prompt messages found for curation.")
    
    system_message = str(prompt_messages.pop(0).content)
    
    for msg in prompt_messages:
        if not isinstance(msg, PromptMessage):
            raise ValueError(f"Expected PromptMessage, got {type(msg)}")
        content = str(msg.content)  # Ensure content is a string
        if not content:
            raise ValueError("PromptMessage content cannot be empty.")
        if not msg.role:
            raise ValueError("PromptMessage role cannot be empty.")

    sample_messages : List[SamplingMessage | str] = [convert_sample_message_from_prompt_message(msg) for msg in prompt_messages]

    # SAMPLE
    response = await ctx.sample(
        system_prompt=system_message,
        messages=sample_messages,
        temperature=0.1, 
        max_tokens=2000,
    )

    valid_response = re.compile(r"^\d+(,\d+)*$")  # Regex to match comma-separated integers
    if not response or not isinstance(response, SamplingMessage) or not valid_response.match(str(response.content)):
        raise ValueError("Failed to generate a valid response.")
    
    curated_crawl_item_ids = [int(id.strip()) for id in str(response.content).split(",") if id.strip().isdigit()]
    
    # CONFIRM
    async with CrawlItem.async_context() as async_session:
        crawl_items = await CrawlItem.query().where(
            CrawlItem.id.in_(curated_crawl_item_ids),
            CrawlItem.crawl_job_id == crawl_job_id
        ).all()
        
        if not crawl_items:
            raise ValueError(f"No valid CrawlItems found for the provided IDs in CrawlJob {crawl_job_id}.")
        
    # ELICIT CONFIRMATION
    result = await ctx.elicit("Approve this action?", response_type=None)

    if result.action == "accept":
        await ctx.info(f"Curating {len(crawl_items)} items from CrawlJob {crawl_job_id} into the knowledge base.")
        






@mcp.prompt( name="curate_crawl_job_items", )
async def curate_crawl_job_items(ctx: Context, crawl_job_id: int) -> List[PromptMessage]:
    return await _curate_crawl_job_items(ctx, crawl_job_id)
