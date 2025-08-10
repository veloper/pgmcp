# from __future__ import annotations

import datetime

from textwrap import dedent
from typing import Annotated, Any, Awaitable, Callable, Dict, List, NamedTuple

# Signals
from fastmcp import Context, FastMCP
from pydantic import Field
from sqlalchemy import Tuple

from pgmcp.async_worker_pool import AsyncWorkerPoolBase
from pgmcp.chunking.document import Document as ChunkDocument
from pgmcp.models.base_query_builder import QueryBuilder
from pgmcp.models.chunk import Chunk
from pgmcp.models.corpus import Corpus
from pgmcp.models.crawl_item import CrawlItem
from pgmcp.models.crawl_job import CrawlJob
from pgmcp.models.document import Document
from pgmcp.models.library import Library
from pgmcp.payload import Payload


KNOWLEDGE_BASE_LIBRARY_NAME = "Knowledge Base"
_kb_library: Library | None = None
async def get_knowledge_base_library() -> Library:
    """Get or create the knowledge base library."""
    
    global _kb_library
    if not _kb_library:
        async with Library.async_context():
            _kb_library = await Library.query().where(Library.name == KNOWLEDGE_BASE_LIBRARY_NAME).first()
            if not _kb_library:
                _kb_library = Library(name=KNOWLEDGE_BASE_LIBRARY_NAME)
                await _kb_library.save()
    return _kb_library

_named_corpus_cache: Dict[str, Corpus] = {}
async def get_corpus_by_name_or_create(name: str) -> Corpus:
    """Get or create a corpus by name."""
    global _named_corpus_cache
    async with Corpus.async_context():
        if name in _named_corpus_cache:
            return _named_corpus_cache[name]
        library = await get_knowledge_base_library()
        corpus = await Corpus.query().where(Corpus.name == name, Corpus.library_id == library.id).first()
        if not corpus:
            corpus = Corpus(name=name, library_id=library.id)
            await corpus.save()
        _named_corpus_cache[name] = corpus
        return corpus
    raise ValueError(f"Failed to get or create corpus with name: {name}")

OVERVIEW = """
    # Knowledge Base Service Overview

    ## Data Model Overview:

    ### Hierarchical Structure:
    - corpora: List[Corpus]
        - `Corpus`
            - documents: List[Document]
                - `Document`
                    - metadata: Dict[str, Any]
                    - body: Element
                        - `Element`
                            - type: str (body, section, paragraph, sentence, listing, table, table_row, table_row_cell, code_block)
                            - content: Content (e.g., text, code, etc.)
                            - embedding : Optional[Embedding] (if applicable)
                            - attributes: Dict[str, Any] (e.g., title for sections)
                            - left: int (for tree structure)
                            - right: int (for tree structure)
                            - level: int (for tree structure)
                            - position: int (for tree structure)
                            - children: List[Element] (recursive structure)
                            - parent: Element | None (for tree structure)
                            - document: Document (back-reference to the document only on body elements)

                    
    ## Usage
    This toolset works hand in hand with the crawl_* jobs to handle the ingestion, curation, and management of technical documentation pages into a knowledge base.
    
    We're under the knowledge base library, thus leaving control over the corpus, and documents of that knowledge base.
    
    Example:
    
    - `documents__ingest :library_id, :corpus_id, :document_uri`
    - `documents__get :library_id, :corpus_id, :document_id`
    - `documents__get :id` # absolute allows simplified access on a root resource
    - `questions__search :query, limit=10` # search for questions similar to a given query etc.
"""

# =====================================================
# Global Prompts
# =====================================================

