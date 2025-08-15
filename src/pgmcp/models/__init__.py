# models/__init__.py

from contextlib import asynccontextmanager


# isort: off
from .base import Base
from .library import Library
from .corpus import Corpus
from .document import Document
from .answer import Answer
from .crawl_item import CrawlItem
from .crawl_job import CrawlJob
from .crawl_log import CrawlLog
from .question import Question
from .chunk import Chunk
from .embedding import Embedding
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
    "Answer",
    "CrawlItem",
    "CrawlJob",
    "CrawlLog",
    "Question",
    "Chunk",
    "Embedding",
    "context"
]



