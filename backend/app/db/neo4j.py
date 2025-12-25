"""Neo4j database connection and utilities."""

from typing import Any, Dict, List, Optional

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession

from app.config import get_settings

settings = get_settings()


class Neo4jClient:
    """Neo4j client for graph database operations."""

    def __init__(self) -> None:
        """Initialize Neo4j client."""
        self.driver: Optional[AsyncDriver] = None

    async def connect(self) -> None:
        """Connect to Neo4j database."""
        self.driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )

    async def close(self) -> None:
        """Close Neo4j connection."""
        if self.driver:
            await self.driver.close()

    async def execute_query(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute Cypher query."""
        if not self.driver:
            await self.connect()

        async with self.driver.session() as session:
            result = await session.run(query, parameters or {})
            return [record.data() async for record in result]

    async def execute_write(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute write query in a transaction."""
        if not self.driver:
            await self.connect()

        async def _write_tx(tx: AsyncSession) -> List[Dict[str, Any]]:
            result = await tx.run(query, parameters or {})
            return [record.data() async for record in result]

        async with self.driver.session() as session:
            return await session.execute_write(_write_tx)

    async def check_health(self) -> bool:
        """Check Neo4j connection health."""
        try:
            if not self.driver:
                await self.connect()
            async with self.driver.session() as session:
                result = await session.run("RETURN 1 AS num")
                record = await result.single()
                return record["num"] == 1
        except Exception:
            return False

    async def create_indexes(self) -> None:
        """Create required indexes."""
        indexes = [
            "CREATE INDEX company_ticker IF NOT EXISTS FOR (c:Company) ON (c.ticker)",
            "CREATE INDEX company_name IF NOT EXISTS FOR (c:Company) ON (c.name)",
            "CREATE INDEX report_date IF NOT EXISTS FOR (r:Report) ON (r.publish_date)",
            """CREATE FULLTEXT INDEX company_search IF NOT EXISTS
               FOR (c:Company) ON EACH [c.name, c.aliases_text]""",
        ]

        for index_query in indexes:
            await self.execute_write(index_query)


# Global client instance
neo4j_client = Neo4jClient()


async def get_neo4j() -> Neo4jClient:
    """Get Neo4j client instance."""
    if not neo4j_client.driver:
        await neo4j_client.connect()
    return neo4j_client
