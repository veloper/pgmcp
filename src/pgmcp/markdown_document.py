from __future__ import annotations

from typing import Any, Dict, List, Self, Union

from pydantic import BaseModel, Field, PrivateAttr


class MdElement(BaseModel):
    """Base class for all markdown elements."""
    text: str = Field(..., description="The markdown content for this element")
    
    @property
    def size(self) -> int:
        """Returns the size of the markdown element."""
        return len(self.text)
    
    

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



