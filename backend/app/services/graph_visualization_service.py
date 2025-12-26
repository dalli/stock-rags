"""
Graph Visualization Service for Knowledge Graph Visualization Data

Handles generation and storage of visualization data for knowledge graphs.
Includes entity storage in PostgreSQL and relationship aggregation from Neo4j.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.neo4j import Neo4jClient, get_neo4j
from app.db.postgres import Entity

logger = logging.getLogger(__name__)


class GraphNodeInfo:
    """그래프 노드 정보"""

    def __init__(
        self,
        id: str,
        label: str,
        type: str,
        properties: Dict[str, Any] = None,
    ):
        self.id = id
        self.label = label
        self.type = type
        self.properties = properties or {}

    def to_dict(self) -> dict:
        """Pydantic 호환 딕셔너리로 변환"""
        return {
            "id": self.id,
            "label": self.label,
            "type": self.type,
            "properties": self.properties,
        }


class GraphRelationshipInfo:
    """그래프 관계 정보"""

    def __init__(
        self,
        source_id: str,
        source_type: str,
        source_label: str,
        target_id: str,
        target_type: str,
        target_label: str,
        relationship_type: str,
        properties: Dict[str, Any] = None,
    ):
        self.source_id = source_id
        self.source_type = source_type
        self.source_label = source_label
        self.target_id = target_id
        self.target_type = target_type
        self.target_label = target_label
        self.relationship_type = relationship_type
        self.properties = properties or {}

    def to_dict(self) -> dict:
        """Pydantic 호환 딕셔너리로 변환"""
        return {
            "source_id": self.source_id,
            "source_type": self.source_type,
            "source_label": self.source_label,
            "target_id": self.target_id,
            "target_type": self.target_type,
            "target_label": self.target_label,
            "relationship_type": self.relationship_type,
            "properties": self.properties,
        }


class NodeAggregator:
    """
    Neo4j 쿼리 결과에서 고유 노드 추출 및 관계 집계

    역할:
    - 여러 쿼리 결과를 병합
    - 같은 노드의 중복 제거
    - 같은 관계의 중복 제거
    - 최종 노드/관계 리스트 생성
    """

    def __init__(self):
        self.nodes: Dict[str, GraphNodeInfo] = {}  # key: "Type:ID"
        self.relationships: List[GraphRelationshipInfo] = []

    def add_relationship(self, rel: dict) -> None:
        """관계 정보를 추가하면서 노드 자동 등록"""
        try:
            # 소스 노드 등록 (중복 제거)
            source_key = f"{rel['source_type']}:{rel['source_id']}"
            if source_key not in self.nodes:
                self.nodes[source_key] = GraphNodeInfo(
                    id=rel["source_id"],
                    label=rel["source_label"],
                    type=rel["source_type"],
                    properties={},
                )

            # 타겟 노드 등록 (중복 제거)
            target_key = f"{rel['target_type']}:{rel['target_id']}"
            if target_key not in self.nodes:
                self.nodes[target_key] = GraphNodeInfo(
                    id=rel["target_id"],
                    label=rel["target_label"],
                    type=rel["target_type"],
                    properties=rel.get("rel_properties", {}),
                )

            # 관계 추가 (중복 제거)
            if not self._relationship_exists(rel):
                relationship = GraphRelationshipInfo(
                    source_id=rel["source_id"],
                    source_type=rel["source_type"],
                    source_label=rel["source_label"],
                    target_id=rel["target_id"],
                    target_type=rel["target_type"],
                    target_label=rel["target_label"],
                    relationship_type=rel["relationship_type"],
                    properties=rel.get("rel_properties", {}),
                )
                self.relationships.append(relationship)

        except KeyError as e:
            logger.warning(f"Missing key in relationship: {e}, rel: {rel}")

    def _relationship_exists(self, rel: dict) -> bool:
        """이미 존재하는 관계인지 확인"""
        return any(
            r.source_id == rel["source_id"]
            and r.target_id == rel["target_id"]
            and r.relationship_type == rel["relationship_type"]
            for r in self.relationships
        )

    def get_aggregated_data(self) -> dict:
        """집계된 데이터 반환"""
        counts_by_type = {}
        for node in self.nodes.values():
            counts_by_type[node.type] = counts_by_type.get(node.type, 0) + 1

        return {
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "relationships": [rel.to_dict() for rel in self.relationships],
            "stats": {
                "node_count": len(self.nodes),
                "relationship_count": len(self.relationships),
                "node_types": counts_by_type,
            },
        }


class GraphVisualizationService:
    """
    그래프 시각화 데이터 생성 및 저장 서비스

    역할:
    1. PostgreSQL에서 엔티티 추출
    2. Neo4j에서 관계 조회 (병렬)
    3. 노드 중복 제거 및 집계
    4. 시각화용 메타데이터 생성
    """

    def __init__(self, neo4j_client: Optional[Neo4jClient] = None) -> None:
        self.neo4j_client = neo4j_client

    async def _get_neo4j_client(self) -> Neo4jClient:
        """Get Neo4j client, initializing if needed"""
        if self.neo4j_client is None:
            self.neo4j_client = await get_neo4j()
        return self.neo4j_client

    async def save_entities_to_postgres(
        self, report_id: UUID, entities: dict[str, Any], db: AsyncSession
    ) -> dict[str, int]:
        """
        추출된 엔티티를 PostgreSQL에 저장

        Args:
            report_id: 리포트 ID
            entities: 추출된 엔티티 (from ExtractionService)
            db: AsyncSession

        Returns:
            저장된 엔티티 수
        """
        stats = {"companies": 0, "industries": 0, "themes": 0, "total": 0}

        try:
            # Companies 저장
            for company in entities.get("companies", []):
                entity = Entity(
                    id=uuid4(),
                    report_id=report_id,
                    entity_type="Company",
                    name=company.get("name", ""),
                    normalized_name=company.get("name", "").lower(),
                    properties={
                        "ticker": company.get("ticker"),
                        "industry": company.get("industry"),
                        "market": company.get("market"),
                        "aliases": company.get("aliases", []),
                    },
                    confidence_score=company.get("confidence_score", 1.0),
                    neo4j_node_id="",
                )
                db.add(entity)
                stats["companies"] += 1

            # Industries 저장
            for industry in entities.get("industries", []):
                entity = Entity(
                    id=uuid4(),
                    report_id=report_id,
                    entity_type="Industry",
                    name=industry.get("name", ""),
                    normalized_name=industry.get("name", "").lower(),
                    properties={"parent_industry": industry.get("parent_industry")},
                    confidence_score=industry.get("confidence_score", 1.0),
                    neo4j_node_id="",
                )
                db.add(entity)
                stats["industries"] += 1

            # Themes 저장
            for theme in entities.get("themes", []):
                entity = Entity(
                    id=uuid4(),
                    report_id=report_id,
                    entity_type="Theme",
                    name=theme.get("name", ""),
                    normalized_name=theme.get("name", "").lower(),
                    properties={
                        "keywords": theme.get("keywords", []),
                        "description": theme.get("description"),
                    },
                    confidence_score=theme.get("confidence_score", 1.0),
                    neo4j_node_id="",
                )
                db.add(entity)
                stats["themes"] += 1

            # 커밋
            await db.commit()
            stats["total"] = (
                stats["companies"] + stats["industries"] + stats["themes"]
            )
            logger.info(f"Saved entities to PostgreSQL: {stats}")

            return stats

        except Exception as e:
            logger.error(f"Failed to save entities to PostgreSQL: {e}", exc_info=True)
            await db.rollback()
            raise

    async def query_graph_relationships(
        self,
        company_tickers: set[str],
        industry_names: set[str],
        theme_names: set[str],
        limit: int = 500,
    ) -> list[dict]:
        """
        Neo4j에서 관계 조회 (3개 쿼리 병렬)

        Args:
            company_tickers: 회사 tickers
            industry_names: 산업 이름들
            theme_names: 테마 이름들
            limit: 관계 조회 제한

        Returns:
            관계 정보 리스트
        """
        client = await self._get_neo4j_client()
        tasks = []

        # Query A: Company 관계
        if company_tickers:
            company_query = """
            MATCH (c:Company)
            WHERE c.ticker IN $tickers
            MATCH (c)-[rel]-(connected)
            RETURN
                c.ticker as source_id,
                'Company' as source_type,
                c.name as source_label,
                type(rel) as relationship_type,
                CASE
                    WHEN connected:Company THEN connected.ticker
                    WHEN connected:Industry THEN connected.name
                    WHEN connected:Theme THEN connected.name
                    WHEN connected:TargetPrice THEN 'TP_' + elementId(connected)
                    WHEN connected:Opinion THEN 'OP_' + elementId(connected)
                    ELSE ID(connected)
                END as target_id,
                head(labels(connected)) as target_type,
                CASE
                    WHEN connected:Company THEN connected.name
                    WHEN connected:Industry THEN connected.name
                    WHEN connected:Theme THEN connected.name
                    WHEN connected:TargetPrice THEN 'Target: ' + toString(connected.value) + ' ' + COALESCE(connected.currency, 'KRW')
                    WHEN connected:Opinion THEN 'Opinion: ' + COALESCE(connected.rating, 'N/A')
                    ELSE toString(properties(connected))
                END as target_label,
                properties(rel) as rel_properties
            LIMIT $limit
            """
            tasks.append(
                client.execute_query(
                    company_query,
                    {"tickers": list(company_tickers), "limit": limit},
                )
            )

        # Query B: Industry 관계
        if industry_names:
            industry_query = """
            MATCH (i:Industry)
            WHERE i.name IN $names
            MATCH (i)-[rel]-(connected)
            RETURN
                i.name as source_id,
                'Industry' as source_type,
                i.name as source_label,
                type(rel) as relationship_type,
                CASE
                    WHEN connected:Company THEN connected.ticker
                    WHEN connected:Industry THEN connected.name
                    WHEN connected:Theme THEN connected.name
                    ELSE ID(connected)
                END as target_id,
                head(labels(connected)) as target_type,
                CASE
                    WHEN connected:Company THEN connected.name
                    WHEN connected:Industry THEN connected.name
                    WHEN connected:Theme THEN connected.name
                    ELSE toString(properties(connected))
                END as target_label,
                properties(rel) as rel_properties
            LIMIT $limit
            """
            tasks.append(
                client.execute_query(
                    industry_query,
                    {"names": list(industry_names), "limit": limit},
                )
            )

        # Query C: Theme 관계
        if theme_names:
            theme_query = """
            MATCH (t:Theme)
            WHERE t.name IN $names
            MATCH (t)-[rel]-(connected)
            RETURN
                t.name as source_id,
                'Theme' as source_type,
                t.name as source_label,
                type(rel) as relationship_type,
                CASE
                    WHEN connected:Company THEN connected.ticker
                    WHEN connected:Industry THEN connected.name
                    WHEN connected:Theme THEN connected.name
                    ELSE ID(connected)
                END as target_id,
                head(labels(connected)) as target_type,
                CASE
                    WHEN connected:Company THEN connected.name
                    WHEN connected:Industry THEN connected.name
                    WHEN connected:Theme THEN connected.name
                    ELSE toString(properties(connected))
                END as target_label,
                properties(rel) as rel_properties
            LIMIT $limit
            """
            tasks.append(
                client.execute_query(
                    theme_query,
                    {"names": list(theme_names), "limit": limit},
                )
            )

        # 병렬 실행
        if not tasks:
            return []

        logger.info(
            f"Executing {len(tasks)} Neo4j queries in parallel "
            f"(companies={len(company_tickers)}, industries={len(industry_names)}, themes={len(theme_names)})"
        )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 결과 합치기
        all_relationships = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Query {i} failed: {result}")
                continue
            all_relationships.extend(result)

        logger.info(f"Retrieved {len(all_relationships)} relationships from Neo4j")

        return all_relationships

    async def generate_visualization_data(
        self,
        report_id: UUID,
        entities: dict[str, Any],
        db: AsyncSession = None,
    ) -> dict[str, Any]:
        """
        리포트의 시각화 데이터 생성

        Args:
            report_id: 리포트 ID
            entities: 추출된 엔티티 (from ExtractionService)
            db: AsyncSession (PostgreSQL 저장용)

        Returns:
            {
                'nodes': [...],
                'relationships': [...],
                'stats': {...}
            }
        """
        logger.info(f"Generating visualization data for report {report_id}")

        # Step 1: 엔티티 식별자 추출
        company_tickers = set()
        industry_names = set()
        theme_names = set()

        for company in entities.get("companies", []):
            ticker = company.get("ticker") or company.get("name", "").replace(" ", "_").lower()
            company_tickers.add(ticker)

        for industry in entities.get("industries", []):
            industry_names.add(industry.get("name", ""))

        for theme in entities.get("themes", []):
            theme_names.add(theme.get("name", ""))

        logger.info(
            f"Extracted identifiers: "
            f"companies={len(company_tickers)}, "
            f"industries={len(industry_names)}, "
            f"themes={len(theme_names)}"
        )

        # Step 2: PostgreSQL에 엔티티 저장
        if db:
            try:
                entity_stats = await self.save_entities_to_postgres(
                    report_id=report_id, entities=entities, db=db
                )
                logger.info(f"Saved entities to PostgreSQL: {entity_stats}")
            except Exception as e:
                logger.error(f"Failed to save entities to PostgreSQL: {e}")
                if db:
                    await db.rollback()
                # 계속 진행 - Entity 저장 실패는 visualization 생성을 막지 않음

        # Step 3: Neo4j에서 관계 조회
        relationships = await self.query_graph_relationships(
            company_tickers=company_tickers,
            industry_names=industry_names,
            theme_names=theme_names,
            limit=500,
        )

        # Step 4: 노드 중복 제거 및 집계
        aggregator = NodeAggregator()
        for rel in relationships:
            aggregator.add_relationship(rel)

        # Step 5: 데이터 반환
        visualization_data = aggregator.get_aggregated_data()

        logger.info(
            f"Generated visualization data: "
            f"nodes={visualization_data['stats']['node_count']}, "
            f"relationships={visualization_data['stats']['relationship_count']}"
        )

        return visualization_data


# Global service instance
_visualization_service: Optional[GraphVisualizationService] = None


async def get_graph_visualization_service() -> GraphVisualizationService:
    """Get global graph visualization service instance."""
    global _visualization_service
    if _visualization_service is None:
        _visualization_service = GraphVisualizationService()
    return _visualization_service
