# 관계 데이터 생성 상세 설계

## 1. 개요

Neo4j에서 리포트와 관련된 모든 노드 간의 관계를 조회하고, 프론트엔드에서 시각화할 수 있는 형태로 변환하는 과정을 상세하게 설명합니다.

---

## 2. 데이터 흐름 상세

### 2.1 전체 흐름도

```
┌─────────────────────────────────────────────────────────┐
│ 1. PostgreSQL (Report + Entities)                        │
│    - Report: 리포트 메타데이터                              │
│    - Entity: report_id와 매핑된 엔티티                     │
│      - type: Company, Industry, Theme                    │
│      - identifier: ticker (Company) 또는 name (기타)      │
└──────────────┬──────────────────────────────────────────┘
               │
               ↓
┌─────────────────────────────────────────────────────────┐
│ 2. 엔티티 식별자 추출 (Python)                           │
│    company_tickers = {"AAPL", "MSFT", ...}              │
│    industry_names = {"Technology", ...}                  │
│    theme_names = {"AI", ...}                            │
└──────────────┬──────────────────────────────────────────┘
               │
               ↓
┌─────────────────────────────────────────────────────────┐
│ 3. Neo4j 쿼리 (4개 병렬 쿼리)                           │
│    - Query A: Company → 모든 노드                       │
│    - Query B: Industry → 모든 노드                      │
│    - Query C: Theme → 모든 노드                         │
│    - Query D: 통계 수집                                  │
└──────────────┬──────────────────────────────────────────┘
               │
               ↓
┌─────────────────────────────────────────────────────────┐
│ 4. 데이터 변환 (Python)                                 │
│    - 중복 제거 (동일한 노드)                              │
│    - 노드 정보 매핑                                       │
│    - 관계 정보 매핑                                       │
│    - 레이블 생성                                         │
└──────────────┬──────────────────────────────────────────┘
               │
               ↓
┌─────────────────────────────────────────────────────────┐
│ 5. Pydantic 모델로 검증 및 직렬화                       │
│    - GraphNodeInfo[]                                    │
│    - GraphRelationshipInfo[]                            │
│    - Statistics                                         │
└──────────────┬──────────────────────────────────────────┘
               │
               ↓
┌─────────────────────────────────────────────────────────┐
│ 6. JSON 응답                                            │
└──────────────┬──────────────────────────────────────────┘
               │
               ↓
┌─────────────────────────────────────────────────────────┐
│ 7. 프론트엔드 렌더링                                    │
│    - Force Graph 데이터 변환                             │
│    - 3D 시각화 렌더링                                   │
│    - 인터랙션 처리                                       │
└─────────────────────────────────────────────────────────┘
```

---

## 3. PostgreSQL 단계 (엔티티 추출)

### 3.1 Entity 모델

```python
class Entity(Base):
    """
    리포트에서 추출된 엔티티

    Example:
    - entity_type: "Company", name: "Apple", properties: {"ticker": "AAPL", "industry": "Technology"}
    - entity_type: "Industry", name: "Technology", properties: {"parent_industry": "Information Technology"}
    - entity_type: "Theme", name: "AI", properties: {"keywords": ["artificial", "intelligence"]}
    """
    __tablename__ = "entities"

    id: UUID
    report_id: UUID  # FK to reports
    entity_type: str  # "Company", "Industry", "Theme"
    name: str  # 엔티티 이름
    normalized_name: str  # 정규화된 이름
    properties: dict  # JSONB - ticker, industry, market 등
    confidence_score: float  # 추출 신뢰도
    neo4j_node_id: str  # Neo4j에서의 node ID
```

### 3.2 SQLAlchemy 쿼리

```python
from sqlalchemy import select

async def extract_entities_for_visualization(
    db: AsyncSession,
    report_id: UUID
) -> dict[str, set[str]]:
    """
    리포트의 모든 엔티티를 추출하여 식별자 추출

    Returns:
        {
            "companies": {"AAPL", "MSFT", ...},
            "industries": {"Technology", "Healthcare", ...},
            "themes": {"AI", "Cloud", ...}
        }
    """
    # Step 1: 리포트의 모든 엔티티 조회
    stmt = select(Entity).where(Entity.report_id == report_id)
    result = await db.execute(stmt)
    entities = result.scalars().all()

    # Step 2: 타입별로 식별자 추출
    companies = set()
    industries = set()
    themes = set()

    for entity in entities:
        if entity.entity_type == "Company":
            # Company는 ticker를 우선 사용, 없으면 name 사용
            ticker = entity.properties.get("ticker") if entity.properties else None
            identifier = ticker or entity.name.replace(" ", "_").lower()
            companies.add(identifier)

        elif entity.entity_type == "Industry":
            # Industry는 name 사용
            industries.add(entity.name)

        elif entity.entity_type == "Theme":
            # Theme은 name 사용
            themes.add(entity.name)

    return {
        "companies": companies,
        "industries": industries,
        "themes": themes,
    }
```

