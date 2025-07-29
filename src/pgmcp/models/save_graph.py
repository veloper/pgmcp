from typing import Any, AsyncGenerator, Dict, List, Self

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession

from pgmcp.models.base import Base
from pgmcp.object_graph import ObjectGraph


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

class SaveGraph(ObjectGraph[Base]):

    def predicate(self: Self, node: Base) -> bool:
        """Only walk Base model instances."""
        return True if isinstance(node, Base) else False

    async def explore(self: Self, node: Base) -> AsyncGenerator[Base, None]:
        """First pass maps out all relationships that are loaded in the model instance.
        
        The predicate ensures we only explore Base model instances.
        """
        for name, rel in get_loaded_relationships_from_model(node).items():
            if rel is not None:
                if isinstance(rel, list):
                    for item in rel:
                        yield item
                else:
                    yield rel

    async def add_to_session_in_correct_order(self: Self, session: AsyncSession) -> None:
        print("=== Topological order for session add ===")
        async for node in self.topological_nodes():
            print(f"{type(node).__name__} id={getattr(node, 'id', None)}")
            session.add(node)

    async def refresh_in_correct_order(self: Self, session: AsyncSession) -> None:
        """Refresh all nodes in the graph in the order they were visited."""
        async for node in self.topological_nodes():
            await session.refresh(node)
