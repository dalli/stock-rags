# 리포트 상세보기 그래프 시각화 구현 계획

## 1. 개요

리포트 상세보기 페이지에서 노드(Node)와 관계(Relationship)를 **인터랙티브 그래프**로 시각화합니다.

**현재 상태:**
- 카드: 노드수, 관계수 표시만 가능
- 테이블: 회사, 산업, 테마 정보만 표시
- **문제점**: 어떤 노드가 어떤 노드와 연결되어 있는지 시각적으로 표시 불가

**구현 후:**
- Interactive force graph로 노드-관계 시각화
- 노드 클릭 → 상세 정보 표시
- 관계 표시 → 관계 타입, 속성 표시

---

## 2. 아키텍처 설계

### 2.1 데이터 흐름

```
Neo4j (그래프 DB)
  ↓
[1] GraphService.get_report_relationships()
  ├─ 관계 쿼리 (source → target → relationship_type)
  └─ Neo4j 결과 → 파이썬 객체
  ↓
[2] FastAPI Endpoint: GET /reports/{report_id}/graph/relationships
  └─ GraphRelationshipsResponse (JSON)
  ↓
Frontend API Client
  ├─ reportsApi.getReportRelationships(reportId)
  └─ 캐싱 (선택사항)
  ↓
React Component: GraphVisualization
  ├─ 데이터 → Force Graph 변환
  ├─ React-Force-Graph 렌더링
  └─ 인터랙션 처리
```

### 2.2 Neo4j 쿼리 설계

**쿼리 1: 리포트 관련 노드와 관계 조회**
```cypher
MATCH (r:Report {report_id: $report_id})-[*0..2]-(n)
MATCH (n)-[rel]-(target)
WHERE target IS NOT NULL
RETURN DISTINCT
  startNode(rel).ticker as source_id,
  labels(startNode(rel))[0] as source_type,
  type(rel) as relationship_type,
  endNode(rel).ticker as target_id,
  labels(endNode(rel))[0] as target_type,
  properties(rel) as rel_properties
LIMIT 1000
```

**쿼리 2: 특정 엔티티 관련 관계만 조회 (최적화 버전)**
```cypher
MATCH (c:Company)
WHERE c.ticker IN $tickers
MATCH (c)-[rel]-(connected)
RETURN
  c.ticker as source_id,
  'Company' as source_type,
  type(rel) as relationship_type,
  CASE
    WHEN connected:Company THEN connected.ticker
    WHEN connected:Industry THEN connected.name
    WHEN connected:Theme THEN connected.name
    WHEN connected:TargetPrice THEN 'TargetPrice'
    WHEN connected:Opinion THEN 'Opinion'
    ELSE connected.id
  END as target_id,
  head(labels(connected)) as target_type,
  properties(rel) as rel_properties
LIMIT 500
```

---

## 3. 백엔드 구현

### 3.1 데이터 모델 정의 (Pydantic)

**파일:** `backend/app/api/v1/reports.py`

```python
# 추가할 Pydantic 모델들

class GraphNodeInfo(BaseModel):
    """그래프 노드 정보"""
    id: str  # ticker, name, 또는 ID
    label: str  # 노드의 표시할 레이블
    type: str  # Company, Industry, Theme, TargetPrice, Opinion
    properties: dict = {}  # 노드의 추가 정보


class GraphRelationshipInfo(BaseModel):
    """그래프 관계 정보"""
    source_id: str  # 소스 노드 ID
    source_type: str  # Company, Industry, Theme 등
    source_label: str  # 소스 노드 표시 라벨
    target_id: str  # 타겟 노드 ID
    target_type: str  # 타겟 노드 타입
    target_label: str  # 타겟 노드 표시 라벨
    relationship_type: str  # HAS_TARGET_PRICE, RELATED_TO 등
    properties: dict = {}  # 관계의 속성


class GraphVisualizationResponse(BaseModel):
    """그래프 시각화용 응답 모델"""
    report_id: str
    nodes: List[GraphNodeInfo]  # 고유 노드들
    relationships: List[GraphRelationshipInfo]  # 관계들
    stats: dict = {}  # 그래프 통계
```