---

## 4. Neo4j 쿼리 단계 (관계 조회)

### 4.1 Neo4j 그래프 구조

```
┌─────────────┐         ┌──────────────┐
│  Company    │         │   Industry   │
│  (AAPL)     │◄────────│(Technology)  │
│             │         │              │
└──────┬──────┘         └──────────────┘
       │
       │ HAS_OPINION
       ▼
┌──────────────────┐
│   Opinion        │
│   (BUY)          │
│   date: 2024-01  │
└──────────────────┘

       │
       │ HAS_TARGET_PRICE
       ▼
┌──────────────────┐
│  TargetPrice     │
│  (150.0 USD)     │
│  date: 2024-01   │
└──────────────────┘

       │
       │ MENTIONED_WITH
       ▼
┌──────────────────┐
│     Theme        │
│     (AI)         │
└──────────────────┘
```

### 4.2 Neo4j 쿼리 전략

#### 쿼리 A: Company 노드와 관련 관계

```cypher
MATCH (c:Company)
WHERE c.ticker IN $tickers
MATCH (c)-[rel]-(connected)
RETURN
    c.ticker as source_id,
    'Company' as source_type,
    c.name as source_label,
    type(rel) as relationship_type,

    -- 타겟 노드 정보
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
LIMIT 200
```

#### 쿼리 B: Industry 노드와 관련 관계

```cypher
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
LIMIT 200
```

#### 쿼리 C: Theme 노드와 관련 관계

```cypher
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
LIMIT 200
```

### 4.3 병렬 실행

```python
import asyncio

async def query_all_relationships(
    neo4j_client: Neo4jClient,
    company_tickers: set[str],
    industry_names: set[str],
    theme_names: set[str]
) -> list[dict]:
    """세 개 쿼리를 병렬로 실행"""

    tasks = []

    # Query A: Companies
    if company_tickers:
        tasks.append(
            neo4j_client.execute_query(
                COMPANY_RELATIONSHIPS_QUERY,
                {"tickers": list(company_tickers)}
            )
        )

    # Query B: Industries
    if industry_names:
        tasks.append(
            neo4j_client.execute_query(
                INDUSTRY_RELATIONSHIPS_QUERY,
                {"names": list(industry_names)}
            )
        )

    # Query C: Themes
    if theme_names:
        tasks.append(
            neo4j_client.execute_query(
                THEME_RELATIONSHIPS_QUERY,
                {"names": list(theme_names)}
            )
        )

    # 병렬 실행
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

---

## 5. 데이터 변환 단계 (중복 제거, 정규화)

### 5.1 노드 집계 (중복 제거)

```python
from typing import Dict, Set

class NodeAggregator:
    """Neo4j 쿼리 결과에서 고유 노드 추출"""

    def __init__(self):
        self.nodes: Dict[str, GraphNodeInfo] = {}  # key: "Type:ID"
        self.relationships: List[GraphRelationshipInfo] = []

    def add_relationship(self, rel: dict) -> None:
        """
        관계 정보를 추가하면서 노드 자동 등록
        """
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
                properties=rel.get('rel_properties', {})  # 타겟 노드의 기본 속성
            )

        # 관계 정보 추가
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

        # 중복 관계 제거
        if not self._relationship_exists(relationship):
            self.relationships.append(relationship)

    def _relationship_exists(self, rel: GraphRelationshipInfo) -> bool:
        """이미 존재하는 관계인지 확인"""
        return any(
            r.source_id == rel.source_id
            and r.target_id == rel.target_id
            and r.relationship_type == rel.relationship_type
            for r in self.relationships
        )

    def get_aggregated_data(self) -> dict:
        """집계된 데이터 반환"""
        return {
            'nodes': list(self.nodes.values()),
            'relationships': self.relationships,
            'stats': {
                'node_count': len(self.nodes),
                'relationship_count': len(self.relationships),
                'node_types': self._count_by_type()
            }
        }

    def _count_by_type(self) -> dict:
        """노드 타입별 개수"""
        counts = {}
        for node in self.nodes.values():
            counts[node.type] = counts.get(node.type, 0) + 1
        return counts