PROMPT_CURATE_CRAWL_ITEMS = dedent("""
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
    You will be provided with a list of raw webpage metadata from which you will base your curation.  See illustrative example below)


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
# =====================================================
# Tools
# =====================================================
# =====================================================

def std_corpora_query_builder(per_page: int = 15, page: int = 1, sort: str = "id", order: str = "asc") -> QueryBuilder[Corpus]:
    qb = Corpus.query()
    qb = qb.select(
        "corpora.*",
        "COUNT(DISTINCT documents.id) AS documents_count",
        "COUNT(DISTINCT chunks.id) AS chunks_count",
        "SUM(chunks.token_count) AS chunks_token_total",
    )
    
    qb = qb.left_joins(Corpus.documents)
    qb = qb.left_joins(Document.chunks)


    if not sort.startswith("corpora."):
        sort = f"corpora.{sort}"
    if sort not in ["corpora.id", "corpora.created_at", "corpora.updated_at", "corpora.name"]:
        raise ValueError(f"Invalid sort attribute: {sort}")
    
    if order != "asc" and order != "desc":
        raise ValueError(f"Invalid sort order: {order}")

    qb = qb.order(sort, order)  

    qb = qb.group_by(Corpus.id)
    
    qb = qb.limit(per_page).offset((page - 1) * per_page)
    return qb

@mcp.tool(tags={"corpora", "list", "data", "start"})
async def list_corpora(
    per_page : Annotated[int, Field(description="Number of corpora per page", ge=1, lt=100)] = 15, 
    page     : Annotated[int, Field(description="Page number to retrieve", ge=1)] = 1,
    sort     : Annotated[str, Field(description="Attribute to sort corpora by", pattern=r"^(id|created_at|updated_at|name)$")] = "id", 
    order    : Annotated[str, Field(description="Sort order: asc or desc", pattern=r"^(asc|desc)$")] = "desc"
) -> Dict[str, Any]:
    """List all corpora."""
    async with Corpus.async_context():
        if sort not in ["id", "created_at", "updated_at", "name"]: raise ValueError(f"Invalid sort attribute: {sort}")
        if order not in ["asc", "desc"]: raise ValueError(f"Invalid sort order: {order}")
        payload = Payload()

        qb = std_corpora_query_builder(per_page=per_page, page=page, sort=sort, order=order)

        payload.metadata.count = await Corpus.query().count()
        payload.metadata.page = page
        payload.metadata.per_page = per_page
        
        models = await qb.all()
        
        for model in models:
            model_data = model.model_dump()
            payload.collection.append(model_data)

        return payload.model_dump()


class ChunkDocumentJob(NamedTuple):
    crawl_item_id: int
    chunk_document: ChunkDocument

class ChunkDocumentWorkerPool(AsyncWorkerPoolBase[ChunkDocumentJob]):
    """Worker pool for processing ChunkDocuments."""

    def __init__(self, jobs: list[ChunkDocumentJob], worker_count: int = 10):
        super().__init__(jobs=jobs, worker_count=worker_count)
        self.on_job_done : Callable[[ChunkDocumentJob, bool, str | None], Awaitable[None]] | None = None

    async def work(self, job: ChunkDocumentJob) -> None:
        """Process a single ChunkDocument."""
        try:
            job.chunk_document.chunks # Create chunks (and memoize them)
        except Exception as e:
            raise RuntimeError(f"Failed to process ChunkDocument for CrawlItem {job.crawl_item_id}: {e}") from e
        
    async def done(self, job: ChunkDocumentJob, status: bool, message: str | None = None) -> None:
        """Handle completion of a job."""
        if self.on_job_done:
            await self.on_job_done(job, status, message)

@mcp.tool
async def ingest_crawl_job(ctx: Context, crawl_job_id: int) -> Dict[str, Any]:
    """Ingest a CrawlJob into the knowledge base."""
    async with CrawlJob.async_context() as session:
        crawl_job = await CrawlJob.query().find(crawl_job_id)
        if not crawl_job:
            raise ValueError(f"CrawlJob with ID {crawl_job_id} not found.")
        
        corpus_name = crawl_job.get_name_from_most_common_domain()

        corpus = await get_corpus_by_name_or_create(corpus_name)
        
        # Delete existing documents in the corpus
        async for doc in Document.query().where(Document.corpus_id == corpus.id).find_each(batch_size=100):
            await doc.destroy()

        qb = CrawlItem.query().where(CrawlItem.crawl_job_id == crawl_job_id).where(CrawlItem.status == 200)

        total_items = await qb.count()
        completed   = 0
        errored     = 0
        started_at  = datetime.datetime.now()
        
        
        
        # Create a document for each crawl item
        async for crawl_items in qb.find_in_batches(batch_size=50):
            
            try:
                crawl_item_id_to_chunk_documents = {crawl_item.id: ChunkDocument.from_html(crawl_item.body) for crawl_item in crawl_items if crawl_item.body}

                # Process in parallel using the worker pool
                jobs = [
                    ChunkDocumentJob(crawl_item_id=crawl_item_id, chunk_document=chunk_document) 
                    for crawl_item_id, chunk_document in crawl_item_id_to_chunk_documents.items()
                ]
                pool = ChunkDocumentWorkerPool(jobs=jobs, worker_count=4)
                async def on_job_complete(job: ChunkDocumentJob, status: bool, message: str | None) -> None:
                    """Callback for when a job is completed."""
                    nonlocal completed, errored
                    if status:
                        completed += 1
                        elapsed = datetime.datetime.now() - started_at
                        elapsed_seconds_total = elapsed.total_seconds()

                        # Rate should include both completed and errored per second
                        processed = completed + errored
                        per_second = processed / elapsed_seconds_total if elapsed_seconds_total > 0 else 0.0

                        elapsed_minutes = int(elapsed_seconds_total // 60)
                        elapsed_seconds = int(elapsed_seconds_total % 60)

                        message = f"⚡ {per_second:0.2f}/s 🟢 {completed} 🔴 {errored} ⏳ {elapsed_minutes:02}:{elapsed_seconds:02}"
                        await ctx.report_progress(completed, total_items, message)
                    else:
                        errored += 1
                        await ctx.log(f"Error processing ChunkDocument for CrawlItem {job.crawl_item_id}", "error")
                        
                pool.pool.on_job_done = on_job_complete
                await pool.start()
                await pool.wait_for_completion()

                # Save the batch of documents
                for job in jobs:
                    try:
                        document = await Document.from_chunking_document(job.chunk_document, corpus_id=corpus.id)
                        await document.save()
                        
                        
                    except Exception as e:
                        raise RuntimeError(f"Failed to save document for CrawlItem {job.crawl_item_id}: {e}") from e

            except Exception as e:
                print(f"Error processing batch of CrawlItems: {e}")
                await ctx.log(f"Error processing batch of CrawlItems: {e}", "error")
                errored += 1


    qb = std_corpora_query_builder(per_page=1, page=1, sort="corpora.id", order="desc")
    qb = qb.where(Corpus.id == corpus.id)
    new_corpora = await qb.all()
    new_corpus = new_corpora[0] if new_corpora else None
    if not new_corpora:
        raise ValueError(f"Corpus {corpus.id} not found after ingestion.")

    if not isinstance(new_corpus, Corpus):
        raise ValueError(f"Expected new_corpus to be a Corpus instance, got {type(new_corpus)}")

    return Payload.create(new_corpus).model_dump()

@mcp.tool(tags={"corpora", "embed", "data"})
async def embed_corpus(ctx: Context, corpus_id: int) -> Dict[str, Any]:
    """Embed all documents in a corpus."""
    async with Corpus.async_context():
        corpus = await Corpus.query().find(corpus_id)
        if not corpus:
            raise ValueError(f"Corpus with ID {corpus_id} not found.")
        
        started_at = datetime.datetime.now()
        
        async def on_save(chunks, processed, total):
            """Callback for progress reporting."""
            
            elapsed = datetime.datetime.now() - started_at
            elapsed_seconds_total = elapsed.total_seconds()
            elapsed_minutes = int(elapsed_seconds_total // 60)
            elapsed_seconds = int(elapsed_seconds_total % 60)
            elapsed_str = f"⏳ {elapsed_minutes:02}:{elapsed_seconds:02}"

            processed_str = f"🧬 {processed}/{total} Processed"

            message = f"{processed_str} | {elapsed_str}"
            await ctx.report_progress(processed, total, message)
        
        await corpus.update_embeddings(on_save=on_save)
        
        qb = std_corpora_query_builder(per_page=1, page=1, sort="corpora.id", order="desc")
        qb = qb.where(Corpus.id == corpus.id)
        new_corpora = await qb.all()
        new_corpus = new_corpora[0] if new_corpora else None

        if not new_corpus:
            raise ValueError(f"Corpus {corpus.id} not found after embedding.")

        return Payload.create(new_corpus).model_dump()




@mcp.tool(tags={"corpora", "search", "data", "rag"})
async def search_corpus(
    ctx: Context, 
    query: Annotated[str, Field(description="Query string used to find related knowledge from the base.", min_length=1, max_length=10000)]
) -> Dict[str, Any]:
    """Search the knowledge base and uses sampling to enable dynamic rag."""
    async with Corpus.async_context():
        library = await get_knowledge_base_library()

        # 2. We need to embed the query
        from openai import AsyncOpenAI
        client = AsyncOpenAI()

        response = await client.embeddings.create(
            model="text-embedding-3-small",
            input=query
        )

        if not response or not response.data or not isinstance(response.data, list):
            raise ValueError(f"Invalid response from OpenAI: {response}")

        query_embedding : List[float] = response.data[0].embedding    
        
        if not query_embedding or not isinstance(query_embedding, list):
            raise ValueError(f"Invalid embedding in response: {response.data[0]}")
        
        from pgmcp.models.chunk import Chunk
        from pgmcp.models.document import Document

        # 2.1 - idea: ask AI to consider narrowing search to a list of documents related to the user's input.
        # 3. Search the postgresql database using similarity search with pgvector
        results = []
        async with Chunk.async_context() as session:
            qb = Chunk.cosine_distance(query_embedding)

            # Scope to only those documents in the knowledge base library
            qb = qb.joins(Chunk.document, Document.corpus, Corpus.library)
            qb = qb.where(Corpus.library_id == library.id)
            
            # Limit
            qb = qb.limit(10)

            chunks = await qb.all()
            results = [chunk.model_dump_rag() for chunk in chunks]
            
            
        # 4. idea: Format / CURATE the results for use in a new RAG prompt we will construct
        # for ctx.sample

        # 4. Instructions that tells the AI how to use the response to help the user.
        instr = dedent(f"""
            THE USER ORIGINALLY ASKED THIS QUERY:
            
            ~~~~~~~~~~
            {query}
            ~~~~~~~~~~

            1. ENSURE YOU CONSIDER THE ILLOCUTIONARY FORCE OF THE QUERY ABOVE, AND EXPERTISE THEY CLEARLY ALREADY POSSESS.
            2. THIS PAYLOAD CONTAINS CHUNKS OF RELEVANT INFORMATION YOU (THE AI) WILL USE TO INFORM YOUR ANSWER OR ASSISTANCE TO THE USER.
            3. CONSIDER THIS CONTENT, AND THE PERLOCUTIONARY EFFECTS EXPECTED OF YOU, IN YOUR RESPONSE TO THIS PAYLOAD.
        """)

        payload = Payload.create(results)
        # 5. on response form the AI, we will use it to respond to the AI using this command right now
        return payload.model_dump()
