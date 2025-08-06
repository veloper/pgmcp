"""Protocol for text splitters that can split text into chunks."""

from typing import List, Protocol, runtime_checkable

from langchain_core.documents import Document as LangChainDocument


@runtime_checkable
class TextSplitterProtocol(Protocol):
    """Protocol for text splitters that can split text into chunks."""
    
    def split_text(self, text: str) -> List[str] | list[LangChainDocument]:
        """Split the input text into a list of strings."""
        ...
