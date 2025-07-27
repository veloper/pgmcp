from typing import Any, Dict, List, Protocol, Self, Union, runtime_checkable

from pydantic import BaseModel, Field, model_serializer


class PayloadMetadata(BaseModel):
    """Metadata for MCP payloads."""
    message  : str | None = Field(default="", description="status message associated with the payload")
    error    : str | None = Field(default=None, description="Error message if any")
    page     : int | None = Field(default=1, description="Current page number if collection")
    per_page : int | None = Field(default=10, description="Number of items per page if collection")
    count    : int | None = Field(default=0, description="Total count of items if collection")

    @model_serializer
    def model_serialize(self) -> Dict[str, Any]:
        """Serialize the metadata to a dictionary."""
        output = {}
        
        if message   := self.message  : output["message"]  = message
        if error     := self.error    : output["error"]    = error
        if page      := self.page     : output["page"]     = page
        if per_page  := self.per_page : output["per_page"] = per_page
        
        
        output["count"] = self.count or 0
        
        return output

@runtime_checkable
class ModelDumpProtocol(Protocol):
    """Protocol for objects that can be dumped to a dictionary."""
    
    def model_dump(self) -> Dict[str, Any]:
        """Dump the object to a dictionary."""
        raise NotImplementedError("Subclasses must implement model_dump method.")

class Payload(BaseModel):
    """Generic payload structure for MCP responses."""
    metadata   : PayloadMetadata       = Field(default_factory=PayloadMetadata, description="Metadata about this payload")
    record     : Dict[str, Any]        = Field(default_factory=dict, description="Single record payload")
    collection : List[Dict[str, Any]]  = Field(default_factory=list, description="Collection of records payload")

    

    @model_serializer
    def model_serialize(self) -> Dict[str, Union[str, Dict[str, Any], List[Dict[str, Any]]]]:
        """Serialize the payload to a dictionary."""
        output = {
            "metadata": self.metadata.model_dump(),
            "record": {},
            "collection": []
        }

        if record := self.record:
            output["record"] = record

        if (collection := self.collection) and isinstance(collection, list):
            output["collection"] = self.collection

        # remove empty collections or records
        if not output["record"]:
            del output["record"]
        if not output["collection"]:
            del output["collection"]

        return output

    @classmethod
    def create(cls,
        record_or_collection: Union[ModelDumpProtocol, Dict[str, Any], List[ModelDumpProtocol], List[Dict[str, Any]]],
        message: str | None = None,
        error: str | None = None,
        page: int | None = None,
        per_page: int | None = None,
        count: int | None = None
    ) -> Self:
        """Create a new Payload instance from a record or collection."""

        meta = PayloadMetadata(
            message=message,
            error=error,
            page=page,
            per_page=per_page,
            count=count
        )

        # Convert ModelDumpProtocol(s) to dict(s) before passing to the class
        if isinstance(record_or_collection, list):
            collection = [
                item.model_dump() if isinstance(item, ModelDumpProtocol) else item
                for item in record_or_collection
            ]
            return cls.model_validate({
                "metadata": meta.model_dump(),
                "collection": collection
            })
        else:
            record = (
                record_or_collection.model_dump()
                if isinstance(record_or_collection, ModelDumpProtocol)
                else record_or_collection
            )
            return cls.model_validate({
                "metadata": meta.model_dump(),
                "record": record
            })