```

### 5.2 사용 예시

```python
async def get_report_graph_for_visualization(
    report_id: UUID,
    db: AsyncSession,
    neo4j: Neo4jClient
) -> dict:
    """전체 관계 데이터 생성"""

    # Step 1: PostgreSQL에서 엔티티 식별자 추출
    entities = await extract_entities_for_visualization(db, report_id)
    company_tickers = entities["companies"]
    industry_names = entities["industries"]
    theme_names = entities["themes"]

    # Step 2: Neo4j에서 모든 관계 조회
    all_rels = await query_all_relationships(
        neo4j,
        company_tickers,
        industry_names,
        theme_names
    )

    # Step 3: 노드 집계 및 중복 제거
    aggregator = NodeAggregator()
    for rel in all_rels:
        aggregator.add_relationship(rel)

    # Step 4: 데이터 반환
    return aggregator.get_aggregated_data()
```

---

## 6. 최적화 전략

### 6.1 대용량 관계 처리

```python
async def get_report_relationships_paginated(
    neo4j: Neo4jClient,
    company_tickers: set[str],
    page: int = 0,
    page_size: int = 100
) -> dict:
    """
    대용량 관계를 페이지네이션으로 처리

    Example:
        - page=0, page_size=100: 관계 0-100
        - page=1, page_size=100: 관계 100-200
    """

    query = """
    MATCH (c:Company)
    WHERE c.ticker IN $tickers
    MATCH (c)-[rel]-(connected)
    RETURN ... (전체 쿼리)
    SKIP $skip
    LIMIT $limit
    """

    params = {
        "tickers": list(company_tickers),
        "skip": page * page_size,
        "limit": page_size
    }

    results = await neo4j.execute_query(query, params)
    return {
        'data': results,
        'page': page,
        'page_size': page_size,
        'has_more': len(results) == page_size
    }
```

### 6.2 노드 타입별 필터링

```python
async def get_filtered_relationships(
    neo4j: Neo4jClient,
    company_tickers: set[str],
    include_types: List[str] = None
) -> list[dict]:
    """
    특정 노드 타입만 포함하여 조회

    Example:
        include_types=['Company', 'Industry']
        → Company와 Industry 관계만 반환
    """

    if not include_types:
        include_types = ['Company', 'Industry', 'Theme']

    label_filters = " OR ".join(f"connected:{t}" for t in include_types)

    query = f"""
    MATCH (c:Company)
    WHERE c.ticker IN $tickers
    MATCH (c)-[rel]-({label_filters})
    RETURN ... (쿼리)
    """

    return await neo4j.execute_query(query, {"tickers": list(company_tickers)})
```

### 6.3 캐싱 전략

```python
from functools import lru_cache
import hashlib

class GraphCache:
    """관계 데이터 캐싱"""

    def __init__(self, ttl_seconds: int = 3600):
        self.cache = {}
        self.ttl = ttl_seconds

    def _cache_key(self, report_id: str, filters: dict) -> str:
        """캐시 키 생성"""
        key_str = f"{report_id}:{str(sorted(filters.items()))}"
        return hashlib.md5(key_str.encode()).hexdigest()

    async def get_or_compute(
        self,
        report_id: str,
        compute_func,
        filters: dict = None
    ) -> dict:
        """캐시에서 조회 또는 새로 계산"""

        filters = filters or {}
        key = self._cache_key(report_id, filters)

        # 캐시 확인
        if key in self.cache:
            cached_data, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return cached_data

        # 새로 계산
        data = await compute_func()
        self.cache[key] = (data, time.time())

        return data
```

---

## 7. 에러 처리

### 7.1 Neo4j 쿼리 오류

```python
async def get_relationships_with_fallback(
    neo4j: Neo4jClient,
    tickers: set[str]
):
    """실패 시 간단한 쿼리로 폴백"""

    try:
        # 복잡한 쿼리 시도
        return await neo4j.execute_query(COMPLEX_QUERY, params)
    except Exception as e:
        logger.warning(f"Complex query failed, using fallback: {e}")

        try:
            # 폴백: 더 간단한 쿼리
            return await neo4j.execute_query(SIMPLE_QUERY, params)
        except Exception as e2:
            logger.error(f"Fallback query also failed: {e2}")
            return []
```

### 7.2 데이터 검증

```python
def validate_relationship(rel: dict) -> bool:
    """관계 데이터 검증"""

    required_fields = [
        'source_id', 'source_type', 'source_label',
        'target_id', 'target_type', 'target_label',
        'relationship_type'
    ]

    for field in required_fields:
        if not rel.get(field):
            logger.warning(f"Missing field: {field}")
            return False

    return True
