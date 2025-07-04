from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, Iterable, Iterator, List, TypeVar

from pydantic import ConfigDict, PrivateAttr, RootModel, model_serializer, model_validator


if TYPE_CHECKING:
    from pgmcp.ag_edge import AgEdge
    from pgmcp.ag_graph import AgGraph
    from pgmcp.ag_vertex import AgVertex
    T = TypeVar("T", AgEdge, AgVertex)
else:
    T = TypeVar("T", bound=Any)

class ListRootModel(RootModel[List[T]], Generic[T]):
    """Base RootModel for ObservableList with shared logic and preserved typing."""
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    _graph: AgGraph | None = PrivateAttr(default=None)

    # ===================================================================
    # Model Serializer
    # ===================================================================
    @model_serializer
    def custom_serializer(self) -> list:
        """Custom serializer to handle the serialization of the model."""
        return list(self.root)

    # ===================================================================
    # Model Validators
    # ===================================================================
    
    @model_validator(mode="after")
    def ensure_items_have_graph(self) -> ListRootModel[T]:
        """Ensure all items in the collection have a reference to the graph if we also have a reference to it."""
        if graph := self.graph:
            for item in self.root:
                item.graph = graph
        return self

    # ===================================================================
    # Properties
    # ===================================================================

    @property
    def graph(self) -> AgGraph | None:
        """The graph this collection belongs to."""
        return self._graph
    
    @graph.setter
    def graph(self, value: AgGraph) -> None:
        """Set the graph for this collection."""
        from pgmcp.ag_graph import AgGraph
        if not isinstance(value, AgGraph):
            raise TypeError("Expected an instance of AgGraph.")
        self._graph = value

    def get_by_ident(self, ident: str) -> List[T]:
        results: List[T] = [x for x in self if getattr(x, "ident", None) == ident]
        return results

    # ===================================================================
    # Mapped Methods
    # ===================================================================

    def append(self, item: T) -> None: self.root.append(item)
    def insert(self, index: int, item: T) -> None: self.root.insert(index, item)
    def extend(self, items: Iterable[T]) -> None: self.root.extend(items)
    def remove(self, item: T) -> None: self.root.remove(item)
    def pop(self, index: int = -1) -> T: return self.root.pop(index)
    def clear(self) -> None: self.root.clear()
    def __setitem__(self, index: int, value: T) -> None: self.root[index] = value
    def __delitem__(self, index: int) -> None: del self.root[index]
    def __getitem__(self, index: int) -> T: return self.root[index]
    def __iter__(self) -> Iterator[T]: return iter(self.root)
    def __contains__(self, item: Any) -> bool: return item in self.root
    def __len__(self) -> int: return len(self.root)