### 3.2 GraphService 확장

**파일:** `backend/app/services/graph_service.py`

```python
async def get_report_relationships(
    self,
    report_id: UUID,
    include_types: Optional[List[str]] = None,  # 특정 타입만 포함
    limit: int = 500
) -> dict[str, Any]:
    """
    리포트와 관련된 모든 관계를 조회합니다.

    Args:
        report_id: 리포트 ID
        include_types: 포함할 노드 타입 (e.g., ['Company', 'Industry'])
        limit: 최대 관계 개수

    Returns:
        {
            'nodes': [노드 정보],
            'relationships': [관계 정보],
            'stats': {
                'node_count': int,
                'relationship_count': int,
                'node_types': {타입: 개수}
            }
        }
    """
    client = await self._get_client()

    # Step 1: 리포트의 엔티티 타입 조회
    # PostgreSQL에서 report_id의 entities 조회
    # Company tickers, Industry names, Theme names 추출

    # Step 2: Neo4j에서 관계 조회
    query = """
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
            WHEN connected:TargetPrice THEN apoc.util.md5(['TargetPrice', connected.date, connected.value])
            WHEN connected:Opinion THEN apoc.util.md5(['Opinion', connected.date, connected.rating])
            ELSE ID(connected)
        END as target_id,
        head(labels(connected)) as target_type,
        CASE
            WHEN connected:Company THEN connected.name
            WHEN connected:Industry THEN connected.name
            WHEN connected:Theme THEN connected.name
            WHEN connected:TargetPrice THEN 'Target Price: ' + toString(connected.value)
            WHEN connected:Opinion THEN 'Opinion: ' + connected.rating
            ELSE toString(properties(connected))
        END as target_label,
        properties(rel) as rel_properties
    LIMIT $limit
    """

    relationships = await client.execute_query(
        query,
        {"tickers": list(company_tickers), "limit": limit}
    )

    # Step 3: 노드 정보 집계
    nodes = {}  # 노드 ID → 노드 정보

    for rel in relationships:
        # 소스 노드
        source_key = f"{rel['source_type']}:{rel['source_id']}"
        if source_key not in nodes:
            nodes[source_key] = GraphNodeInfo(
                id=rel['source_id'],
                label=rel['source_label'],
                type=rel['source_type'],
                properties={}
            )

        # 타겟 노드
        target_key = f"{rel['target_type']}:{rel['target_id']}"
        if target_key not in nodes:
            nodes[target_key] = GraphNodeInfo(
                id=rel['target_id'],
                label=rel['target_label'],
                type=rel['target_type'],
                properties=rel.get('rel_properties', {})
            )

    # Step 4: 관계 정보 변환
    rels = [
        GraphRelationshipInfo(
            source_id=rel['source_id'],
            source_type=rel['source_type'],
            source_label=rel['source_label'],
            target_id=rel['target_id'],
            target_type=rel['target_type'],
            target_label=rel['target_label'],
            relationship_type=rel['relationship_type'],
            properties=rel.get('rel_properties', {})
        )
        for rel in relationships
    ]

    return {
        'nodes': list(nodes.values()),
        'relationships': rels,
        'stats': {
            'node_count': len(nodes),
            'relationship_count': len(rels),
            'node_types': self._count_by_type([n.type for n in nodes.values()])
        }
    }

async def get_report_graph_for_visualization(
    self,
    report_id: UUID,
    db: AsyncSession
) -> dict[str, Any]:
    """
    리포트 시각화용 그래프 데이터를 조회합니다.
    PostgreSQL 엔티티 + Neo4j 관계를 통합하여 반환합니다.
    """
    # PostgreSQL에서 엔티티 조회
    entity_stmt = select(Entity).where(Entity.report_id == report_id)
    entity_result = await db.execute(entity_stmt)
    entities = entity_result.scalars().all()

    # 엔티티별 ID 추출
    company_tickers = set()
    industry_names = set()
    theme_names = set()

    for entity in entities:
        if entity.entity_type == "Company":
            ticker = entity.properties.get("ticker") if entity.properties else None
            if ticker:
                company_tickers.add(ticker)
        elif entity.entity_type == "Industry":
            if entity.name:
                industry_names.add(entity.name)
        elif entity.entity_type == "Theme":
            if entity.name:
                theme_names.add(entity.name)

    # Neo4j에서 관계 조회
    relationships_data = await self.get_report_relationships(
        report_id,
        include_types=['Company', 'Industry', 'Theme']
    )

    return relationships_data
```