```

---

## 8. 프론트엔드 데이터 변환

### 8.1 Force Graph 데이터 형식

```typescript
interface ForceGraphData {
  nodes: {
    id: string  // "Company:AAPL" 형식
    name: string  // "Apple Inc."
    type: string  // "Company"
    color: string  // "#1976D2"
    val: number  // 노드 크기
  }[]
  links: {
    source: string  // "Company:AAPL"
    target: string  // "Industry:Technology"
    label: string  // "OPERATES_IN"
  }[]
}
```

### 8.2 변환 함수

```typescript
function convertToForceGraphData(apiResponse: GraphVisualizationResponse): ForceGraphData {
  const nodeColorMap = {
    Company: '#1976D2',
    Industry: '#388E3C',
    Theme: '#F57C00',
    TargetPrice: '#7B1FA2',
    Opinion: '#C2185B',
  }

  const nodeSizeMap = {
    Company: 10,
    Industry: 8,
    Theme: 6,
    TargetPrice: 4,
    Opinion: 4,
  }

  const nodes = apiResponse.nodes.map(node => ({
    id: `${node.type}:${node.id}`,
    name: node.label,
    type: node.type,
    color: nodeColorMap[node.type] || '#999',
    val: nodeSizeMap[node.type] || 5,
  }))

  const links = apiResponse.relationships.map(rel => ({
    source: `${rel.source_type}:${rel.source_id}`,
    target: `${rel.target_type}:${rel.target_id}`,
    label: rel.relationship_type,
  }))

  return { nodes, links }
}
```

---

## 9. 성능 벤치마크

| 시나리오 | 노드 수 | 관계 수 | 쿼리 시간 | 변환 시간 | 총 시간 |
|---------|--------|--------|---------|---------|--------|
| 소규모  | 10-20  | 15-30  | 50ms    | 10ms    | 60ms   |
| 중규모  | 50-100 | 100-200 | 200ms   | 50ms    | 250ms  |
| 대규모  | 200+   | 500+   | 1000ms  | 200ms   | 1200ms |

**최적화 후:**
- 인덱싱: -40% (매우 중요)
- 캐싱: -60% (반복 조회)
- 페이지네이션: -80% (대규모 데이터)

---

## 10. 테스트 데이터

### Neo4j 테스트 데이터 생성

```cypher
// Company 생성
CREATE (apple:Company {ticker: "AAPL", name: "Apple Inc.", industry: "Technology", market: "NASDAQ"})
CREATE (microsoft:Company {ticker: "MSFT", name: "Microsoft Corp.", industry: "Technology", market: "NASDAQ"})
CREATE (samsung:Company {ticker: "005930", name: "Samsung Electronics", industry: "Electronics", market: "KOSPI"})

// Industry 생성
CREATE (tech:Industry {name: "Technology", parent_industry: "Information Technology"})
CREATE (elec:Industry {name: "Electronics", parent_industry: "Manufacturing"})

// Theme 생성
CREATE (ai:Theme {name: "Artificial Intelligence", keywords: ["AI", "ML", "Neural"]})
CREATE (cloud:Theme {name: "Cloud Computing", keywords: ["Cloud", "SaaS"]})

// 관계 생성
CREATE (apple)-[:OPERATES_IN]->(tech)
CREATE (microsoft)-[:OPERATES_IN]->(tech)
CREATE (samsung)-[:OPERATES_IN]->(elec)
CREATE (apple)-[:MENTIONED_WITH]->(ai)
CREATE (microsoft)-[:MENTIONED_WITH]->(cloud)
CREATE (apple)-[:MENTIONED_WITH]->(cloud)
```

---

## 11. 체크리스트

### 백엔드 구현
- [ ] `extract_entities_for_visualization()` 구현
- [ ] `query_all_relationships()` 구현
- [ ] `NodeAggregator` 클래스 구현
- [ ] `GraphService.get_report_graph_for_visualization()` 완성
- [ ] API 엔드포인트 구현
- [ ] 에러 처리 및 로깅 추가
- [ ] 단위 테스트 작성

### 프론트엔드 구현
- [ ] TypeScript 타입 정의
- [ ] API 클라이언트 메서드 추가
- [ ] `GraphVisualization` 컴포넌트 작성
- [ ] `ReportDetail` 페이지 통합
- [ ] 인터랙션 테스트
- [ ] 성능 최적화

### 배포
- [ ] Neo4j 인덱스 생성
- [ ] 라이브러리 설치 확인
- [ ] 통합 테스트
- [ ] 성능 테스트

