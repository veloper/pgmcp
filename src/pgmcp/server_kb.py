from textwrap import dedent
from typing import Annotated, Any, Dict, List, Literal, Tuple

# Signals
from fastmcp import Client, Context, FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

import pgmcp.models as models

from pgmcp.settings import get_settings


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
# MCP Setup
# =====================================================
mcp = FastMCP(name="Knowledge Base Service", instructions=OVERVIEW)

# =====================================================
# Settings
# =====================================================
settings = get_settings()

# =====================================================
# Database Connection
# =====================================================
dbs = settings.db.get_primary()


# =====================================================
# =====================================================
# Tools
# =====================================================
# =====================================================

@mcp.tool
async def find_corpus(corpus_name: str) -> List[models.Corpus]:
    """Find a corpus_id by its name."""
    corpus = await models.Corpus.filter_by(name=corpus_name).all()
    
    


    return results
   

@mcp.tool
def ingest(corpus_id: int, document_uri: str) -> Dict[str, Any]:
    """
    Ingest a document into the KB system

    Args:
        corpus_id (int): The ID of the corpus to ingest the document into.
        document_uri (str): The URI of the document to ingest.
    Returns:
        Dict[str, Any]: A dictionary containing the normalized Document object.
    """
