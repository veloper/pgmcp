import re

from abc import abstractmethod
from typing import Any, Dict, List

from blinker import Namespace
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr
from typing_extensions import Self

from pgmcp.markdown_document import MdDocument
from pgmcp.models import Corpus, CrawlItem, CrawlJob, Document, Library
from pgmcp.utils import convert_markdown_to_markdown_document


# async with CrawlItem.async_context() as async_session:
#     async with async_session.begin() as txn: 
#         # Get CrawlJob 
#         crawl_job = await CrawlJob.find(crawl_job_id)
#         if not crawl_job:
#             raise ValueError(f"CrawlJob with ID {crawl_job_id} does not exist.")
        
#         # Get CrawlItems based on curated_crawl_item_ids + CrawlJob.id
#         crawl_items = await CrawlItem.query().where(
#             CrawlItem.id.in_(curated_crawl_item_ids),
#             CrawlItem.crawl_job_id == crawl_job.id
#         ).all()
        
#         if not crawl_items:
#             raise ValueError(f"No valid CrawlItems found for the provided IDs in CrawlJob {crawl_job_id}.")
        

#         # LIBRARY
#         library = await Library.query().where(Library.name == "knowledge_base").first()
#         if not library:
#             library = Library(name="knowledge_base")
#             library = await library.save()
#             if not library:
#                 raise ValueError("Failed to create or retrieve the knowledge base library.")
        
            
#         # CORPUS
#         corpus_name = next(iter(crawl_job.start_urls), None)
#         if corpus_name is None:
#             raise ValueError(f"CrawlJob {crawl_job_id} has no start URLs to determine corpus name.")
#         corpus_name = re.sub(r'\W+', '_', corpus_name) # Replace non-alphanumeric characters with underscores
#         corpus_name = re.sub(r'__+', '_', corpus_name) # Ensure no double underscores
        
#         corpus = await Corpus.query().where(
#             Corpus.name == corpus_name,
#             Corpus.library_id == library.id
#         ).first()

#         if not corpus:
#             corpus = Corpus(name=corpus_name, library_id=library.id)
#             corpus = await corpus.save()
#             if not corpus:
#                 raise ValueError("Failed to create or retrieve the corpus.")
            
        
        
#         @dataclass(frozen=True)
#         class WorkItem:
#             crawl_item_id: int
#             crawl_item_body: str
#             crawl_item_headers: Dict[str, Any]
#             crawl_item_url: str
#             corpus_id: int
            
#             @classmethod
#             def from_corpus_and_crawl_item(cls, corpus: Corpus, crawl_item: CrawlItem) -> Self:
#                 return cls(
#                     crawl_item_id=crawl_item.id,
#                     crawl_item_body=crawl_item.body,
#                     crawl_item_headers=dict(crawl_item.response_headers or {}),
#                     crawl_item_url=crawl_item.url,
#                     corpus_id=corpus.id
#                 )
            
                
            
#             def get_markdown_document(self) -> MdDocument:
#                 """Convert the work item to a markdown document."""
#                 return MdDocument.from_str(
#                     text=self.crawl_item_body,
#                     title=self.crawl_item_headers.get("title", "Untitled Document")
#                 )
                
#         work_items = [WorkItem.from_corpus_and_crawl_item(corpus, crawl_item) for crawl_item in crawl_items]


ingestion_signals = Namespace()

# Triggers when a document has been inserted into the knowledge base.
document_ingested = ingestion_signals.signal('document_ingested')

"""
A module dedicated to adding sanity around ingestion of crawl jobs into the knowledge base library.

Flow

IngestConfig:
    - Desc: How to import information into the knowledge base library.
IngestionJob
    - Desc: A job representing the entire ingestion process of many Documents into a corpus within the Knowledge Base Library.
    - from_config(config: IngestionConfig) -> IngestionJob
    




"""

class CreateDocumentJob(BaseModel):
    """talks content, turns it into a document, saves it to its configured corpus"""
    
    model_config = ConfigDict(
        extra='forbid',
        arbitrary_types_allowed=True,
    )

    corpus_id: int = Field(..., description="The ID of the corpus to which the document will be added.")
    content: str = Field(..., description="The text content to be processed.")
    
    
    @abstractmethod
    def get_title(self) -> str:        
        """Extracts the title from the content"""
        raise NotImplementedError("Subclasses must implement this method to extract the title from content.")

    @abstractmethod
    def get_document(self) -> Document:
        """Convert the content into a Document instance."""
        raise NotImplementedError("Subclasses must implement this method to convert content into a Document.")
    