### 3.3 API 엔드포인트

**파일:** `backend/app/api/v1/reports.py`

```python
@router.get("/{report_id}/graph/relationships", response_model=GraphVisualizationResponse)
async def get_report_graph_relationships(
    report_id: UUID,
    limit: int = 500,
    db: AsyncSession = Depends(get_db),
) -> GraphVisualizationResponse:
    """
    리포트의 그래프 관계 정보를 조회합니다.

    노드(node)와 그들 사이의 관계(relationship)를 반환하여
    인터랙티브 그래프 시각화에 사용합니다.

    Returns:
        GraphVisualizationResponse: {
            "report_id": "...",
            "nodes": [
                {"id": "ticker1", "label": "Company Name", "type": "Company", ...},
                {"id": "industry1", "label": "Industry Name", "type": "Industry", ...}
            ],
            "relationships": [
                {
                    "source_id": "ticker1",
                    "source_type": "Company",
                    "target_id": "industry1",
                    "target_type": "Industry",
                    "relationship_type": "OPERATES_IN",
                    ...
                }
            ],
            "stats": {...}
        }
    """
    # 리포트 존재 확인
    stmt = select(Report).where(Report.id == report_id)
    result = await db.execute(stmt)
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    try:
        from app.services.graph_service import GraphService

        graph_service = GraphService()
        relationships_data = await graph_service.get_report_graph_for_visualization(
            report_id, db
        )

        return GraphVisualizationResponse(
            report_id=str(report_id),
            nodes=relationships_data['nodes'],
            relationships=relationships_data['relationships'],
            stats=relationships_data['stats']
        )

    except Exception as e:
        logger.error(f"Failed to get graph relationships: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get graph relationships: {str(e)}",
        )
```

---

## 4. 프론트엔드 구현

### 4.1 타입 정의 확장

**파일:** `frontend/src/api/types.ts`

```typescript
// 그래프 시각화 관련 타입 추가

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

// ReportDetail 페이지에서 사용할 통합 응답
export interface ReportGraphData {
  graph_info: GraphInfo  // 기존: 노드수, 관계수, 엔티티 목록
  visualization: GraphVisualizationResponse  // 신규: 노드와 관계 상세
}
```

### 4.2 API 클라이언트

**파일:** `frontend/src/api/reports.ts` (수정)

```typescript
export const reportsApi = {
  // ... 기존 메서드들

  /**
   * 리포트의 그래프 시각화 데이터 조회
   */
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

### 4.3 GraphVisualization 컴포넌트

**파일:** `frontend/src/components/GraphVisualization.tsx` (신규)

```typescript
import React, { useEffect, useRef, useState } from 'react'
import ForceGraph3D from '3d-force-graph'
import {
  Box,
  Paper,
  Typography,
  CircularProgress,
  Tooltip,
  Card,
  CardContent,
  Grid,
} from '@mui/material'
import { GraphVisualizationResponse, GraphNode, GraphRelationship } from '@/api/types'

interface GraphVisualizationProps {
  data: GraphVisualizationResponse
  loading?: boolean
  height?: number | string
}

// 노드 타입별 색상 정의
const NODE_COLORS: Record<string, string> = {
  Company: '#1976D2',      // Blue
  Industry: '#388E3C',     // Green
  Theme: '#F57C00',        // Orange
  TargetPrice: '#7B1FA2',  // Purple
  Opinion: '#C2185B',      // Pink
}

