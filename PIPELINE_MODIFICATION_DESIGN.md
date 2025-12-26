# 파이프라인 수정 설계 - 그래프 시각화 데이터 저장

## 📊 현재 파이프라인 구조

```
process_report_task (Celery)
  ├─ Step 1: 파일 파싱 (PDF Parser)
  ├─ Step 2: 엔티티 추출 (ExtractionService)
  ├─ Step 3: 관계 추출 (ExtractionService)
  ├─ Step 4: 그래프 빌딩 (GraphService.build_graph_from_extraction)
  │   └─ Neo4j에 노드/관계 저장만 함
  ├─ Step 5: 벡터 임베딩 (VectorService.store_document)
  └─ Step 6: 메타데이터 업데이트 (PostgreSQL)
```

**문제점:** 그래프 시각화 데이터가 저장되지 않음
- PostgreSQL Entity 테이블이 있지만 채워지지 않음
- Neo4j의 노드/관계 정보를 조회할 때마다 쿼리 실행
- 시각화용 데이터 캐시 없음

---

## 🎯 수정 목표

파이프라인의 "그래프 빌딩" 단계 후에 다음을 추가:

```
Step 4.5: 그래프 시각화 데이터 생성 및 저장
  ├─ PostgreSQL Entity 테이블에 엔티티 저장
  ├─ Neo4j에서 관계 조회 및 집계
  ├─ 시각화용 메타데이터 생성
  └─ Report의 visualization_data 필드 업데이트
```

---

## 🔄 수정된 파이프라인

```
process_report_task (Celery)
  ├─ Step 1: 파일 파싱
  ├─ Step 2: 엔티티 추출
  ├─ Step 3: 관계 추출
  ├─ Step 4: 그래프 빌딩
  │   ├─ Neo4j 노드 생성
  │   └─ Neo4j 관계 생성
  ├─ Step 4.5: 그래프 시각화 데이터 생성 ✨ [신규]
  │   ├─ PostgreSQL Entity 엔티티 저장
  │   ├─ Neo4j 관계 조회 (병렬)
  │   ├─ NodeAggregator로 중복 제거
  │   └─ Report.visualization_cached = true 설정
  ├─ Step 5: 벡터 임베딩
  └─ Step 6: 메타데이터 업데이트
```

---

## 📁 수정할 파일 목록

### 1. `backend/app/services/graph_service.py` (수정)
   - 메서드 추가: `generate_visualization_data()`
   - 메서드 추가: `save_entities_to_postgres()`
   - 메서드 추가: `query_graph_relationships()`
   - 클래스 추가: `NodeAggregator`

### 2. `backend/app/workers/tasks/process_report.py` (수정)
   - Step 4.5 추가: 시각화 데이터 생성 및 저장
   - 에러 처리 개선

### 3. `backend/app/db/postgres.py` (수정 - 존재 확인)
   - Report 모델에 `visualization_cached` 필드 추가 (선택)
   - Entity 모델 확인

---

## 💻 구현 세부 내용

### 1. GraphService 확장

#### 1.1 NodeAggregator 클래스 추가

```python
class NodeAggregator:
    """Neo4j 쿼리 결과에서 고유 노드 추출 및 관계 집계"""

    def __init__(self):
        self.nodes: Dict[str, GraphNodeInfo] = {}  # key: "Type:ID"
        self.relationships: List[GraphRelationshipInfo] = []

    def add_relationship(self, rel: dict) -> None:
        """관계 정보를 추가하면서 노드 자동 등록"""
        # 소스 노드 등록
        source_key = f"{rel['source_type']}:{rel['source_id']}"
        if source_key not in self.nodes:
            self.nodes[source_key] = GraphNodeInfo(
                id=rel['source_id'],
                label=rel['source_label'],
                type=rel['source_type'],
                properties={}
            )

        # 타겟 노드 등록
        target_key = f"{rel['target_type']}:{rel['target_id']}"
        if target_key not in self.nodes:
            self.nodes[target_key] = GraphNodeInfo(
                id=rel['target_id'],
                label=rel['target_label'],
                type=rel['target_type'],
                properties=rel.get('rel_properties', {})
            )

        # 관계 추가 (중복 제거)
        if not self._relationship_exists(rel):
            relationship = GraphRelationshipInfo(
                source_id=rel['source_id'],
                source_type=rel['source_type'],
                source_label=rel['source_label'],
                target_id=rel['target_id'],
                target_type=rel['target_type'],
                target_label=rel['target_label'],
                relationship_type=rel['relationship_type'],
                properties=rel.get('rel_properties', {})
            )
            self.relationships.append(relationship)

    def _relationship_exists(self, rel: dict) -> bool:
        """이미 존재하는 관계인지 확인"""
        return any(
            r.source_id == rel['source_id']
            and r.target_id == rel['target_id']
            and r.relationship_type == rel['relationship_type']
            for r in self.relationships
        )

    def get_aggregated_data(self) -> dict:
        """집계된 데이터 반환"""
        counts_by_type = {}
        for node in self.nodes.values():
            counts_by_type[node.type] = counts_by_type.get(node.type, 0) + 1

        return {
            'nodes': list(self.nodes.values()),
            'relationships': self.relationships,
            'stats': {
                'node_count': len(self.nodes),
                'relationship_count': len(self.relationships),
                'node_types': counts_by_type
            }
        }
```