class CreateDocumentFromMdDocumentJob(CreateDocumentJob):
    
    md_document: MdDocument = Field(..., description="The markdown document to be processed and saved.")

    def get_title(self) -> str:
        """Extracts the title from the markdown document."""
        return self.md_document.title or ""

    # def get_document(self) -> Document:
        # """Convert the markdown document into a Document instance."""
        # return convert_markdown_document_to_markdown_document

    def from_markdown(cls, markdown: str, *, title: str | None, corpus_id: int | None) -> Self:
        """Create a job from a markdown string."""
        md_document = convert_markdown_to_markdown_document(markdown, title=title)
        return cls.model_validate({
            "md_document": md_document,
            "corpus_id": corpus_id,
        })

class IngestionConfig(BaseModel):
    """A class to configure, orchestrate, and manage the ingestion of crawl jobs into the knowledge base library."""
    model_config = ConfigDict(
        extra='forbid',
        arbitrary_types_allowed=True,
        json_schema_extra={
            "description": "A class to configure, orchestrate, and manage the ingestion of crawl jobs into the knowledge base library."
        }
    )

    crawl_job_id: int = Field(..., description="The ID of the crawl job to ingest.")
    curated_crawl_item_ids: List[int] = Field(default_factory=list, description="Whitelist of crawl item IDs to ingest. If empty, all items from the crawl job will be ingested.")
    
    _crawl_job: CrawlJob | None = PrivateAttr(None)
    _library: Library | None = PrivateAttr(None)
    _corpus: Corpus | None = PrivateAttr(None)
    
    
    
    @property
    async def crawl_job(self) -> CrawlJob:
        """Fetch the crawl job instance associated with the crawl_job_id."""
        if self._crawl_job is None:
            self._crawl_job = await CrawlJob.find(self.crawl_job_id)
            if not self._crawl_job:
                raise ValueError(f"CrawlJob with ID {self.crawl_job_id} does not exist.")
        return self._crawl_job
    
    @property
    async def crawl_items(self) -> List[CrawlItem]:
        """Fetch the crawl items associated with the crawl job."""
        crawl_job = await self.crawl_job
        crawl_items = await CrawlItem.query().where(
            CrawlItem.crawl_job_id == crawl_job.id
        ).all()
        
        if not crawl_items:
            raise ValueError(f"No valid CrawlItems found for CrawlJob {self.crawl_job_id}.")
        
        return crawl_items
    
    @property
    async def eligible_crawl_items(self) -> List[CrawlItem]:
        """Fetch the crawl items that are eligible for ingestion based on the various configured filters (e.g., curated_crawl_item_ids)."""
        crawl_items = await self.crawl_items
        
        if self.curated_crawl_item_ids:
            # Filter by curated crawl item IDs
            eligible_items = [item for item in crawl_items if item.id in self.curated_crawl_item_ids]
        else:
            # If no curated IDs are provided, all items are eligible
            eligible_items = crawl_items
        
        if not eligible_items:
            raise ValueError(f"No eligible CrawlItems found for the provided criteria in CrawlJob {self.crawl_job_id}.")
        
        return eligible_items
    
    @property
    async def library(self) -> 'Library':
        """Fetch or create the knowledge base library."""
        library = await Library.query().where(Library.name == "knowledge_base").first()
        if not library:
            library = Library(name="knowledge_base")
            library = await library.save()
            if not library:
                raise ValueError("Failed to create or retrieve the knowledge base library.")
        return library
    
    @property
    async def corpus_name(self) -> str:
        """Generate a corpus name based on the crawl job's start URLs."""
        crawl_job = await self.crawl_job
        corpus_name = next(iter(crawl_job.start_urls), None)
        if corpus_name is None:
            raise ValueError(f"CrawlJob {self.crawl_job_id} has no start URLs to determine corpus name.")
        corpus_name = re.sub(r'\W+', '_', corpus_name)
        corpus_name = re.sub(r'__+', '_', corpus_name)
        return corpus_name
    
    @property
    async def corpus(self) -> 'Corpus':
        """Fetch or create the corpus for the crawl job."""
        corpus_name = await self.corpus_name
        corpus = await Corpus.query().where(Corpus.name == corpus_name).first()
        if not corpus:
            corpus = Corpus(name=corpus_name)
            corpus = await corpus.save()
            if not corpus:
                raise ValueError("Failed to create or retrieve the corpus.")
        return corpus
    
            
    @classmethod
    def from_crawl_job_id(cls, crawl_job_id: int) -> Self:
        """Create an instance from a crawl job ID."""
        return cls(crawl_job_id=crawl_job_id)