// 노드 크기 정의
const NODE_SIZES: Record<string, number> = {
  Company: 8,
  Industry: 6,
  Theme: 5,
  TargetPrice: 4,
  Opinion: 4,
}

export const GraphVisualization: React.FC<GraphVisualizationProps> = ({
  data,
  loading = false,
  height = '600px',
}) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const graphRef = useRef<any>(null)
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [selectedRelationship, setSelectedRelationship] = useState<GraphRelationship | null>(null)

  useEffect(() => {
    if (!containerRef.current || !data?.nodes || loading) return

    // Force Graph 데이터 변환
    const graphData = {
      nodes: data.nodes.map(node => ({
        id: `${node.type}:${node.id}`,
        name: node.label,
        type: node.type,
        color: NODE_COLORS[node.type] || '#999',
        size: NODE_SIZES[node.type] || 5,
        properties: node.properties,
      })),
      links: data.relationships.map(rel => ({
        source: `${rel.source_type}:${rel.source_id}`,
        target: `${rel.target_type}:${rel.target_id}`,
        label: rel.relationship_type,
        type: rel.relationship_type,
        properties: rel.properties,
      })),
    }

    // Force Graph 초기화
    const graph = ForceGraph3D()(containerRef.current)
      .graphData(graphData)
      .nodeLabel(d => `${d.name} (${d.type})`)
      .nodeColor(d => d.color)
      .nodeVal(d => d.size)
      .linkLabel(d => d.label)
      .linkColor(() => '#999')
      .linkDirectionalArrowLength(5)
      .linkDirectionalArrowRelPos(1)
      .onNodeClick(node => {
        // 노드 클릭 처리
        const foundNode = data.nodes.find(
          n => `${n.type}:${n.id}` === node.id
        )
        setSelectedNode(foundNode || null)
        setSelectedRelationship(null)
      })
      .onLinkClick(link => {
        // 링크 클릭 처리
        const foundRel = data.relationships.find(
          rel =>
            `${rel.source_type}:${rel.source_id}` === link.source.id &&
            `${rel.target_type}:${rel.target_id}` === link.target.id &&
            rel.relationship_type === link.label
        )
        setSelectedRelationship(foundRel || null)
        setSelectedNode(null)
      })

    graphRef.current = graph

    // 카메라 초기 위치 설정
    const distance = 300
    graph.cameraPosition(
      { x: 0, y: 0, z: distance },
      { x: 0, y: 0, z: 0 },
      3000
    )

    return () => {
      // Cleanup
      graphRef.current = null
    }
  }, [data, loading])

  return (
    <Box sx={{ display: 'flex', gap: 2, height }}>
      {/* 그래프 렌더링 영역 */}
      <Box
        ref={containerRef}
        sx={{
          flex: 1,
          border: '1px solid #ddd',
          borderRadius: 1,
          background: '#f5f5f5',
          position: 'relative',
        }}
      >
        {loading && (
          <Box
            sx={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              zIndex: 100,
            }}
          >
            <CircularProgress />
          </Box>
        )}
      </Box>

      {/* 정보 패널 */}
      <Box sx={{ width: 300, overflowY: 'auto' }}>
        {selectedNode && (
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              {selectedNode.label}
            </Typography>
            <Typography variant="body2" color="textSecondary" gutterBottom>
              Type: {selectedNode.type}
            </Typography>
            {selectedNode.properties && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Properties:
                </Typography>
                {Object.entries(selectedNode.properties).map(([key, value]) => (
                  <Typography key={key} variant="body2">
                    <strong>{key}:</strong> {String(value)}
                  </Typography>
                ))}
              </Box>
            )}
          </Paper>
        )}

        {selectedRelationship && (
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              {selectedRelationship.relationship_type}
            </Typography>
            <Card sx={{ mb: 2 }}>
              <CardContent sx={{ py: 1 }}>
                <Typography variant="body2">
                  <strong>From:</strong> {selectedRelationship.source_label}
                </Typography>
                <Typography variant="body2">
                  <strong>To:</strong> {selectedRelationship.target_label}
                </Typography>
              </CardContent>
            </Card>
            {selectedRelationship.properties && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Properties:
                </Typography>
                {Object.entries(selectedRelationship.properties).map(
                  ([key, value]) => (
                    <Typography key={key} variant="body2">
                      <strong>{key}:</strong> {String(value)}
                    </Typography>
                  )
                )}
              </Box>
            )}
          </Paper>
        )}

        {!selectedNode && !selectedRelationship && (
          <Paper sx={{ p: 2 }}>
            <Typography variant="body2" color="textSecondary">
              노드 또는 관계를 클릭하여 세부 정보를 확인합니다.
            </Typography>
            <Box sx={{ mt: 2 }}>
              <Typography variant="subtitle2" gutterBottom>
                그래프 통계
              </Typography>
              <Grid container spacing={1}>
                <Grid item xs={6}>
                  <Typography variant="body2">
                    <strong>Nodes:</strong> {data.stats.node_count}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2">
                    <strong>Relationships:</strong> {data.stats.relationship_count}
                  </Typography>
                </Grid>
              </Grid>
            </Box>
          </Paper>
        )}
      </Box>
    </Box>
  )
}
```

### 4.4 ReportDetail 페이지 수정

**파일:** `frontend/src/pages/ReportDetail.tsx`

```typescript
import { GraphVisualization } from '@/components/GraphVisualization'
import { GraphVisualizationResponse } from '@/api/types'

