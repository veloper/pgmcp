# models/__init__.py

from contextlib import asynccontextmanager


# isort: off
from .base import Base
from .library import Library
from .corpus import Corpus
from .document import Document
from .section import Section
from .section_item import SectionItem
from .answer import Answer
from .code_block import CodeBlock
from .content import Content
from .crawl_item import CrawlItem
from .crawl_job import CrawlJob
from .crawl_log import CrawlLog
from .listing import Listing
from .listing_item import ListingItem
from .paragraph import Paragraph
from .question import Question
from .sentence import Sentence
from .table import Table
from .table_row import TableRow
from .table_row_cell import TableRowCell
# isort: on

# Alias the context manager from Base for convenience
# which is already a context manager wrapping method
@asynccontextmanager
async def context(*args, **kwargs):
    async with Base.async_context() as session:
        yield session
        

__all__ = [
    "Base",
    "Library",
    "Corpus",
    "Document",
    "Section",
    "SectionItem",
    "Answer",
    "CodeBlock",
    "Content",
    "CrawlItem",
    "CrawlJob",
    "CrawlLog",
    "Listing",
    "ListingItem",
    "Paragraph",
    "Question",
    "Sentence",
    "Table",
    "TableRow",
    "TableRowCell",
    "context"
]
