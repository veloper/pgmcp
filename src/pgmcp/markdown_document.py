from __future__ import annotations

from typing import Any, AsyncGenerator, Dict, Generator, List, Self, Union

from pydantic import BaseModel, Field, PrivateAttr


MdElementTypes = Union[
    "MdElement",
    "MdTableRowCell",
    "MdTableRow",
    "MdTable",
    "MdCodeBlock",
    "MdListingItem",
    "MdListing",
    "MdSentence",
    "MdParagraph",
    "MdSection",
    "MdDocument"
    ]
class MdElement(BaseModel):
    """Base class for all markdown elements."""
    text: str = Field(..., description="The markdown content for this element")
    
    @property
    def size(self) -> int:
        """Returns the size of the markdown element."""
        return len(self.text)

    async def traverse( self, depth: int = 0, sibling_index: int = 0 ) -> AsyncGenerator[tuple[MdElementTypes, int, int], None]:
        """Async pre-order DFS traversal yielding (item, depth, sibling_index).
        
        Usage:
            ```python
            async for item, depth, sibling_index in md_element.traverse():
                print(f"Depth: {depth}, Sibling Index: {sibling_index}, Text: {item.text}")
            ```
            
        From this you should be able to reconstruct the tree keeping track of sections using a stack or similar structure.
        """
        yield self, depth, sibling_index

        def _enumerate(items):
            return enumerate(items) if items else []

        if isinstance(self, MdDocument):
            for idx, section in _enumerate(self.sections):
                async for result in section.traverse(depth + 1, idx):
                    yield result

        elif isinstance(self, MdSection):
            for idx, item in _enumerate(self.section_items):
                async for result in item.traverse(depth + 1, idx):
                    yield result

        elif isinstance(self, MdParagraph):
            for idx, sentence in _enumerate(self.sentences):
                async for result in sentence.traverse(depth + 1, idx):
                    yield result

        elif isinstance(self, MdListing):
            for idx, item in _enumerate(self.listing_items):
                async for result in item.traverse(depth + 1, idx):
                    yield result

        elif isinstance(self, MdTable):
            for idx, row in _enumerate(self.table_rows):
                async for result in row.traverse(depth + 1, idx):
                    yield result

        elif isinstance(self, MdTableRow):
            for idx, cell in _enumerate(self.cells):
                async for result in cell.traverse(depth + 1, idx):
                    yield result
        # Leaf nodes (MdTableRowCell, MdCodeBlock, MdListingItem, MdSentence) have no children
    

class MdTableRowCell(MdElement):
    """Represents a cell in a markdown table row."""
    
    # Additional metadata can be added here if needed
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata associated with the cell")

class MdTableRow(MdElement):
    """Represents a row in a markdown table."""
    
    # List of cells in the row
    cells: List[MdTableRowCell] = Field(default_factory=list, description="List of cell objects in the row")

class MdTable(MdElement):
    """Represents a table in a markdown document."""
    table_rows: List[MdTableRow] = Field(default_factory=list, description="List of rows in the table")

class MdCodeBlock(MdElement):
    """Represents a code block in a markdown document."""
    delimiter : str = Field(..., description="The delimiter used for the code block")
    language_id: str | None = Field(..., description="The programming language of the code block")

class MdListingItem(MdElement):
    """Represents an item in a markdown list."""

class MdListing(MdElement):
    """Represents a list in a markdown document."""
    listing_items: List[Union[MdListingItem, MdListing]] = Field(default_factory=list, description="List of items in the list, can be ListingItem or nested Listing")
    ordered: bool = Field(default=False, description="True if the list is ordered, False if unordered")

class MdSentence(MdElement):
    """Represents a sentence in a markdown document."""

class MdParagraph(MdElement):
    """Represents a paragraph in a markdown document."""
    sentences: List[MdSentence] = Field(default_factory=list, description="List of sentence objects in the paragraph")

class MdSection(MdElement):
    """Represents a 'section' in a markdown document as delineated by headings.
    
    text is all but the heading text.
    """
    level: int = Field(..., description="The heading level of the section (e.g., 1 for H1, 2 for H2)")
    title: str = Field(..., description="The title of the section")
    section_items: List[Union[MdParagraph, MdListing, MdTable, MdCodeBlock, Self]] = Field(default_factory=list, description="List of items in the section, including nested subsections")



class MdDocument(MdElement):
    """Represents a markdown document as a nested tree structure."""

    sections: List[MdSection] = Field(default_factory=list, description="List of sections parsed from the markdown content nested and recursive")
    title: str | None = Field(None, description="The optional title of the markdown document")

    @classmethod
    def from_str(cls, text: str, title: str | None = None) -> Self:
        """Parses the markdown document using the new MarkdownParser."""
        # Import here to avoid circular dependency
        from pgmcp.markdown_parser import MarkdownParser
        parser = MarkdownParser()
        return parser.parse(text, cls, title=title)



