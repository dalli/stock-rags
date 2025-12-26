# 그래프 시각화 구현 요약

## 📋 목표

리포트 상세보기 페이지의 그래프 탭에서 **노드(Node)와 관계(Relationship)를 인터랙티브하게 시각화**합니다.

**현재:** 카드로 개수만 표시 → **구현 후:** Force Graph로 관계 시각화

---

## 🏗️ 핵심 아키텍처

### 데이터 흐름

```
PostgreSQL (엔티티)
    ↓ [식별자 추출]
Neo4j (관계 쿼리)
    ↓ [데이터 변환]
FastAPI (JSON 응답)
    ↓ [API 호출]
React (GraphVisualization)
    ↓ [Force Graph 렌더링]
UI (인터랙티브 그래프)
```

---

## 🔧 기술 스택

| 레이어 | 기술 | 역할 |
|--------|------|------|
| 백엔드 | FastAPI + Neo4j + PostgreSQL | 관계 데이터 조회 및 제공 |
| 프론트엔드 | React + TypeScript | 그래프 렌더링 및 인터랙션 |
| 그래프 라이브러리 | 3d-force-graph 또는 force-graph | 시각화 |

---

## 📊 구현 범위

### Phase 1: 백엔드 (필수)

#### 1.1 데이터 모델 (Pydantic)

```python
class GraphNodeInfo(BaseModel):
    id: str  # ticker, name
    label: str  # 표시 라벨
    type: str  # Company, Industry, Theme, TargetPrice, Opinion
    properties: dict = {}

class GraphRelationshipInfo(BaseModel):
    source_id: str
    source_type: str
    source_label: str
    target_id: str
    target_type: str
    target_label: str
    relationship_type: str  # HAS_OPINION, OPERATES_IN 등
    properties: dict = {}

class GraphVisualizationResponse(BaseModel):
    report_id: str
    nodes: List[GraphNodeInfo]
    relationships: List[GraphRelationshipInfo]
    stats: dict
```

#### 1.2 GraphService 메서드

**메서드 1: 엔티티 식별자 추출**
```python
async def extract_entities_for_visualization(
    db: AsyncSession,
    report_id: UUID
) -> dict[str, set[str]]:
    """
    PostgreSQL에서 리포트의 모든 엔티티 조회

    Returns:
        {
            "companies": {"AAPL", "MSFT"},
            "industries": {"Technology"},
            "themes": {"AI"}
        }
    """
```

**메서드 2: Neo4j 관계 조회**
```python
async def get_report_relationships(
    self,
    report_id: UUID,
    include_types: Optional[List[str]] = None,
    limit: int = 500
) -> dict:
    """
    Neo4j에서 3가지 쿼리 병렬 실행:
    - Company → 모든 노드
    - Industry → 모든 노드
    - Theme → 모든 노드

    Returns:
        {
            'nodes': [GraphNodeInfo],
            'relationships': [GraphRelationshipInfo],
            'stats': {...}
        }
    """
```

**메서드 3: 데이터 통합**
```python
async def get_report_graph_for_visualization(
    self,
    report_id: UUID,
    db: AsyncSession
) -> dict:
    """
    엔티티 + 관계 데이터 통합

    1. PostgreSQL 엔티티 식별자 추출
    2. Neo4j 관계 조회 (병렬)
    3. 노드 중복 제거
    4. 데이터 변환
    """
```

#### 1.3 API 엔드포인트

```python
@router.get("/{report_id}/graph/relationships", response_model=GraphVisualizationResponse)
async def get_report_graph_relationships(
    report_id: UUID,
    limit: int = 500,
    db: AsyncSession = Depends(get_db),
) -> GraphVisualizationResponse:
    """
    GET /reports/{report_id}/graph/relationships

    Response:
        {
            "report_id": "...",
            "nodes": [...],
            "relationships": [...],
            "stats": {...}
        }
    """
```

#### 1.4 Neo4j 쿼리 (3개 병렬)

**쿼리 A: Company 관계**
```cypher
MATCH (c:Company)
WHERE c.ticker IN $tickers
MATCH (c)-[rel]-(connected)
RETURN
    c.ticker as source_id,
    'Company' as source_type,
    c.name as source_label,
    type(rel) as relationship_type,
    [타겟 노드 정보],
    properties(rel) as rel_properties
LIMIT 200
```

**쿼리 B: Industry 관계** (유사)

**쿼리 C: Theme 관계** (유사)

#### 1.5 핵심 로직: NodeAggregator

