"""
Graph Service for Knowledge Graph Operations

Handles creation and management of knowledge graph in Neo4j.
"""

import logging
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from app.db.neo4j import Neo4jClient, get_neo4j

logger = logging.getLogger(__name__)


class GraphService:
    """
    Service for building and managing knowledge graph in Neo4j.

    Handles entity and relationship creation, graph queries,
    and knowledge graph operations.
    """

    def __init__(self, neo4j_client: Optional[Neo4jClient] = None) -> None:
        self.neo4j_client = neo4j_client

    async def _get_client(self) -> Neo4jClient:
        """Get Neo4j client, initializing if needed"""
        if self.neo4j_client is None:
            self.neo4j_client = await get_neo4j()
        return self.neo4j_client

    async def create_report_node(
        self, report_id: UUID, title: str, publish_date: Optional[datetime] = None
    ) -> str:
        """
        Create Report node in knowledge graph.

        Args:
            report_id: UUID of report from PostgreSQL
            title: Report title
            publish_date: Publication date

        Returns:
            Neo4j node ID
        """
        client = await self._get_client()

        query = """
        MERGE (r:Report {report_id: $report_id})
        ON CREATE SET
            r.title = $title,
            r.publish_date = $publish_date,
            r.created_at = datetime()
        RETURN elementId(r) as node_id
        """

        params = {
            "report_id": str(report_id),
            "title": title,
            "publish_date": publish_date.isoformat() if publish_date else None,
        }

        result = await client.execute_write(query, params)
        return result[0]["node_id"] if result else None

    async def create_company_node(self, company: dict[str, Any]) -> str:
        """
        Create or merge Company node.

        Args:
            company: Company entity with name, ticker, etc.

        Returns:
            Neo4j node ID
        """
        client = await self._get_client()

        # Prepare aliases text for full-text search
        aliases = company.get("aliases", [])
        aliases_text = " ".join(aliases) if aliases else ""

        # Use ticker if available, otherwise generate one from company name
        name = company["name"]
        ticker = company.get("ticker")
        if not ticker:
            # Generate a simple ticker from company name (replace spaces with underscores)
            ticker = name.replace(" ", "_").lower()

        query = """
        MERGE (c:Company {ticker: $ticker})
        ON CREATE SET
            c.name = $name,
            c.aliases = $aliases,
            c.aliases_text = $aliases_text,
            c.industry = $industry,
            c.market = $market,
            c.created_at = datetime()
        ON MATCH SET
            c.name = COALESCE($name, c.name),
            c.industry = COALESCE($industry, c.industry),
            c.market = COALESCE($market, c.market),
            c.updated_at = datetime()
        RETURN elementId(c) as node_id, c.ticker as ticker
        """

        params = {
            "ticker": ticker,
            "name": name,
            "aliases": aliases,
            "aliases_text": aliases_text,
            "industry": company.get("industry"),
            "market": company.get("market"),
        }

        result = await client.execute_write(query, params)
        return result[0]["node_id"] if result else None

    async def create_industry_node(self, industry: dict[str, Any]) -> str:
        """Create or merge Industry node."""
        client = await self._get_client()

        query = """
        MERGE (i:Industry {name: $name})
        ON CREATE SET
            i.parent_industry = $parent_industry,
            i.created_at = datetime()
        RETURN elementId(i) as node_id
        """

        params = {
            "name": industry["name"],
            "parent_industry": industry.get("parent_industry"),
        }

        result = await client.execute_write(query, params)
        return result[0]["node_id"] if result else None

    async def create_theme_node(self, theme: dict[str, Any]) -> str:
        """Create or merge Theme node."""
        client = await self._get_client()

        query = """
        MERGE (t:Theme {name: $name})
        ON CREATE SET
            t.keywords = $keywords,
            t.description = $description,
            t.created_at = datetime()
        RETURN elementId(t) as node_id
        """

        params = {
            "name": theme["name"],
            "keywords": theme.get("keywords", []),
            "description": theme.get("description"),
        }

        result = await client.execute_write(query, params)
        return result[0]["node_id"] if result else None

    async def create_target_price_node(
        self, target_price: dict[str, Any], company_ticker: str
    ) -> Optional[str]:
        """Create TargetPrice node and link to Company."""
        client = await self._get_client()

        query = """
        MATCH (c:Company {ticker: $ticker})
        CREATE (tp:TargetPrice {
            value: $value,
            currency: $currency,
            date: $date,
            change_type: $change_type,
            previous_value: $previous_value,
            created_at: datetime()
        })
        CREATE (c)-[:HAS_TARGET_PRICE]->(tp)
        RETURN elementId(tp) as node_id
        """

        params = {
            "ticker": company_ticker,
            "value": target_price["value"],
            "currency": target_price.get("currency", "KRW"),
            "date": target_price.get("date"),
            "change_type": target_price.get("change_type"),
            "previous_value": target_price.get("previous_value"),
        }

        try:
            result = await client.execute_write(query, params)
            return result[0]["node_id"] if result else None
        except Exception as e:
            logger.warning(f"Failed to create target price for {company_ticker}: {e}")
            return None

    async def create_opinion_node(self, opinion: dict[str, Any], company_ticker: str) -> Optional[str]:
        """Create Opinion node and link to Company."""
        client = await self._get_client()

        query = """
        MATCH (c:Company {ticker: $ticker})
        CREATE (o:Opinion {
            rating: $rating,
            date: $date,
            previous_rating: $previous_rating,
            change_type: $change_type,
            created_at: datetime()
        })
        CREATE (c)-[:HAS_OPINION]->(o)
        RETURN elementId(o) as node_id
        """

        params = {
            "ticker": company_ticker,
            "rating": opinion["rating"],
            "date": opinion.get("date"),
            "previous_rating": opinion.get("previous_rating"),
            "change_type": opinion.get("change_type"),
        }

        try:
            result = await client.execute_write(query, params)
            return result[0]["node_id"] if result else None
        except Exception as e:
            logger.warning(f"Failed to create opinion for {company_ticker}: {e}")
            return None

    async def create_relationship(self, relationship: dict[str, Any]) -> bool:
        """
        Create relationship between entities.

        Args:
            relationship: Relationship with source, target, type, and properties

        Returns:
            True if successful
        """
        client = await self._get_client()

        source = relationship["source"]
        target = relationship["target"]
        rel_type = relationship["relation_type"]
        properties = relationship.get("properties", {})

        # Build query based on entity types
        source_label = source["entity_type"]
        target_label = target["entity_type"]

        # Determine identifier field
        source_id_field = "ticker" if source_label == "Company" else "name"
        target_id_field = "ticker" if target_label == "Company" else "name"

        # Handle missing tickers by using name
        source_id = source["identifier"]
        target_id = target["identifier"]

        # If identifier is empty and it's a Company, generate from name
        if source_label == "Company" and not source_id:
            source_id = source.get("name", "").replace(" ", "_").lower()
        if target_label == "Company" and not target_id:
            target_id = target.get("name", "").replace(" ", "_").lower()

        query = f"""
        MATCH (s:{source_label} {{{source_id_field}: $source_id}})
        MATCH (t:{target_label} {{{target_id_field}: $target_id}})
        MERGE (s)-[r:{rel_type}]->(t)
        SET r.confidence_score = $confidence_score,
            r.evidence = $evidence,
            r.created_at = COALESCE(r.created_at, datetime())
        """

        # Add custom properties
        for key, value in properties.items():
            query += f", r.{key} = ${key}"

        params = {
            "source_id": source_id,
            "target_id": target_id,
            "confidence_score": relationship.get("confidence_score", 1.0),
            "evidence": relationship.get("evidence"),
            **properties,
        }

        try:
            await client.execute_write(query, params)
            return True
        except Exception as e:
            logger.warning(f"Failed to create relationship {rel_type}: {e}")
            return False

    async def build_graph_from_extraction(
        self,
        report_id: UUID,
        report_title: str,
        entities: dict[str, Any],
        relationships: dict[str, Any],
        publish_date: Optional[datetime] = None,
    ) -> dict[str, int]:
        """
        Build knowledge graph from extracted entities and relationships.

        Args:
            report_id: Report UUID
            report_title: Report title
            entities: Extracted entities
            relationships: Extracted relationships
            publish_date: Report publication date

        Returns:
            Statistics of created nodes and relationships
        """
        stats = {
            "nodes_created": 0,
            "relationships_created": 0,
            "companies": 0,
            "industries": 0,
            "themes": 0,
        }

        try:
            # Create report node
            await self.create_report_node(report_id, report_title, publish_date)
            stats["nodes_created"] += 1

            # Create company nodes
            for company in entities.get("companies", []):
                await self.create_company_node(company)
                stats["nodes_created"] += 1
                stats["companies"] += 1

            # Create industry nodes
            for industry in entities.get("industries", []):
                await self.create_industry_node(industry)
                stats["nodes_created"] += 1
                stats["industries"] += 1

            # Create theme nodes
            for theme in entities.get("themes", []):
                await self.create_theme_node(theme)
                stats["nodes_created"] += 1
                stats["themes"] += 1

            # Create target prices
            for tp in entities.get("target_prices", []):
                await self.create_target_price_node(tp, tp["company_ticker"])
                stats["nodes_created"] += 1

            # Create opinions
            for opinion in entities.get("opinions", []):
                await self.create_opinion_node(opinion, opinion["company_ticker"])
                stats["nodes_created"] += 1

            # Create relationships
            for rel in relationships.get("relationships", []):
                success = await self.create_relationship(rel)
                if success:
                    stats["relationships_created"] += 1

            logger.info(f"Graph built for report {report_id}: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Failed to build graph: {e}", exc_info=True)
            raise

    async def delete_report_graph(self, report_id: UUID) -> dict[str, int]:
        """
        Delete all graph data associated with a report.

        Args:
            report_id: Report UUID

        Returns:
            Dictionary with deletion statistics
        """
        client = await self._get_client()

        stats = {
            "nodes_deleted": 0,
            "relationships_deleted": 0,
        }

        try:
            # First, count relationships connected to the Report node
            count_query = """
            MATCH (r:Report {report_id: $report_id})
            OPTIONAL MATCH (r)-[rel1]-()
            WITH count(rel1) as rel_count
            RETURN rel_count
            """
            
            count_result = await client.execute_query(count_query, {"report_id": str(report_id)})
            if count_result:
                stats["relationships_deleted"] = count_result[0].get("rel_count", 0)

            # Delete the Report node and all its relationships
            # Note: We only delete the Report node itself, not connected nodes
            # as they might be shared with other reports
            delete_query = """
            MATCH (r:Report {report_id: $report_id})
            DETACH DELETE r
            RETURN count(r) as deleted_count
            """

            result = await client.execute_write(delete_query, {"report_id": str(report_id)})
            
            if result:
                stats["nodes_deleted"] = result[0].get("deleted_count", 0)

            logger.info(f"Deleted graph data for report {report_id}: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Failed to delete graph data for report {report_id}: {e}", exc_info=True)
            # Don't raise - continue with other deletions
            return stats


# Global service instance
_graph_service: Optional[GraphService] = None


async def get_graph_service() -> GraphService:
    """Get global graph service instance."""
    global _graph_service
    if _graph_service is None:
        _graph_service = GraphService()
    return _graph_service