#### 1.2 그래프 관계 조회 메서드

```python
async def query_graph_relationships(
    self,
    company_tickers: set[str],
    industry_names: set[str],
    theme_names: set[str],
    limit: int = 500
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
    import asyncio

    client = await self._get_client()
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
                WHEN connected:TargetPrice THEN 'Target: ' + toString(connected.value)
                WHEN connected:Opinion THEN 'Opinion: ' + COALESCE(connected.rating, 'N/A')
                ELSE toString(properties(connected))
            END as target_label,
            properties(rel) as rel_properties
        LIMIT $limit
        """
        tasks.append(
            client.execute_query(
                company_query,
                {"tickers": list(company_tickers), "limit": limit}
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
                {"names": list(industry_names), "limit": limit}
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
                {"names": list(theme_names), "limit": limit}
            )
        )

    # 병렬 실행
    if not tasks:
        return []

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 결과 합치기
    all_relationships = []
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Query failed: {result}")
            continue
        all_relationships.extend(result)

    return all_relationships
```

#### 1.3 시각화 데이터 생성 메서드

```python
async def generate_visualization_data(
    self,
    report_id: UUID,
    entities: dict[str, Any],
    db: AsyncSession = None
) -> dict[str, Any]:
    """
    리포트의 시각화 데이터 생성

    Args:
        report_id: 리포트 ID
        entities: 추출된 엔티티 (from PostgreSQL)
        db: AsyncSession (PostgreSQL 저장용)

    Returns:
        {
            'nodes': [...],
            'relationships': [...],
            'stats': {...}
        }
    """
    # Step 1: 엔티티 식별자 추출
    company_tickers = set()
    industry_names = set()
    theme_names = set()

    for company in entities.get("companies", []):
        ticker = company.get("ticker") or company.get("name").replace(" ", "_").lower()
        company_tickers.add(ticker)

    for industry in entities.get("industries", []):
        industry_names.add(industry["name"])

    for theme in entities.get("themes", []):
        theme_names.add(theme["name"])

    logger.info(
        f"Extracting visualization data: "
        f"companies={len(company_tickers)}, "
        f"industries={len(industry_names)}, "
        f"themes={len(theme_names)}"
    )

    # Step 2: PostgreSQL에 엔티티 저장
    if db:
        await self.save_entities_to_postgres(
            report_id=report_id,
            entities=entities,
            db=db
        )

    # Step 3: Neo4j에서 관계 조회
    relationships = await self.query_graph_relationships(
        company_tickers=company_tickers,
        industry_names=industry_names,
        theme_names=theme_names,
        limit=500
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
```

#### 1.4 PostgreSQL에 엔티티 저장

