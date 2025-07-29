from __future__ import annotations

import weakref

from abc import ABC, abstractmethod
from typing import (Any, AsyncGenerator, Callable, Dict, Generic, List, Literal, Mapping, Optional, Self, Sequence,
                    TypeVar)


T = TypeVar('T')

class TreeWalker(ABC, Generic[T]):
    """
    Async generic tree walker that traverses a tree-like structure and applies an async visit function to each node.

    Generic Type Variables:
        - T: The type of the node the walker was declared with.

    Arguments:
        order: Literal["pre", "post"]
            - "pre": Visit the node before visiting its children.
            - "post": Visit the node after visiting its children.
        predicate: Optional[Callable[[T], bool]]
            Used to scope what nodes will be visited during a walk operation. If None, all nodes will be visited.

    Usage Example:
        # Suppose you have a simple tree structure:
        class Node:
            def __init__(self, value, children=None):
                self.value = value
                self.children = children or []

        # To sum all values in the tree (async):
        class SumWalker(TreeWalker[Node]):
            def __init__(self):
                super().__init__(order="post")
                self.total = 0
            async def visit(self, node: Node):
                self.total += node.value
            async def extract_children(self, node: Node):
                for child in node.children:
                    yield child

        import asyncio
        root = Node(1, [Node(2), Node(3, [Node(4)])])
        walker = SumWalker()
        asyncio.run(walker.walk(root))
        print(walker.total)  # Output: 10
    """
    def __init__(
        self: Self,
        order: Literal["pre", "post"] = "post",
        predicate: Optional[Callable[[T], bool]] = None
    ) -> None:
        self._visited: weakref.WeakValueDictionary[int, T] = weakref.WeakValueDictionary()
        self._order: Literal["pre", "post"] = order
        self._predicate: Optional[Callable[[T], bool]] = predicate

    @abstractmethod
    async def visit(self: Self, node: T) -> None:
        """Override this method to implement custom visit logic."""
        raise NotImplementedError("You must implement the async visit method.")

    async def extract_children(self: Self, node: T) -> AsyncGenerator[T, None]:
        """
        Yields children of the node for custom tree structures.
        Override this in subclasses to provide additional child extraction logic.
        By default, yields nothing.
        """
        if False:
            yield  # pragma: no cover
        return

    def order(self: Self) -> Literal["pre", "post"]:
        return self._order

    def predicate(self, node: T) -> bool:
        if self._predicate:
            return self._predicate(node)
        return True  # If no predicate is set, consider all nodes as valid

    def visited(self: Self) -> List[T]:
        """Return all visited objects."""
        return list(self._visited.values())

    def _check_visited(self: Self, node: T) -> bool:
        return id(node) in self._visited

    def _check_predicate(self: Self, node: T) -> bool:
        return self.predicate(node)

    async def walk(self: Self, node: T) -> None:
        """Start walking the tree from the given node."""
        if self._check_visited(node):
            return  # Skip if already visited
        if not self._check_predicate(node):
            return  # Skip if predicate is not satisfied
        self._visited[id(node)] = node  # Mark the node as visited

        # For pre-order traversal, visit the node before visiting its children
        if self._order == "pre":
            await self.visit(node)

        # Recurse Containers
        if isinstance(node, (tuple, list, set, Sequence)):
            for child in node:
                await self.walk(child)
        elif isinstance(node, (dict, Mapping)):
            for child in node.values():
                await self.walk(child)
        else:
            async for child in self.extract_children(node):
                await self.walk(child)

        # For post-order traversal, visit the node after visiting its children
        if self._order == "post":
            await self.visit(node)
