from contextlib import asynccontextmanager
from typing import AsyncContextManager, AsyncGenerator, Awaitable, List, Union, overload

import asyncpg

from pgmcp.ag_graph import AgGraph
from pgmcp.ag_patch import AgPatch
from pgmcp.db import AgtypeRecord, settings


class ApacheAGE:
    """An apache age repository for interacting with the apache age graph database."""

    # Remove close method; rely on lazy pool recreation in settings

    async def cypher_fetch(self, graph_name: str, cypher_query: str = "MATCH (n) RETURN n UNION ALL MATCH ()-[e]->() RETURN e") -> List[AgtypeRecord]:
        """Fetch records from a Cypher query using a server-side cursor."""
        if not graph_name:
            raise ValueError("Graph name must be provided.")
        async with settings.db.connection() as conn:
            async with conn.transaction():
                records: list[asyncpg.Record] = []
                async for record in conn.cursor(f"SELECT * from cypher('{graph_name}', $$ {cypher_query} $$) as (v agtype);"):
                    records.append(record)
                return AgtypeRecord.from_raw_records(records)

    async def cypher_execute(self, graph_name: str, cypher_query: str) -> None:
        """Execute a Cypher query on the specified graph."""
        async with settings.db.connection() as conn:
            age_query = f"SELECT * from cypher('{graph_name}', $$ {cypher_query} $$) as (v agtype);"
            await conn.execute(age_query)

    async def create_graph(self, graph_name: str) -> AgGraph:
        async with settings.db.connection() as conn:
            query = f"SELECT create_graph('{graph_name}');"
            await conn.execute(query)
            return AgGraph(name=graph_name)

    async def drop_graph(self, graph_name: str) -> None:
        if not graph_name:
            raise ValueError("Graph name must be provided.")

        async with settings.db.connection() as conn:
            query = f"SELECT drop_graph('{graph_name}', true);" # true = cascade all
            await conn.execute(query)

    async def truncate_graph(self, graph_name: str) -> None:
        """Truncate all vertices and edges in the graph."""
        if not graph_name:
            raise ValueError("Graph name must be provided.")
        await self.cypher_execute(graph_name, "MATCH (n) DETACH DELETE n")
        await self.cypher_execute(graph_name, "MATCH ()-[e]->() DELETE e")

    async def ensure_graph(self, graph_name: str) -> None:
        """Like create_graph, but does nothing if the graph already exists. """
        if not await self.graph_exists(graph_name):
            await self.create_graph(graph_name)


    async def graph_exists(self, graph_name: str) -> bool:
        if not isinstance(graph_name, str) or not graph_name:
            raise ValueError("Graph name must be a non-empty string.")
        return graph_name in await self.get_graph_names()

    async def get_graph(self, graph_name: str) -> AgGraph:
        """Get the entire graph by name."""
        if not graph_name:
            raise ValueError("Graph name must be provided.")

        records = await self.cypher_fetch(graph_name, "MATCH (v) RETURN v")
        graph = AgGraph.from_agtype_records(graph_name, records)
        return graph

    async def get_graph_names(self) -> List[str]:
        """
        Return a list of all Apache AGE graph names in the database.

        This method queries PostgreSQL for all schemas that:
          - Are not system schemas (do not start with 'pg_' and are not 'information_schema')
          - Contain an 'ag_label' table, which is created by AGE's `create_graph` and is required for a schema to function as an AGE graph

        Only schemas that meet both criteria are considered valid AGE graphs and included in the result.
        """
        async with settings.db.connection() as conn:
            query = """
                SELECT nspname
                FROM pg_catalog.pg_namespace n
                WHERE nspname NOT LIKE 'pg_%'
                  AND nspname != 'information_schema'
                  AND EXISTS ( SELECT 1 FROM pg_class c WHERE c.relnamespace = n.oid AND c.relname = 'ag_label' );
            """
            rows = await conn.fetch(query)
            return [row['nspname'] for row in rows]


    async def get_or_create_graph(self, graph_name: str) -> AgGraph:
        """Get an existing graph or create a new one if it doesn't exist."""
        await self.ensure_graph(graph_name)
        return await self.get_graph(graph_name)

    async def upsert_graph(self, new_graph : AgGraph) -> AgGraph:
        """
        Upsert a graph by applying a patch to the existing graph.

        This method is a convenience wrapper around `patch_graph` that allows you to
        upsert a graph without needing to manage the original graph explicitly.

        Additionally, it ensures that the graph exists before applying the patch.

        Args:
            new_graph (AgGraph): The new graph to upsert.

        Returns:
            AgGraph: The updated graph after applying the patch.
        """
        if not new_graph.name:
            raise ValueError("Graph name must be provided.")

        await self.ensure_graph(new_graph.name)
        original_graph = await self.get_graph(new_graph.name)

        patched_graph = await self.patch_graph(original_graph, new_graph)

        return patched_graph

        

    @overload
    def patch_graph(
        self,
        original_graph: AgGraph
    ) -> AsyncContextManager[AgGraph]: ...

    @overload
    def patch_graph(
        self,
        original_graph: AgGraph,
        new_graph: AgGraph
    ) -> Awaitable[AgGraph]: ...

    def patch_graph(
        self,
        original_graph: AgGraph,
        new_graph: AgGraph | None = None
    ) -> Union[AsyncContextManager[AgGraph], Awaitable[AgGraph]]:
        if new_graph is None:
            return self._patch_graph_cm(original_graph)
        else:
            return self._patch_graph_apply(original_graph, new_graph)

    @asynccontextmanager
    async def _patch_graph_cm(
        self,
        original_graph: AgGraph
    ) -> AsyncGenerator[AgGraph, None]:
        graph_name = original_graph.name

        async with settings.db.connection() as conn:
            async with conn.transaction():
                graph_to_patch = original_graph.deepcopy()
                yield graph_to_patch
                patch = AgPatch.from_a_to_b(original_graph, graph_to_patch)

                cypher_statements = patch.to_cypher_statements()

                cypher_sql = [f"SELECT * FROM cypher('{graph_name}', $$ {stmt} $$) AS (v agtype);" for stmt in cypher_statements]

                statements = [
                    "LOAD 'age';",
                    """SET search_path = ag_catalog, "$user", public;""",
                ] + cypher_sql

                for stmt in statements:
                    await conn.execute(stmt)

    async def _patch_graph_apply(
        self,
        original_graph: AgGraph,
        new_graph: AgGraph
    ) -> AgGraph:
        graph_name = original_graph.name
        async with settings.db.connection() as conn:
            async with conn.transaction():
                patch = AgPatch.from_a_to_b(original_graph, new_graph)

                cypher_statements = patch.to_cypher_statements()
                cypher_sql = [f"SELECT * FROM cypher('{graph_name}', $$ {stmt} $$) AS (v agtype);" for stmt in cypher_statements]

                statements = [
                    "LOAD 'age';",
                    """SET search_path = ag_catalog, "$user", public;""",
                ] + cypher_sql

                for stmt in statements:
                    await conn.execute(stmt)
        return new_graph