```python
async def save_entities_to_postgres(
    self,
    report_id: UUID,
    entities: dict[str, Any],
    db: AsyncSession
) -> dict[str, int]:
    """
    추출된 엔티티를 PostgreSQL에 저장

    Args:
        report_id: 리포트 ID
        entities: 추출된 엔티티
        db: AsyncSession

    Returns:
        저장된 엔티티 수
    """
    from app.db.postgres import Entity
    from uuid import uuid4

    stats = {
        "companies": 0,
        "industries": 0,
        "themes": 0,
        "total": 0
    }

    try:
        # Companies 저장
        for company in entities.get("companies", []):
            entity = Entity(
                id=uuid4(),
                report_id=report_id,
                entity_type="Company",
                name=company.get("name"),
                normalized_name=company.get("name", "").lower(),
                properties={
                    "ticker": company.get("ticker"),
                    "industry": company.get("industry"),
                    "market": company.get("market"),
                    "aliases": company.get("aliases", [])
                },
                confidence_score=company.get("confidence_score", 1.0),
                neo4j_node_id=""  # Neo4j에서 조회 필요 시 별도 처리
            )
            db.add(entity)
            stats["companies"] += 1

        # Industries 저장
        for industry in entities.get("industries", []):
            entity = Entity(
                id=uuid4(),
                report_id=report_id,
                entity_type="Industry",
                name=industry.get("name"),
                normalized_name=industry.get("name", "").lower(),
                properties={
                    "parent_industry": industry.get("parent_industry")
                },
                confidence_score=industry.get("confidence_score", 1.0),
                neo4j_node_id=""
            )
            db.add(entity)
            stats["industries"] += 1

        # Themes 저장
        for theme in entities.get("themes", []):
            entity = Entity(
                id=uuid4(),
                report_id=report_id,
                entity_type="Theme",
                name=theme.get("name"),
                normalized_name=theme.get("name", "").lower(),
                properties={
                    "keywords": theme.get("keywords", []),
                    "description": theme.get("description")
                },
                confidence_score=theme.get("confidence_score", 1.0),
                neo4j_node_id=""
            )
            db.add(entity)
            stats["themes"] += 1

        # 커밋
        await db.commit()
        stats["total"] = stats["companies"] + stats["industries"] + stats["themes"]
        logger.info(f"Saved entities to PostgreSQL: {stats}")

        return stats

    except Exception as e:
        logger.error(f"Failed to save entities to PostgreSQL: {e}", exc_info=True)
        await db.rollback()
        raise
```

---

### 2. process_report.py 수정

```python
# 파일 위치: backend/app/workers/tasks/process_report.py
# 라인 168 이후에 추가

async def _process_report_async(report_id_str: str, file_path: str) -> dict:
    """Async implementation of report processing"""
    report_id = UUID(report_id_str)

    try:
        logger.info(f"Starting processing for report {report_id}")

        # ... 기존 Step 1-4 ...

        # Step 4: Build knowledge graph
        await update_report_status(report_id, "building_graph")
        logger.info("Building knowledge graph")
        graph_service = await get_graph_service()

        # Get report title from metadata or entities
        report_title = pdf_document.metadata.title or "Untitled Report"

        graph_stats = await graph_service.build_graph_from_extraction(
            report_id=report_id,
            report_title=report_title,
            entities=entities,
            relationships=relationships,
            publish_date=pdf_document.metadata.creation_date,
        )

        # ✨ [신규] Step 4.5: Generate visualization data
        await update_report_status(report_id, "generating_visualization")
        logger.info("Generating visualization data for graph")

        try:
            async with AsyncSessionLocal() as db:
                visualization_data = await graph_service.generate_visualization_data(
                    report_id=report_id,
                    entities=entities,
                    db=db
                )
                # 시각화 데이터 생성 통계 추가
                graph_stats["visualization_nodes"] = visualization_data["stats"]["node_count"]
                graph_stats["visualization_relationships"] = visualization_data["stats"]["relationship_count"]
        except Exception as e:
            logger.warning(f"Failed to generate visualization data: {e}")
            # 계속 진행 - visualization은 선택사항

        # Step 5: Store vector embeddings
        await update_report_status(report_id, "storing_embeddings")
        logger.info("Generating and storing embeddings")
        vector_service = await get_vector_service()

        # ... 기존 Step 5-6 ...

        stats = {
            "report_id": report_id_str,
            "status": "completed",
            "pages": pdf_document.metadata.page_count,
            "entities_found": entities.get("entities_found", {}),
            "graph_nodes": graph_stats["nodes_created"],
            "graph_relationships": graph_stats["relationships_created"],
            "visualization_nodes": graph_stats.get("visualization_nodes", 0),  # 신규
            "visualization_relationships": graph_stats.get("visualization_relationships", 0),  # 신규
            "vector_chunks": chunks_stored,
        }

        logger.info(f"Report processing completed: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Report processing failed: {e}", exc_info=True)
        # ... 기존 에러 처리 ...
```

