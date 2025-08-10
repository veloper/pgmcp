"""Just like a delicatessen slicer, this slices large or irregular chunks into an upper threshold of chunk size."""

from typing import List

import tiktoken

from langchain.text_splitter import RecursiveCharacterTextSplitter
from pydantic import BaseModel, Field

from pgmcp.chunking.chunk import Chunk
from pgmcp.chunking.encodable_chunk import EncodableChunk
from pgmcp.chunking.text_splitter_protocol import TextSplitterProtocol


class Slicer(BaseModel):
    """Just like a delicatessen slicer, this slices large or irregular chunks into an upper threshold of chunk size.
    
    + ----------------------- What Happens ------------------------------+
    | Hopper             | Slicer          | Processed Output            |
    |--------------------|-----------------|-----------------------------|
    |                    |                 |                             |
    
    |> 10 units of content                 |> Max 3 units per chunk
    |           |> 4 units                 |
    |           |     |> 1 units           |
    |           |     |                    |
    [==========][====][==] -> slicer(3) -> [===][===][===][=][===][=][==]
    |                    |                 |                            |
    |>---- 3 chunks ----<|                 |>-------- 7 chunks --------<|
    
    """

    model_config = {
        "arbitrary_types_allowed": True
    }

    hopper: List[Chunk] = Field(default_factory=list, description="Chunks to be sliced.")
    max_tokens: int = Field(8191, description="Max tokens per serialized output chunk.")
    encoding: str = Field("cl100k_base", description="Token encoding.")
    reserve_tokens: int = Field(0, description="Tokens to reserve for any reason, eating content budget.")
    # Base splitter provides coarse boundaries; we still enforce token ceilings per piece.
    text_splitter: TextSplitterProtocol = Field( default_factory=lambda: RecursiveCharacterTextSplitter(
            separators=["\n", " ", ""], 
            chunk_size=400, 
            chunk_overlap=0, 
        ),
        description="Text splitter for initial content partitioning."
    )
    
    def _get_token_count(self, text: str) -> int:
        """Get token count for given text using specified encoding."""
        encoder = tiktoken.get_encoding(self.encoding)
        tokens = encoder.encode(text)
        return len(tokens)

    def process(self) -> List[Chunk]:
        """Process all chunks in the hopper, slicing as needed."""
        processed_chunks: List[Chunk] = []
        for chunk in self.hopper:
            processed_chunks.extend(self.process_chunk(chunk))
        return processed_chunks
        
    def process_chunk(self, chunk: Chunk) -> List[Chunk]:
        """Stroke of the blade, slicing a single Chunk into 1 or many Chunks."""
        sub_chunks: List[Chunk] = []
        encodable_chunk = EncodableChunk.from_chunk(chunk, model=self.encoding, max_tokens=self.max_tokens, reserve_tokens=self.reserve_tokens)

        # Short-Circuit: If it already fits, return as is in a list.
        if not encodable_chunk.is_overflowing:
            return [chunk]
        
        offset = 0
        for content in self.text_splitter.split_text(chunk.content):
            new_sub_chunk = encodable_chunk.spawn_sub_chunk(content=str(content), offset=offset)
            offset += len(content if isinstance(content, str) else content.page_content)
            sub_chunks.append(new_sub_chunk.to_chunk())
            
        # final check to ensure no sub-chunk is still overflowing
        for sub_chunk in sub_chunks:
            chunk_token_count = self._get_token_count(sub_chunk.to_str())
            if chunk_token_count > self.max_tokens:
                raise ValueError("Slicer failed to properly slice chunk; sub-chunk still exceeds max tokens.")

        return sub_chunks

