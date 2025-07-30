from contextlib import asynccontextmanager
from typing import AsyncContextManager, AsyncGenerator, Awaitable, List, Union, overload

from sqlalchemy import text
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession

from pgmcp.ag_graph import AgGraph
from pgmcp.ag_patch import AgPatch
from pgmcp.db import AgtypeRecord
from pgmcp.settings import get_settings


dbs = get_settings().db.get_primary()

class ApacheAGE:
    """An apache age repository for interacting with the apache age graph database."""

    async def load_age_extension(self):
        async with dbs.sqlalchemy_transaction() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS age;"))
            await conn.execute(text("LOAD 'age';"))
            await conn.execute(text("SET search_path = ag_catalog, \"$user\", public;"))

    async def ensure_age_loaded(self):
        """Ensure the AGE extension is loaded and search_path is set."""
        await self.load_age_extension()

    async def create_graph(self, graph_name: str) -> AgGraph:
        await self.ensure_age_loaded()
        async with dbs.sqlalchemy_transaction() as conn:
            query = text(f"SELECT create_graph('{graph_name}');")
            await conn.execute(query)
            return AgGraph(name=graph_name)

    async def drop_graph(self, graph_name: str) -> None:
        if not graph_name:
            raise ValueError("Graph name must be provided.")
        await self.ensure_age_loaded()
        async with dbs.sqlalchemy_transaction() as conn:
            query = text(f"SELECT drop_graph('{graph_name}', true);")
            await conn.execute(query)

    async def truncate_graph(self, graph_name: str) -> None:
        """Truncate all vertices and edges in the graph."""
        if not graph_name:
            raise ValueError("Graph name must be provided.")
        async with dbs.sqlalchemy_transaction() as conn:
                await self.cypher_execute(graph_name, "MATCH (n) DETACH DELETE n")

    async def ensure_graph(self, graph_name: str) -> None:
        """Like create_graph, but does nothing if the graph already exists. """
        graph_exists = await self.graph_exists(graph_name)
        if not graph_exists:
            await self.create_graph(graph_name)


    async def graph_exists(self, graph_name: str) -> bool:
        if not isinstance(graph_name, str) or not graph_name:
            raise ValueError("Graph name must be a non-empty string.")
        
        return graph_name in await self.get_graph_names()

    async def get_graph(self, graph_name: str) -> AgGraph:
        """Get the entire graph by name."""
        if not graph_name:
            raise ValueError("Graph name must be provided.")

        records = await self.cypher_fetch(graph_name)
        graph = AgGraph.from_agtype_records(graph_name, records)
        return graph

    async def get_graph_names(self) -> list[str]:
        """Get all graph names from the AGE catalog."""
        async with dbs.sqlalchemy_transaction() as conn:
            result = await conn.execute(text("SELECT name FROM ag_catalog.ag_graph ORDER BY name;"))
            rows = result.mappings().all()
            return [row['name'] for row in rows]

    async def run_cypher(self, graph_name: str, cypher_query: str):
        async with dbs.sqlalchemy_transaction() as conn:
            result = await conn.execute(text(f"SELECT * from cypher('{graph_name}', $$ {cypher_query} $$) as (v agtype);"))
            rows = result.mappings().all()
            return rows

    async def cypher_execute(self, graph_name: str, cypher_query: str) -> None:
        await self.ensure_age_loaded()
        async with dbs.sqlalchemy_transaction() as conn:
            age_query = text(f"SELECT * from cypher('{graph_name}', $$ {cypher_query} $$) as (v agtype);")
            await conn.execute(age_query)

    async def cypher_fetch(self, graph_name: str, cypher_query: str = "MATCH (n) RETURN n UNION ALL MATCH ()-[e]->() RETURN e") -> List[AgtypeRecord]:
        await self.ensure_age_loaded()
        results: List[Row] = []
        if not graph_name:
            raise ValueError("Graph name must be provided.")
        async with dbs.sqlalchemy_transaction() as conn:
            result = await conn.execute(text(f"SELECT * from cypher('{graph_name}', $$ {cypher_query} $$) as (v agtype);"))
            for record in result:
                results.append(record)
        return AgtypeRecord.from_raw_records(results)

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

        async with dbs.sqlalchemy_transaction() as conn:
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
                await conn.execute(text(stmt))

    async def _patch_graph_apply(
        self,
        original_graph: AgGraph,
        new_graph: AgGraph
    ) -> AgGraph:
        graph_name = original_graph.name
        async with dbs.sqlalchemy_transaction() as conn:
            patch = AgPatch.from_a_to_b(original_graph, new_graph)

            # Load and setup AGE if not already done
            await conn.execute(text("LOAD 'age';"))
            await conn.execute(text("SET search_path = ag_catalog, \"$user\", public;"))

            # Convert the patch to Cypher statements
            cypher_statements = patch.to_cypher_statements()
            stmts = [f"SELECT * FROM cypher('{graph_name}', $$ {stmt} $$) AS (v agtype);" for stmt in cypher_statements]
            for stmt in stmts:
                if isinstance(stmt, str):
                    await conn.execute(text(stmt))
                else:
                    await conn.execute(stmt)
        return new_graph

    async def get_or_create_graph(self, graph_name: str) -> AgGraph:
        """Get the graph if it exists, otherwise create and return it."""
        if not graph_name:
            raise ValueError("Graph name must be provided.")
        if await self.graph_exists(graph_name):
            return await self.get_graph(graph_name)
        else:
            return await self.create_graph(graph_name)
