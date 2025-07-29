from typing import Any, AsyncGenerator, Callable, Dict, Generic, List, Optional, Self, Sequence, Set, TypeVar

import networkx as nx


T = TypeVar('T')

class ObjectGraph(Generic[T]):
    """
    Async-compatible, extensible object graph for dependency resolution and ordered visitation.
    - Subclass and override `explore(self, node)` to yield associations/dependencies for each node.
    - Call `build_graph(root)` to construct the internal dependency graph from a root object.
    - Provides named async iterators for various traversal orders (topological, reverse, leaves, roots, etc).

    Extensions:
    - Override `explore(self, node)` for custom association logic (like extract_children in a walker)
    - Override or supply custom `predicate` for node filtering
    - Override or supply custom visit logic via the `visit` method

    Usage Example:

        class MyGraph(ObjectGraph[MyNodeType]):
            async def explore(self, node):
                # yield associations/dependencies for this node
                ...

        graph = MyGraph()
        await graph.build_graph(root_node)
        
        # or
        graph = await MyGraph.build(root_node)

        async for node in graph.iter_topological():
            ...
    """
    def predicate(self, node: T) -> bool:
        """Override in subclasses to filter which nodes are included in the graph."""
        return True

    def __init__(self) -> None:
        self.graph = nx.DiGraph()
        self._visited: Set[int] = set()
        self._node_map: Dict[int, T] = {}

    @classmethod
    async def build(cls, root: T) -> Self:
        """Async factory method to build the object graph from a root object."""
        instance = cls()
        await instance.build_graph(root)
        return instance

    async def build_graph(self, root: T) -> None:
        """Async build the dependency graph from the root object."""
        await self._build_node(root)

    async def _build_node(self, node: T) -> None:
        if id(node) in self._visited:
            return
        if not self.predicate(node):
            return
        self._visited.add(id(node))
        self._node_map[id(node)] = node
        self.graph.add_node(node)
        async for dep in self.explore(node):
            self.graph.add_node(dep)
            self.graph.add_edge(node, dep)
            await self._build_node(dep)

    async def explore(self, node: T) -> AsyncGenerator[T, None]:
        """Override in subclasses to yield associations/dependencies for a node."""
        if False:
            yield  # pragma: no cover
        return

    async def topological_nodes(self) -> AsyncGenerator[T, None]:
        """Yield nodes in topological (dependency-respecting) order."""
        for node in nx.topological_sort(self.graph):
            yield node

    async def reverse_topological_nodes(self) -> AsyncGenerator[T, None]:
        """Yield nodes in reverse topological order (dependents before dependencies)."""
        for node in reversed(list(nx.topological_sort(self.graph))):
            yield node

    async def leaves_nodes(self) -> AsyncGenerator[T, None]:
        """Yield nodes with no outgoing edges (leaves)."""
        for node in self.graph.nodes:
            if self.graph.out_degree(node) == 0:
                yield node

    async def roots_nodes(self) -> AsyncGenerator[T, None]:
        """Yield nodes with no incoming edges (roots)."""
        for node in self.graph.nodes:
            if self.graph.in_degree(node) == 0:
                yield node
