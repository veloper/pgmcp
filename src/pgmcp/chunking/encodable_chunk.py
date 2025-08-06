"""A chunk that has a specific tiktoken model and max_size set."""

from copy import deepcopy
from typing import Any, ClassVar, Dict

import tiktoken

from pydantic import Field

from pgmcp.chunking.chunk import Chunk


class EncodableChunk(Chunk):
    """A chunk that has a specific tiktoken model and max_size set.
    
    Manages calculations of three pools of tokens budgets:
    
        1. Max Tokens: How big the _entire serialized_ chunk is allowed to be.
        2. Overhead tokens: Metadata + JSON wrapper + Reserve tokens
        3. Effective Max Tokens: How many tokens are left for content after accounting for overhead
        
    See:
    
        +---------- Overhead Tokens ----------+
        |                                     |          
        [---Metadata---][------ Reserve ------][------------------Content------------------]
        |                                      |                                           |
        |                                      +---------- Effective Max Tokens -----------+
        |                                                                                  |                                           
        +---------------------------------Max Tokens---------------------------------------+
    """
    model_config = {
        "arbitrary_types_allowed": True
    }

    # class variables to cache encoders at the class level
    _encoders: ClassVar[Dict[str, Any]] = {}
    
    model: str = Field("cl100k_base", description="tiktoken model name for encoding.")
    max_tokens: int = Field(8191, description="Max tokens allowed for serialized chunk.")
    reserve_tokens: int = Field(0, description="Number of tokens reserved for any reason, eating content budget.")
    
    @property
    def encoder(self):
        if self.model not in self._encoders:
            self._encoders[self.model] = tiktoken.get_encoding(self.model)
        return self._encoders[self.model]
    
    # == Hard counts =============================================================================
    
    @property
    def content_token_count(self) -> int: 
        """Get the token count of the content in its raw form.
        ```text
        some content
        ```
        
        No json envelope quotes.
        """
        return len(self.encoder.encode(self.content))
    
    @property
    def meta_token_count(self) -> int: 
        """Get the token count of the metadata in its serialized form MINUS the enclosing {}.
        
        The reason we don't count the enclosing {} is because they are accounted for in the JSON envelope token count.
        
        ```text
        "heading 1": "some heading",
        ```
        """
        subtract = self.encoder.encode("{") + self.encoder.encode("}")
        return len(self.encoder.encode(self.meta.model_dump_json())) - len(subtract)

    @property
    def json_envelope_token_count(self) -> int:
        """Get the token count of the JSON envelope / wrapper of this chunk.
        
        We always count the empty meta's braces to ensure accountability for _all_ tokens, even if meta is empty.
        
        Consistency is key.
        
        ```json
        {
            "meta": {},
            "content": "",
        }
        """
        return len(self.encoder.encode(self.json_envelope))
    
    @property
    def reserve_token_count(self) -> int: 
        return self.reserve_tokens
    
    @property
    def max_token_count(self) -> int: 
        return self.max_tokens

    # == Derived counts ==========================================================================

    @property
    def overhead_token_count(self) -> int:
        """Get the token count of Meta Data + JSON wrapper + Reserve tokens."""
        return self.meta_token_count + self.json_envelope_token_count + self.reserve_token_count

    @property
    def content_max_token_count(self) -> int:
        """Get the effective max tokens count representing the total space the content can occupy."""
        return max(0, self.max_tokens - self.overhead_token_count)
    
    @property
    def content_remaining_token_count(self) -> int:
        """Get the remaining tokens available for the content to grow into."""
        return max(0, self.content_max_token_count - self.content_token_count)

    @property
    def is_overflowing(self) -> bool:
        """Check if the chunk's total token count exceeds the max tokens allowed."""
        return self.token_count > self.max_tokens

    @property
    def token_count(self) -> int:
        """Get the final form, authoritative token count of this object in its serialized form."""
        return len(self.encoder.encode(self.to_str()))

    # == Sub-Chunking Helpers ==================================================================
    
    def to_chunk(self) -> Chunk:
        """Convert to a base Chunk, stripping out model/max_tokens/reserve settings."""
        return Chunk(
            meta=deepcopy(self.meta),
            content=self.content,
            content_offset=self.content_offset,
            content_length=self.content_length
        )

    def spawn_sub_chunk(self, content: str | None = None, offset: int = 0) -> "EncodableChunk":
        """Create an empty sub-chunk with the same metadata and model/max_tokens/reserve settings."""
        content = content or ""
        return EncodableChunk(
            meta=deepcopy(self.meta),
            content=content or "",
            content_offset=offset,
            content_length=len(content),
            model=self.model,
            max_tokens=self.max_tokens,
            reserve_tokens=self.reserve_tokens
        )

    # == Constructors ============================================================================
    
    @classmethod
    def from_chunk(cls, chunk: Chunk, model: str = "cl100k_base", max_tokens: int = 8191, reserve_tokens: int = 0) -> "EncodableChunk":
        return cls(
            meta=chunk.meta,
            content=chunk.content,
            content_offset=chunk.content_offset,
            content_length=chunk.content_length,
            model=model,
            max_tokens=max_tokens,
            reserve_tokens=reserve_tokens
        )
