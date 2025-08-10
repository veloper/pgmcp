"""Document pipeline for processing HTML/Markdown/PDF content into chunks."""

import re

from functools import cached_property
from typing import Callable, List, Self

from langchain.text_splitter import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_core.documents import Document as LangChainDocument
from pydantic import BaseModel, Field

from pgmcp.chunking.chunk import Chunk
from pgmcp.chunking.html_washing_machine import HTMLWashingMachine
from pgmcp.chunking.markdown_converter import convert_html_to_markdown
from pgmcp.chunking.slicer import Slicer
from pgmcp.chunking.text_splitter_protocol import TextSplitterProtocol


class Document(BaseModel):
    
    
    model_config = {
        "arbitrary_types_allowed": True
    }
    
    input_content: bytes = Field(..., description="Raw input content to be processed.")
    input_content_type: str = Field("text/html", description="MIME type of the input content.")

    input_content_pdf: bytes | None = Field(None, description="PDF content extracted from the input.")
    input_content_html: str | None = Field(None, description="HTML content extracted from the input.")
    input_content_markdown: str | None = Field(None, description="Markdown content extracted from the input.")

    title: str | None = Field(None, description="Title of the content, if available. Will be assigned if missing.")

    encoding: str = Field("cl100k_base", description="Token encoding for chunking.")
    max_tokens: int = Field(8191, description="Max tokens per serialized output chunk.")
    reserve_tokens: int = Field(0, description="Tokens to reserve for any reason, eating content budget.")
    primary_text_splitter: TextSplitterProtocol = Field(default_factory=lambda: MarkdownHeaderTextSplitter(headers_to_split_on=[("#" * i, f"Header {i}") for i in range(1, 7)]))
    secondary_text_splitter: TextSplitterProtocol = Field(default_factory=lambda: RecursiveCharacterTextSplitter(
        separators=["\n", " ", ""], chunk_size=400, chunk_overlap=0
    ))

    steps: List[Callable[[], List[Chunk]]] = Field(
        default_factory=list,
        description="List of processing steps to apply to the input content to get to the output content, which will then be chunked."
    )
    
    @classmethod
    def from_html(cls, html: str, **kwargs) -> Self:
        return cls.model_validate({
            "input_content": str.encode(html, encoding="utf-8"),
            "input_content_type": "text/html",
            **kwargs
        })

    @classmethod
    def from_markdown(cls, markdown: str, **kwargs) -> Self:
        return cls.model_validate({
            "input_content": str.encode(markdown, encoding="utf-8"),
            "input_content_type": "text/markdown",
            **kwargs
        })
        
    @classmethod
    def from_pdf(cls, pdf: bytes, **kwargs) -> Self:
        return cls.model_validate({
            "input_content": pdf,
            "input_content_type": "application/pdf",
            **kwargs
        })
            
    def extract_title_from_markdown(self, markdown: str) -> str | None:
        """Extract the title from Markdown content."""
        lines = markdown.splitlines()
        for line in lines:
            if line.startswith("# "):
                return line[2:].strip()
        return None
            
    def extract_title_from_html(self, html: str) -> str | None:
        """Extract the title from HTML content."""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, 'html.parser')
        title_tag = soup.title
        if title_tag and title_tag.string:
            return title_tag.string.strip()
        return None
    
    def convert_html_to_markdown(self, html: str) -> str:
        
        washing_machine = HTMLWashingMachine.create(html) \
            .with_dashes_encoded() \
            .with_tags_before_h1_removed() \
            .with_non_pre_code_tags_replaced_with_backticks() \
            .with_script_tags_removed() \
            .with_style_tags_removed() \
            .with_meta_tags_removed() \
            .with_link_tags_removed() \
            .with_anchor_tags_replaced_with_text() \
            .with_possible_buttons_removed() \
            .with_readability_applied_lxml()    
            
        clean_html = washing_machine.wash()
        
        return convert_html_to_markdown(clean_html)

    def _split_markdown_into_chunks(self) -> List[Chunk]:
        if not self.input_content_markdown:
            raise ValueError("No markdown content available for chunking.")

        # Primary splitting to get initial high quality chunks
        primary = self.primary_text_splitter.split_text(self.input_content_markdown)

        if not isinstance(primary, list) or not primary:
            # Thus, we should put the entire content into a single chunk and let the secondary splitter handle it.
            primary = [self.input_content_markdown]

        chunk_models: List[Chunk] = []
        for item in primary:
            # Normalize to content + metadata
            if isinstance(item, LangChainDocument):
                content = str(item.page_content)
                metadata = item.metadata if isinstance(item.metadata, dict) else {}
            elif isinstance(item, str):
                content = item
                metadata = {}
            else:
                raise ValueError(f"Primary text splitter returned unsupported type: {type(item)}")

            content = str(content)
            chunk_models.append(
                Chunk.model_validate(
                    {
                        "meta": metadata,
                        "content": content,
                        "content_offset": 0,
                        "content_length": len(content),
                    }
                )
            )
        return chunk_models
        
    def _step_001_assign_typed_input_content(self) -> None:
        """Assign the input content to the appropriate typed field based on the input_content_type."""
        if self.input_content_type == "text/html":
            self.input_content_html = str(self.input_content, encoding="utf-8")
        elif self.input_content_type == "application/pdf":
            self.input_content_pdf = self.input_content
        elif self.input_content_type == "text/markdown":
            self.input_content_markdown = str(self.input_content, encoding="utf-8")
        else:
            raise ValueError(f"Unsupported input content type: {self.input_content_type}")
    
    def _step_002_convert_to_markdown(self) -> None:
        if self.input_content_html:
            # Convert HTML to Markdown
            self.input_content_markdown = self.convert_html_to_markdown(self.input_content_html)
        elif self.input_content_pdf:
            # Placeholder for PDF to Markdown conversion
            self.input_content_markdown = "PDF to Markdown conversion not implemented."
        elif self.input_content_markdown:
            # Already in Markdown format
            pass
        
    def _step_003_assign_title_if_missing(self) -> None:
        if not self.title and self.input_content_html:
            if title := self.extract_title_from_html(self.input_content_html):
                # Errant newlines and spaces in title
                title = title.strip().replace("\n", " ")
                title = re.sub(r"\s\s+", " ", title)
                
                # Cut off after common seperators
                # "name of doc page | name of website" => "name of doc page"
                pattern = re.compile(r"(?P<title>.+?)(?P<cruft>\s\W\s)")
                match = pattern.match(title)
                if match and match.group("title"):
                    title = match.group("title").strip()
                else:
                    title = title.strip()
                
                self.title = title
        
        if not self.title and self.input_content_pdf:
            pass  # Not implemented yet
            
        if not self.title and self.input_content_markdown:
            self.title = self.extract_title_from_markdown(self.input_content_markdown)
            
        if not self.title:
            # Fallback title if none found
            self.title = "Untitled Document"
        
    @cached_property
    def chunks(self) -> List[Chunk]:
        """Process the input content through the pipeline and return the final chunks."""
        
        self._step_001_assign_typed_input_content()
        self._step_002_convert_to_markdown()
        self._step_003_assign_title_if_missing()
                
        chunk_models = self._split_markdown_into_chunks()
        
        # Add meta data
        for i, chunk in enumerate(chunk_models):
            chunk.meta["part_id"] = i
            chunk.meta["title"]   = self.title

        # Slicing to enforce max token limits
        slicer = Slicer.model_validate({
            "hopper": chunk_models,
            "max_tokens": self.max_tokens,
            "reserve_tokens": self.reserve_tokens,
            "encoding": self.encoding,
            "text_splitter": self.secondary_text_splitter
        })

        return slicer.process()