export const ReportDetailPage: React.FC = () => {
  // ... 기존 상태들
  const [graphVisualization, setGraphVisualization] = useState<GraphVisualizationResponse | null>(null)
  const [visualizationLoading, setVisualizationLoading] = useState(false)

  useEffect(() => {
    if (!reportId) {
      setError('Report ID가 없습니다.')
      setLoading(false)
      return
    }

    loadReportData()
  }, [reportId])

  const loadReportData = async () => {
    if (!reportId) return

    try {
      setLoading(true)
      setError(null)

      // Load PDF file
      const pdfBlob = await reportsApi.getReportFile(reportId)
      const url = URL.createObjectURL(pdfBlob)
      setPdfUrl(url)

      // Load graph info
      try {
        const graph = await reportsApi.getReportGraph(reportId)
        setGraphInfo(graph)
      } catch (err) {
        console.error('Failed to load graph info:', err)
      }

      // [신규] Load graph visualization data
      try {
        setVisualizationLoading(true)
        const visualization = await reportsApi.getReportGraphVisualization(reportId)
        setGraphVisualization(visualization)
      } catch (err) {
        console.error('Failed to load graph visualization:', err)
      } finally {
        setVisualizationLoading(false)
      }

      // Load vector info
      try {
        const vectors = await reportsApi.getReportVectors(reportId)
        setVectorInfo(vectors)
      } catch (err) {
        console.error('Failed to load vector info:', err)
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || '리포트를 불러오는데 실패했습니다.')
      console.error('Failed to load report:', err)
    } finally {
      setLoading(false)
    }
  }

  // TabPanel 내용 수정
  return (
    <TabPanel value={tabValue} index={0}>
      {/* 그래프 통계 카드 */}
      {graphInfo && (
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary">Nodes</Typography>
                <Typography variant="h5">{graphInfo.nodes_count}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary">Relationships</Typography>
                <Typography variant="h5">{graphInfo.relationships_count}</Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* [신규] 그래프 시각화 */}
      {graphVisualization && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" sx={{ mb: 2 }}>
            Graph Visualization
          </Typography>
          <GraphVisualization
            data={graphVisualization}
            loading={visualizationLoading}
            height={600}
          />
        </Box>
      )}

      {/* 기존 테이블들 */}
      {/* Companies, Industries, Themes 테이블 */}
    </TabPanel>
  )
}
```

---

## 5. 설치 및 라이브러리

### 5.1 백엔드 라이브러리 (이미 설치됨)
- `neo4j`: 이미 설치
- `fastapi`, `pydantic`: 이미 설치

### 5.2 프론트엔드 라이브러리

```bash
# 그래프 시각화
npm install 3d-force-graph
npm install --save-dev @types/3d-force-graph