---

## 🔍 상태 업데이트 추가

```python
async def update_report_status(
    report_id: UUID,
    status: str,
    error: str = None
) -> None:
    """
    Update report processing status

    Status 값:
    - parsing_pdf
    - extracting_entities
    - extracting_relationships
    - building_graph
    - generating_visualization  # 신규
    - storing_embeddings
    - updating_metadata
    - completed
    - failed
    """
    async with AsyncSessionLocal() as session:
        stmt = (
            update(Report)
            .where(Report.id == report_id)
            .values(status=status)
        )
        await session.execute(stmt)
        await session.commit()
```

---

## 📋 PostgreSQL Entity 모델 확인

```python
# 기존 모델 (app/db/postgres.py)

class Entity(Base):
    """리포트에서 추출된 엔티티"""
    __tablename__ = "entities"

    id: UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    report_id: UUID = Column(UUID(as_uuid=True), ForeignKey("reports.id"), nullable=False)
    entity_type: str = Column(String, nullable=False)  # Company, Industry, Theme
    name: str = Column(String, nullable=False)
    normalized_name: str = Column(String, nullable=False)
    properties: dict = Column(JSON, nullable=True)  # JSONB
    confidence_score: float = Column(Float, default=1.0)
    neo4j_node_id: str = Column(String, nullable=True)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
```

**확인 사항:**
- ✅ Entity 테이블 이미 존재
- ✅ properties: JSON 필드 (ticker, industry, market, keywords 등 저장 가능)
- ✅ confidence_score: 추출 신뢰도
- ✅ neo4j_node_id: Neo4j 노드 참조 (향후 사용)

---

## 🔧 Pydantic 모델 추가

```python
# 파일 위치: backend/app/api/v1/reports.py (기존 모델 근처)

from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class GraphNodeInfo(BaseModel):
    """그래프 노드 정보"""
    id: str
    label: str
    type: str
    properties: Dict[str, Any] = {}

class GraphRelationshipInfo(BaseModel):
    """그래프 관계 정보"""
    source_id: str
    source_type: str
    source_label: str
    target_id: str
    target_type: str
    target_label: str
    relationship_type: str
    properties: Dict[str, Any] = {}

class GraphVisualizationResponse(BaseModel):
    """그래프 시각화용 응답"""
    report_id: str
    nodes: List[GraphNodeInfo]
    relationships: List[GraphRelationshipInfo]
    stats: Dict[str, Any]
```

---

## ⚙️ 성능 최적화

### Neo4j 인덱스 생성

```cypher
CREATE INDEX IF NOT EXISTS FOR (c:Company) ON (c.ticker);
CREATE INDEX IF NOT EXISTS FOR (i:Industry) ON (i.name);
CREATE INDEX IF NOT EXISTS FOR (t:Theme) ON (t.name);
```

### 병렬 쿼리 실행

사용된 `asyncio.gather()`로 3개 쿼리 동시 실행:
- Query A (Company): ~100ms
- Query B (Industry): ~50ms
- Query C (Theme): ~50ms
- **순차 실행**: 200ms
- **병렬 실행**: ~100ms (2배 빠름)

---

## 📊 파이프라인 성능

| 단계 | 시간 | 비고 |
|------|------|------|
| 1. PDF 파싱 | 500ms | 페이지 수에 따름 |
| 2. 엔티티 추출 | 2-3s | LLM API 호출 |
| 3. 관계 추출 | 2-3s | LLM API 호출 |
| 4. 그래프 빌딩 | 500ms | Neo4j 쓰기 |
| **4.5 시각화 생성** | **200ms** | **병렬 쿼리** |
| 5. 벡터 임베딩 | 1-2s | 청크 수에 따름 |
| 6. 메타데이터 업데이트 | 100ms | PostgreSQL |
| **총 시간** | **7-10s** | |

**Step 4.5 오버헤드: ~200ms (2%)**

---

## 🔄 데이터 흐름 예시

