from __future__ import annotations

from dataclasses import dataclass
from functools import reduce
from typing import TYPE_CHECKING, Any, Callable, Generic, List, Optional, Self, Tuple, TypeVar, Union, cast

from pydantic import BaseModel, ConfigDict, Field

from pgmcp.ag_edge import AgEdge
from pgmcp.ag_entity import AgEntity
from pgmcp.ag_vertex import AgVertex
from pgmcp.lru_cache import LRUCache


if TYPE_CHECKING:
    from pgmcp.ag_graph import AgGraph  

T = TypeVar('T', bound=AgEntity, covariant=True)

class Step:
    """Base class for all query steps. Subclasses must be hashable and comparable so as to allow for caching and equality checks."""
    def apply(self, items):
        raise NotImplementedError

@dataclass(frozen=True)
class FilterStep(Step):
    attr: str
    value: Any
    def apply(self, items):
        return [item for item in items if getattr(item, self.attr) == self.value]

@dataclass(frozen=True)
class SortStep(Step):
    key: str
    reverse: bool = False
    def apply(self, items: List[T]) -> List[T]:
        return sorted(items, key=lambda item: getattr(item, self.key), reverse=self.reverse)

@dataclass(frozen=True)
class ReverseStep(Step):
    def apply(self, items):
        return list(reversed(items))

@dataclass(frozen=True)
class PropsStep(Step):
    props: Tuple[Tuple[str, Any], ...]
    def apply(self, items: List[T]) -> List[T]:
        def item_matches(item):
            for key, value in self.props:
                if item.properties.get(key, None) != value:
                    return False
            return True
        return [item for item in items if item_matches(item)]

@dataclass(frozen=True)
class LabelStep(Step):
    label: str
    def apply(self, items: List[T]) -> List[T]:
        return [item for item in items if item.label == self.label]

@dataclass(frozen=True)
class StartIdentStep(Step):
    start_ident: str
    def apply(self, items: List[T]) -> List[T]:
        return [item for item in items if item.start_ident == self.start_ident]

@dataclass(frozen=True)
class EndIdentStep(Step):
    end_ident: str
    def apply(self, items: List[T]) -> List[T]:
        return [item for item in items if item.end_ident == self.end_ident]

@dataclass(frozen=True)
class IdentStep(Step):
    ident: str
    def apply(self, items: List[T]) -> List[T]:
        return [item for item in items if item.ident == self.ident]

class AgQueryBuilder(BaseModel, Generic[T]):
    """
    Drains:
        - all() -> List[T]
        - find(ident) -> T | None
        - first() -> T | None
        - last() -> T | None
    """
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    graph: AgGraph
    steps: List[Step] = Field(default_factory=list)

    @property
    def vertex_cache(self) -> LRUCache[int, List[AgVertex]]:
        return self.graph._vertices_query_cache

    @property
    def edge_cache(self) -> LRUCache[int, List[AgEdge]]:
        return self.graph._edges_query_cache

    # ==============================
    # Steps
    # ==============================
        
    def filter(self, attr: str, value: Any)          -> Self: return self._create_step(FilterStep(attr, value))        
    def sort(self, key: str, reverse: bool = False)  -> Self: return self._create_step(SortStep(key, reverse))        
    def reverse(self)                                -> Self: return self._create_step(ReverseStep())    
    def prop(self, key: str, value: Any)             -> Self: return self._create_step(PropsStep(((key, value),)))    
    def props(self, **kwargs: Any)                   -> Self: return self._create_step(PropsStep(tuple(kwargs.items())))        
    def label(self, label: str)                      -> Self: return self._create_step(LabelStep(label))        
    def start_ident(self, start_ident: str)          -> Self: return self._create_step(StartIdentStep(start_ident))    
    def end_ident(self, end_ident: str)              -> Self: return self._create_step(EndIdentStep(end_ident))        
    def ident(self, ident: str)                      -> Self: return self._create_step(IdentStep(ident))
    
    def reset(self) -> Self:
        self.steps.clear()
        return self

    # ==============================
    # Drains
    # ==============================
    
    def all(self) -> List[T]:
        """Return all items after applying all steps."""
        return self._pre_drain(self._applied_items())
    
    def find(self, ident: str) -> Optional[T]:
        """Find a single item by its identifier."""
        for item in self.all():
            if item.ident == ident: return item
        return None
    
    def first(self) -> T | None:
        """Return the first item after applying all steps."""
        items = self._pre_drain(self._applied_items())
        return items[0] if items else None
    
    def last(self) -> T | None:
        """Return the last item after applying all steps."""
        items = self._pre_drain(self._applied_items())
        return items[-1] if items else None

    # ===============================
    # Helpers
    # ===============================

    def _is_for_edge(self) -> bool: return self.__class__.__name__ == "AgQueryBuilderEdge"
    def _is_for_vertex(self) -> bool: return self.__class__.__name__ == "AgQueryBuilderVertex"
    
    def _base_items(self) -> List[T]:
        """Return all items without applying any steps."""
        items = []
        for vertex in self.graph.vertices:
            items.append(vertex) 
        
        for edge in self.graph.edges:
            items.append(edge)
        return cast(List[T], items)
            
    def _pre_drain(self, items: List[T]) -> List[T]:
        """Pre-drain step to apply any initial transformations."""
        if self._is_for_edge():
            return [item for item in items if item.is_edge]
        elif self._is_for_vertex():
            return [item for item in items if item.is_vertex]
        else:
            raise TypeError("QueryBuilder must be for either vertices or edges.")
    
    def _applied_items(self) -> List[T]:
        """Apply all steps to the base items returning the items just before the final drain action.
        
        This is where we setup our caching mechanism.
        """
        result : List[T] = []
        cache : LRUCache = self.vertex_cache if self._is_for_vertex() else self.edge_cache
        if cache and (items := cache.get(hash(self))) is not None:
            # Cache hit
            result = items
        else:
            # Work
            items = self._base_items()
            for step in self.steps:
                items = step.apply(items)
            # Put Cache
            cache.put(hash(self), items)
            result = items
        return result

    def _create_step(self, step: Step) -> Self:
        self.steps.append(step)
        return self

    def __eq__(self, other):
        if not isinstance(other, AgQueryBuilder):
            return False
        return (self.graph.name, tuple(self.steps)) == (other.graph.name, tuple(other.steps))

    def __hash__(self):
        return hash((self.graph.name, tuple(self.steps)))

class AgQueryBuilderVertex(AgQueryBuilder[AgVertex]):
    
    @classmethod
    def from_ag_graph(cls, graph: AgGraph) -> Self:
        return cls.model_validate({"graph": graph})


class AgQueryBuilderEdge(AgQueryBuilder[AgEdge]):
    
    @classmethod
    def from_ag_graph(cls, graph: AgGraph) -> Self:
        return cls.model_validate({"graph": graph})