# 또는 2D 버전 (더 가볍고 빠름)
npm install force-graph
npm install --save-dev @types/force-graph
```

---

## 6. 구현 순서

### Phase 1: 백엔드 (우선순위: HIGH)
1. ✅ GraphService 메서드 구현: `get_report_relationships()`
2. ✅ GraphService 메서드 구현: `get_report_graph_for_visualization()`
3. ✅ Pydantic 모델 추가
4. ✅ API 엔드포인트 구현: `GET /reports/{report_id}/graph/relationships`
5. ✅ 테스트 (curl, Postman)

### Phase 2: 프론트엔드 (우선순위: HIGH)
1. ✅ 라이브러리 설치
2. ✅ 타입 정의 추가
3. ✅ API 클라이언트 메서드 추가
4. ✅ GraphVisualization 컴포넌트 작성
5. ✅ ReportDetail 페이지 통합

### Phase 3: 고급 기능 (우선순위: MEDIUM)
1. 필터링 기능 (노드 타입별)
2. 줌/팬 제스처 개선
3. 검색 기능
4. 그래프 크기 최적화 (큰 그래프)

### Phase 4: 성능 최적화 (우선순위: LOW)
1. 가상화 (매우 큰 그래프)
2. 캐싱 (클라이언트)
3. 백그라운드 로딩

---

## 7. Neo4j 쿼리 최적화

### 인덱스 추가 (권장)
```cypher
CREATE INDEX IF NOT EXISTS FOR (c:Company) ON (c.ticker);
CREATE INDEX IF NOT EXISTS FOR (i:Industry) ON (i.name);
CREATE INDEX IF NOT EXISTS FOR (t:Theme) ON (t.name);
CREATE INDEX IF NOT EXISTS FOR (r:Report) ON (r.report_id);
```

### 관계 쿼리 팁
- `MATCH (n)-[r]-(m)` vs `MATCH (n)-[r]->(m)`: 방향성 차이
- `WHERE` 절로 관계 타입 필터링: `WHERE type(r) IN ['HAS_OPINION', 'HAS_TARGET_PRICE']`
- 최대 결과 제한: `LIMIT 500`으로 성능 유지

---

## 8. 테스트 케이스

### 백엔드
```python
# test_get_report_graph_relationships
# - 정상 리포트
# - 리포트 없음
# - 엔티티 없음
# - 관계 없음
# - 대량 관계
```

### 프론트엔드
```typescript
// GraphVisualization 테스트
// - 노드 클릭
// - 관계 클릭
// - 빈 그래프
// - 대량 노드
```

---

## 9. 예상 결과

### 백엔드 응답 예시
```json
{
  "report_id": "550e8400-e29b-41d4-a716-446655440000",
  "nodes": [
    {
      "id": "TSLA",
      "label": "Tesla Inc.",
      "type": "Company",
      "properties": {"market": "NASDAQ", "industry": "Automotive"}
    },
    {
      "id": "Automotive",
      "label": "Automotive",
      "type": "Industry",
      "properties": {"parent_industry": "Manufacturing"}
    }
  ],
  "relationships": [
    {
      "source_id": "TSLA",
      "source_type": "Company",
      "source_label": "Tesla Inc.",
      "target_id": "Automotive",
      "target_type": "Industry",
      "target_label": "Automotive",
      "relationship_type": "OPERATES_IN",
      "properties": {"confidence": 0.95}
    }
  ],
  "stats": {
    "node_count": 25,
    "relationship_count": 42,
    "node_types": {"Company": 5, "Industry": 3, "Theme": 2, "Opinion": 15}
  }
}
```

---

## 10. 주의사항

1. **성능**: 대량 노드(>500)는 별도 페이지 처리 고려
2. **메모리**: 3D Force Graph는 많은 메모리 소비 → 2D 버전 고려
3. **Neo4j 쿼리**: 적절한 필터로 결과 제한
4. **보안**: API 응답에 민감 정보 제외
5. **접근성**: 그래프 조작 시 키보드 지원