```python
class NodeAggregator:
    """Neo4j 결과에서 고유 노드 추출 및 관계 집계"""

    def add_relationship(self, rel: dict):
        # 소스 노드 등록 (중복 제거)
        source_key = f"{rel['source_type']}:{rel['source_id']}"
        if source_key not in self.nodes:
            self.nodes[source_key] = GraphNodeInfo(...)

        # 타겟 노드 등록 (중복 제거)
        target_key = f"{rel['target_type']}:{rel['target_id']}"
        if target_key not in self.nodes:
            self.nodes[target_key] = GraphNodeInfo(...)

        # 관계 등록 (중복 제거)
        if not self._relationship_exists(rel):
            self.relationships.append(rel)
```

---

### Phase 2: 프론트엔드 (필수)

#### 2.1 타입 정의

```typescript
// frontend/src/api/types.ts 추가

export interface GraphNode {
  id: string
  label: string
  type: 'Company' | 'Industry' | 'Theme' | 'TargetPrice' | 'Opinion'
  properties?: Record<string, unknown>
}

export interface GraphRelationship {
  source_id: string
  source_type: string
  source_label: string
  target_id: string
  target_type: string
  target_label: string
  relationship_type: string
  properties?: Record<string, unknown>
}

export interface GraphVisualizationResponse {
  report_id: string
  nodes: GraphNode[]
  relationships: GraphRelationship[]
  stats: {
    node_count: number
    relationship_count: number
    node_types: Record<string, number>
  }
}
```

#### 2.2 API 클라이언트

```typescript
// frontend/src/api/reports.ts 수정

export const reportsApi = {
  async getReportGraphVisualization(
    reportId: string
  ): Promise<GraphVisualizationResponse> {
    const response = await api.get(
      `/reports/${reportId}/graph/relationships`
    )
    return response.data
  },
}
```

#### 2.3 GraphVisualization 컴포넌트

```typescript
// frontend/src/components/GraphVisualization.tsx (신규)

interface GraphVisualizationProps {
  data: GraphVisualizationResponse
  loading?: boolean
  height?: number | string
}

export const GraphVisualization: React.FC<GraphVisualizationProps> = ({
  data,
  loading = false,
  height = '600px',
}) => {
  // 1. Force Graph 데이터 변환
  const graphData = {
    nodes: data.nodes.map(n => ({
      id: `${n.type}:${n.id}`,
      name: n.label,
      type: n.type,
      color: NODE_COLORS[n.type],
      val: NODE_SIZES[n.type],
    })),
    links: data.relationships.map(r => ({
      source: `${r.source_type}:${r.source_id}`,
      target: `${r.target_type}:${r.target_id}`,
      label: r.relationship_type,
    })),
  }

  // 2. 3D Force Graph 렌더링
  useEffect(() => {
    const graph = ForceGraph3D()(containerRef.current)
      .graphData(graphData)
      .nodeColor(d => d.color)
      .nodeVal(d => d.val)
      .onNodeClick(node => setSelectedNode(...))
      .onLinkClick(link => setSelectedRelationship(...))
  }, [graphData])

  // 3. 인터랙션 처리
  return (
    <Box>
      <Box ref={containerRef} height={height} /> {/* 그래프 */}
      <Box> {/* 정보 패널 */}
        {selectedNode && <NodeInfo {...} />}
        {selectedRelationship && <RelationshipInfo {...} />}
      </Box>
    </Box>
  )
}
```

#### 2.4 ReportDetail 페이지 통합

```typescript
// frontend/src/pages/ReportDetail.tsx 수정

const [graphVisualization, setGraphVisualization] = useState<GraphVisualizationResponse | null>(null)

useEffect(() => {
  // 기존 코드...

  // 신규: 그래프 시각화 데이터 로드
  const visualization = await reportsApi.getReportGraphVisualization(reportId)
  setGraphVisualization(visualization)
}, [reportId])

// TabPanel 내용 수정
return (
  <TabPanel value={tabValue} index={0}>
    {/* 통계 카드 (기존) */}
    {graphInfo && (
      <Grid container spacing={2}>
        <Card><CardContent>Nodes: {graphInfo.nodes_count}</CardContent></Card>
        <Card><CardContent>Relationships: {graphInfo.relationships_count}</CardContent></Card>
      </Grid>
    )}

    {/* 신규: 그래프 시각화 */}
    {graphVisualization && (
      <Box sx={{ mt: 3 }}>
        <Typography variant="h6">Graph Visualization</Typography>
        <GraphVisualization data={graphVisualization} height={600} />
      </Box>
    )}

    {/* 기존 테이블들 */}
  </TabPanel>
)
```

