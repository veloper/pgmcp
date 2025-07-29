from datetime import datetime, timezone
from typing import (Any, AsyncGenerator, Callable, ClassVar, Dict, Generator, List, Literal, NoReturn, Optional,
                    Protocol, Self, cast)

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy.orm.base import PassiveFlag

from pgmcp.models.base import Base
from pgmcp.tree_walker import TreeWalker


def get_relationship_names_from_model(model: Base) -> List[str]:
    """Extracts relationship names from a SQLAlchemy model instance (idiomatic, via inspection API)."""
    state = inspect(model)
    return [rel.key for rel in state.mapper.relationships if rel.key != "id"]

def get_loaded_relationships_from_model(model: Base) -> Dict[str, Any]:
    """Extracts loaded relationship names from a SQLAlchemy model instance (idiomatic SA, no lazy loads)."""
    state = inspect(model)
    loaded = {}
    for rel in state.mapper.relationships:
        if rel.key == "id":
            continue
        # Only include if the relationship is not in state.unloaded (i.e., it is loaded)
        if rel.key not in state.unloaded:
            # Check if the attribute has been loaded without triggering a lazy load
            try:
                # Use getattr with NO_FETCH to avoid triggering lazy loads
                value = getattr(model, rel.key, None)
                # Only include if the value is not a lazy loader
                if not hasattr(value, '_sa_adapter'):
                    loaded[rel.key] = value
            except Exception:
                # If we can't access the attribute safely, skip it
                pass
    return loaded

class SaveWalker(TreeWalker[Base]):
    """Walker implementation that traverses object graphs to persist nested SA objects.
    
    This walker identifies Base model instances within a hierarchical structure that need persistence (either new or
    modified records) and adds them to the SQLModel session.
    
    Uses pre-order traversal to ensure that parent objects are added before their children which is critical for
    maintaining proper relationship integrity when persisting deeply nested object structures.
    """

    def __init__(self, session: AsyncSession, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.session : AsyncSession = session
  
    # def context(self: Self) -> AsyncSession: return self.session

    def order(self: Self) -> Literal["pre"]: return "pre"

    def predicate(self: Self, node: Base) -> bool:
        return True if isinstance(node, Base) else False

    async def extract_children(self: Self, node: Base) -> AsyncGenerator[Base, None]:
        if isinstance(node, Base):
            # ONLY Loaded Relationships
            relationships = get_loaded_relationships_from_model(node)
            
            # is this node a join-table between two or more other models?
            if len(relationships) > 1:
                # if so, we need to somehow detect and detail with this case,
                # as it will cause error if this class does not have access to
                # the foreign keys of the other models to them on itself to complete the join
                # this is a complex case, and we need to handle it carefully
                # 
                # This kind of changes a pre-order traversal to a post-order traversal dynamically,
                # as we need to ensure that the parent objects are added before their children if we just
                # so happen to come upon a join table first which leads to other independent models...
                # so how do we handle this?
                #
                # This is a common case in Rails, where join tables are used to connect multiple models,
                # and they handle it by ensuring that the parent models are added first
                # and then the join table is added last, after all the parent models are added.
                raise NotImplementedError("Join-table handling not implemented yet")
            
            for name, rel in relationships.items():
                if rel is not None:
                    if isinstance(rel, list):
                        for item in rel:
                            yield item
                    else:
                        yield rel

            # Field are explicitly NOT walked, so we don't yield them
            
    
    async def visit(self: Self, node: Base) -> None:
        # if not a join table, with multiple belongs_to relationships, add to session
        self.session.add(node)
        # elif this not relies on other relationships being added first, then we need to WAIT
        #      to save this item in the session until those relationships are added
