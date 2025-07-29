import uuid

from textwrap import dedent

import pytest, pytest_asyncio

from pgmcp.markdown_document import MdDocument
from pgmcp.models.base import Base
from pgmcp.models.corpus import Corpus
from pgmcp.models.document import Document
from pgmcp.models.element import Element
from pgmcp.models.library import Library
from pgmcp.utils import convert_html_to_markdown_document, convert_markdown_to_markdown_document


@pytest.fixture
def md_title():
    return "Test Document"

@pytest.fixture
def md_text():
    """Create a complex Markdown document with various elements."""
    return dedent("""
    # Main Title

    ## Subtitle

    This is a paragraph with **bold text** and *italic text*.

    - List item 1
    - List item 2
        - Nested list item
            - Nested nested list item
            - Another nested item
            - Nested item with **bold text**
        - List item 2.1
    - List item 3
    - List item 4
    - List item 5 with [link](https://example.com)

    [Link to example](https://example.com)

    ```python
    def example_function():
        print("Hello, World!")
    ```

    > This is a blockquote.
    >
    > It can span multiple lines.

    ![Image](https://example.com/image.png)
    
    
    ### Another Subtitle
    
    This is another paragraph with a [link](https://example.com) and some more text.

    This is paragraph 2 lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed
    do eiusmod tempor incididunt ut labore et dolore magna aliqua. Lorem ipsum dolor sit 
    amet, consectetur adipiscing elit.

    and this is a paragraph 3
    
    ## Another Sub Title
    
    ```applescript
    tell application "Finder"
        activate
        display dialog "Hello, World!"
    end tell
    ```
    ### _Nested_ Lists
    
    - level 1
    - level 2
        - level 2.1
        - level 2.2
            - level 2.2.1
            - level 2.2.2
    - level 3
        - level 3.1
        - level 3.2
            - level 3.2.1
            - level 3.2.2   
    - level 4
    
    """)



@pytest.fixture
def markdown_document(md_text: str, md_title: str) -> MdDocument:
    """Create a MarkdownDocument from the provided Markdown text."""
    return convert_markdown_to_markdown_document(md_text, title=md_title)

@pytest_asyncio.fixture
async def library() -> Library:
    """Ensure the Library model is loaded."""
    
    unique_lib_name = f"Test Library {uuid.uuid4()}"
    library = Library(name=unique_lib_name, description="Test library for persistence test")
    
    await library.save()
    
    return library

@pytest_asyncio.fixture
async def corpus(library: Library) -> Corpus:
    """Ensure the Corpus model is loaded and associated with the Library."""
    
    unique_corpus_name = f"Test Corpus {uuid.uuid4()}"
    corpus = Corpus(name=unique_corpus_name, description="Test corpus for persistence test", library=library)
    
    await corpus.save()
    
    return corpus

@pytest_asyncio.fixture
async def document(markdown_document: MdDocument, corpus: Corpus) -> Document:
    async with Base.async_session() as session:
        return await Document.from_markdown_document(markdown_document, corpus_id=corpus.id)


# == Tests =========================================================

class TestMdDocumentToDocumentConversion:
    """Test converting MarkdownDocument to Document."""

    @pytest.mark.asyncio
    async def test_convert_markdown_to_document(self, markdown_document: MdDocument):
        document = await Document.from_markdown_document(markdown_document)
        assert isinstance(document, Document)
        assert document.title == markdown_document.title

    @pytest.mark.asyncio
    async def test_document_title(self, document: Document):
        assert document.title == "Test Document"
        print(repr(document.body))


    @pytest.mark.asyncio
    async def test_document_persistence_and_recall(self, document: Document):
        async with Document.async_context() as session:

            # Step 4: Save the Document and verify persistence/recall as before
            await document.save()
            doc_id = document.id
            
            doc = await Document.query().eager_load_chain(
                Document.body,
                Element.children,
                Element.children,
                Element.children,
                Element.children,
                Element.children,
                Element.children,
                Element.children,
                Element.children,
                Element.children,
                Element.children,
                Element.children,
                Element.children,
                Element.children,
                Element.children,
                Element.children,
                Element.children,
                Element.children,
                Element.children,
                Element.children,
                Element.children,
            ).find_by(id=doc_id)
            
            
            assert doc is not None
