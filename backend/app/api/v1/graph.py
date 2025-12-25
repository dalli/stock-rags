"""Graph API endpoints."""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.db.neo4j import get_neo4j

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/graph", tags=["graph"])


class Entity(BaseModel):
    """Entity model."""

    id: str
    name: str
    type: str
    properties: Optional[dict] = None


class TimelineEntry(BaseModel):
    """Timeline entry model."""

    date: str
    opinion: str
    target_price: Optional[float] = None
    analyst: Optional[str] = None


class Timeline(BaseModel):
    """Timeline model."""

    ticker: str
    entries: List[TimelineEntry]


@router.get("/entities", response_model=List[Entity])
async def search_entities(
    query: str = Query(..., description="Search query for entities"),
    type: Optional[str] = Query(None, description="Filter by entity type (Company, Industry, Theme, etc.)"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
) -> List[Entity]:
    """
    Search for entities in the knowledge graph.

    Args:
        query: Search query string
        type: Optional entity type filter
        limit: Maximum number of results

    Returns:
        List of matching entities
    """
    try:
        neo4j = await get_neo4j()
        params = {"query": query, "limit": limit}

        logger.info(f"Searching entities with query: {query}, type: {type}")

        entities = []

        if type:
            # Search specific entity type
            if type == "Company":
                cypher_query = """
                CALL db.index.fulltext.queryNodes('company_search', $query)
                YIELD node, score
                WHERE node:Company
                RETURN elementId(node) as id, node.name as name, 'Company' as type,
                       {ticker: node.ticker, industry: node.industry, market: node.market} as properties
                ORDER BY score DESC
                LIMIT $limit
                """
            else:
                # Search other entity types by name
                cypher_query = f"""
                MATCH (n:{type})
                WHERE toLower(n.name) CONTAINS toLower($query)
                RETURN elementId(n) as id, n.name as name, '{type}' as type,
                       properties(n) as properties
                ORDER BY n.name
                LIMIT $limit
                """
            
            results = await neo4j.execute_query(cypher_query, params)
            for record in results:
                entity = Entity(
                    id=record.get("id", ""),
                    name=record.get("name", ""),
                    type=record.get("type", ""),
                    properties=record.get("properties"),
                )
                entities.append(entity)
        else:
            # Search across all entity types
            # First search companies using full-text index
            company_query = """
            CALL db.index.fulltext.queryNodes('company_search', $query)
            YIELD node, score
            WHERE node:Company
            RETURN elementId(node) as id, node.name as name, 'Company' as type,
                   {ticker: node.ticker, industry: node.industry, market: node.market} as properties,
                   score
            ORDER BY score DESC
            LIMIT $limit
            """
            
            company_results = await neo4j.execute_query(company_query, params)
            for record in company_results:
                entity = Entity(
                    id=record.get("id", ""),
                    name=record.get("name", ""),
                    type=record.get("type", ""),
                    properties=record.get("properties"),
                )
                entities.append(entity)
            
            # Then search other types
            if len(entities) < limit:
                other_types_query = """
                MATCH (n)
                WHERE (n:Industry OR n:Theme)
                  AND toLower(n.name) CONTAINS toLower($query)
                RETURN elementId(n) as id, n.name as name,
                       CASE 
                         WHEN n:Industry THEN 'Industry'
                         WHEN n:Theme THEN 'Theme'
                       END as type,
                       CASE 
                         WHEN n:Industry THEN {parent_industry: n.parent_industry}
                         WHEN n:Theme THEN {keywords: n.keywords, description: n.description}
                       END as properties
                ORDER BY n.name
                LIMIT $limit
                """
                
                other_results = await neo4j.execute_query(other_types_query, params)
                for record in other_results:
                    if len(entities) >= limit:
                        break
                    entity = Entity(
                        id=record.get("id", ""),
                        name=record.get("name", ""),
                        type=record.get("type", ""),
                        properties=record.get("properties"),
                    )
                    entities.append(entity)

        logger.info(f"Found {len(entities)} entities")
        return entities

    except Exception as e:
        logger.error(f"Entity search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Entity search failed: {str(e)}")


@router.get("/companies/{ticker}/timeline", response_model=Timeline)
async def get_company_timeline(ticker: str) -> Timeline:
    """
    Get investment opinion timeline for a company.

    Args:
        ticker: Company ticker symbol

    Returns:
        Timeline with opinion and target price history
    """
    try:
        neo4j = await get_neo4j()

        # Query for opinions and target prices separately, then combine
        opinion_query = """
        MATCH (c:Company {ticker: $ticker})-[:HAS_OPINION]->(o:Opinion)
        RETURN o.date as date, o.rating as opinion, null as target_price, null as analyst
        ORDER BY o.date DESC
        """
        
        target_price_query = """
        MATCH (c:Company {ticker: $ticker})-[:HAS_TARGET_PRICE]->(tp:TargetPrice)
        RETURN tp.date as date, null as opinion, tp.value as target_price, null as analyst
        ORDER BY tp.date DESC
        """

        params = {"ticker": ticker}

        logger.info(f"Fetching timeline for company: {ticker}")

        # Check if company exists
        check_query = "MATCH (c:Company {ticker: $ticker}) RETURN c.ticker as ticker LIMIT 1"
        check_result = await neo4j.execute_query(check_query, params)
        
        if not check_result:
            raise HTTPException(status_code=404, detail=f"Company with ticker '{ticker}' not found")

        # Get opinions and target prices
        opinion_results = await neo4j.execute_query(opinion_query, params)
        target_price_results = await neo4j.execute_query(target_price_query, params)

        # Combine and process entries
        all_entries = []
        seen_dates = set()

        for record in opinion_results:
            date = record.get("date")
            if date and date not in seen_dates:
                seen_dates.add(date)
                all_entries.append({
                    "date": str(date),
                    "opinion": record.get("opinion", "N/A"),
                    "target_price": None,
                    "analyst": None,
                })

        for record in target_price_results:
            date = record.get("date")
            if date:
                date_str = str(date)
                # Merge with existing entry if same date
                existing = next((e for e in all_entries if e["date"] == date_str), None)
                if existing:
                    existing["target_price"] = record.get("target_price")
                elif date_str not in seen_dates:
                    seen_dates.add(date_str)
                    all_entries.append({
                        "date": date_str,
                        "opinion": "N/A",
                        "target_price": record.get("target_price"),
                        "analyst": None,
                    })

        # Sort by date descending
        all_entries.sort(key=lambda x: x["date"], reverse=True)

        timeline_entries = [
            TimelineEntry(
                date=entry["date"],
                opinion=entry["opinion"],
                target_price=entry["target_price"],
                analyst=entry["analyst"],
            )
            for entry in all_entries
        ]

        timeline = Timeline(ticker=ticker, entries=timeline_entries)

        logger.info(f"Found {len(timeline_entries)} timeline entries for {ticker}")
        return timeline

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Timeline fetch failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Timeline fetch failed: {str(e)}")