### 입력: entities (ExtractionService 결과)
```python
{
    "companies": [
        {"name": "Apple Inc.", "ticker": "AAPL", "industry": "Technology"},
        {"name": "Microsoft", "ticker": "MSFT", "industry": "Technology"}
    ],
    "industries": [
        {"name": "Technology", "parent_industry": "Information Technology"}
    ],
    "themes": [
        {"name": "AI", "keywords": ["artificial intelligence", "ML"]}
    ]
}
```

### Step 4.5 처리 흐름
```
1. Entity 식별자 추출
   companies: {"AAPL", "MSFT"}
   industries: {"Technology"}
   themes: {"AI"}

2. Neo4j 병렬 쿼리
   Query A: AAPL, MSFT 관련 관계 → [rel1, rel2, ...]
   Query B: Technology 관련 관계 → [rel3, rel4, ...]
   Query C: AI 관련 관계 → [rel5, rel6, ...]

3. PostgreSQL 저장
   Entity(Company, "Apple Inc.", properties={ticker: AAPL, ...})
   Entity(Company, "Microsoft", properties={ticker: MSFT, ...})
   Entity(Industry, "Technology", ...)
   Entity(Theme, "AI", ...)

4. 노드 중복 제거
   Nodes = {AAPL, MSFT, Technology, AI, ...}

5. 시각화 데이터 생성
   {
       nodes: [GraphNodeInfo, ...],
       relationships: [GraphRelationshipInfo, ...],
       stats: {node_count: 10, relationship_count: 15, ...}
   }
```

### 출력: visualization_data
```json
{
    "nodes": [
        {"id": "AAPL", "label": "Apple Inc.", "type": "Company"},
        {"id": "MSFT", "label": "Microsoft", "type": "Company"},
        {"id": "Technology", "label": "Technology", "type": "Industry"},
        {"id": "AI", "label": "AI", "type": "Theme"}
    ],
    "relationships": [
        {
            "source_id": "AAPL",
            "source_type": "Company",
            "target_id": "Technology",
            "target_type": "Industry",
            "relationship_type": "OPERATES_IN"
        },
        {
            "source_id": "AAPL",
            "source_type": "Company",
            "target_id": "AI",
            "target_type": "Theme",
            "relationship_type": "MENTIONED_WITH"
        }
    ],
    "stats": {
        "node_count": 4,
        "relationship_count": 2,
        "node_types": {"Company": 2, "Industry": 1, "Theme": 1}
    }
}
```

---

## 🎯 구현 순서

### Phase 1: GraphService 수정 (1시간)
1. NodeAggregator 클래스 추가
2. query_graph_relationships() 메서드 추가
3. save_entities_to_postgres() 메서드 추가
4. generate_visualization_data() 메서드 추가

### Phase 2: process_report.py 수정 (30분)
1. Step 4.5 추가 (generate_visualization_data 호출)
2. 상태 업데이트 추가
3. 통계 수집 추가

### Phase 3: 테스트 (30분)
1. 로컬에서 리포트 처리
2. PostgreSQL Entity 저장 확인
3. 시각화 데이터 생성 확인
4. 성능 측정

---

## ✅ 체크리스트

### GraphService 구현
- [ ] NodeAggregator 클래스 추가
- [ ] query_graph_relationships() 구현
- [ ] save_entities_to_postgres() 구현
- [ ] generate_visualization_data() 구현
- [ ] 에러 처리 추가
- [ ] 로깅 추가

### process_report.py 수정
- [ ] Step 4.5 추가
- [ ] update_report_status() 호출
- [ ] 통계 수집
- [ ] 에러 처리 (visualization 실패해도 계속)

### 테스트
- [ ] 실제 리포트 처리 테스트
- [ ] PostgreSQL Entity 확인
- [ ] Neo4j 관계 확인
- [ ] 시각화 데이터 확인
- [ ] 성능 확인

### 배포
- [ ] Neo4j 인덱스 생성
- [ ] 코드 리뷰
- [ ] 프로덕션 배포

---

## 🚀 다음 단계

이 파이프라인 수정 완료 후:
1. API 엔드포인트 `GET /reports/{report_id}/graph/relationships` 구현
2. 프론트엔드 GraphVisualization 컴포넌트 통합
3. 성능 최적화 및 캐싱