---

## 📦 라이브러리 설치

### 프론트엔드

```bash
# 3D 버전 (권장)
npm install 3d-force-graph
npm install --save-dev @types/3d-force-graph

# 또는 2D 버전 (가볍고 빠름)
npm install force-graph
npm install --save-dev @types/force-graph
```

### 백엔드

기존에 설치된 라이브러리 사용:
- neo4j ✅
- sqlalchemy ✅
- fastapi ✅
- pydantic ✅

---

## 🎨 시각화 설계

### 노드 색상 (타입별)

```
Company      → Blue     (#1976D2)
Industry     → Green    (#388E3C)
Theme        → Orange   (#F57C00)
TargetPrice  → Purple   (#7B1FA2)
Opinion      → Pink     (#C2185B)
```

### 노드 크기 (타입별)

```
Company      → 8
Industry     → 6
Theme        → 5
TargetPrice  → 4
Opinion      → 4
```

---

## ⚡ 성능 최적화

### Neo4j
```cypher
-- 인덱스 생성 (필수)
CREATE INDEX IF NOT EXISTS FOR (c:Company) ON (c.ticker);
CREATE INDEX IF NOT EXISTS FOR (i:Industry) ON (i.name);
CREATE INDEX IF NOT EXISTS FOR (t:Theme) ON (t.name);
```

### 백엔드
- 병렬 쿼리 실행 (asyncio.gather)
- 결과 제한 (LIMIT 500)
- 캐싱 (선택사항)

### 프론트엔드
- 요청 시 로딩 표시
- 대용량 노드는 페이지네이션 고려
- 선택적 노드 렌더링 (차후)

---

## 🧪 테스트

### 백엔드 테스트
```bash
curl http://localhost:8000/api/v1/reports/{report_id}/graph/relationships
```

**예상 응답:**
```json
{
  "report_id": "550e8400-e29b-41d4-a716-446655440000",
  "nodes": [
    {
      "id": "AAPL",
      "label": "Apple Inc.",
      "type": "Company",
      "properties": {"market": "NASDAQ"}
    }
  ],
  "relationships": [
    {
      "source_id": "AAPL",
      "source_type": "Company",
      "source_label": "Apple Inc.",
      "target_id": "Technology",
      "target_type": "Industry",
      "target_label": "Technology",
      "relationship_type": "OPERATES_IN",
      "properties": {}
    }
  ],
  "stats": {
    "node_count": 25,
    "relationship_count": 42,
    "node_types": {"Company": 5, "Industry": 3, "Theme": 2}
  }
}
```

---

## 📋 구현 체크리스트

### 백엔드
- [ ] Pydantic 모델 정의 (GraphNodeInfo, GraphRelationshipInfo)
- [ ] GraphService 메서드 구현
  - [ ] extract_entities_for_visualization()
  - [ ] get_report_relationships()
  - [ ] get_report_graph_for_visualization()
- [ ] NodeAggregator 클래스 구현
- [ ] API 엔드포인트 구현
- [ ] 에러 처리 추가
- [ ] 단위 테스트

### 프론트엔드
- [ ] 타입 정의 추가
- [ ] API 클라이언트 메서드 추가
- [ ] 라이브러리 설치
- [ ] GraphVisualization 컴포넌트 작성
- [ ] ReportDetail 페이지 통합
- [ ] 테스트

### 배포
- [ ] Neo4j 인덱스 생성
- [ ] 통합 테스트
- [ ] 성능 테스트
- [ ] 프로덕션 배포

---

## 📚 상세 문서

두 개의 상세 설계 문서 생성됨:

1. **IMPLEMENTATION_PLAN_GRAPH_VISUALIZATION.md**
   - 전체 구현 계획
   - 아키텍처 설계
   - 전체 코드 예시

2. **DETAILED_RELATIONSHIP_DESIGN.md**
   - 관계 데이터 생성 상세 설계
   - Neo4j 쿼리 최적화
   - 에러 처리 및 캐싱

---

## 🚀 다음 단계

**즉시 시작 가능한 작업:**
1. GraphService 메서드 구현 (백엔드)
2. API 엔드포인트 추가 (백엔드)
3. 라이브러리 설치 (프론트엔드)
4. GraphVisualization 컴포넌트 작성 (프론트엔드)

**예상 구현 시간:**
- 백엔드: 2-3시간
- 프론트엔드: 2-3시간
- 통합 및 테스트: 1-2시간

**총 예상 시간:** 5-8시간

