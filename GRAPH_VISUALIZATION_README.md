# 그래프 시각화 구현 가이드

## 📄 생성된 문서

### 1. **IMPLEMENTATION_SUMMARY.md** (👈 먼저 읽기)
   - **목적**: 전체 구현 계획의 요약
   - **내용**:
     - 목표 및 아키텍처
     - 핵심 기술 스택
     - 백엔드 구현 범위 (데이터 모델, 메서드, API)
     - 프론트엔드 구현 범위 (타입, 컴포넌트, 통합)
     - 라이브러리 설치
     - 성능 최적화
     - 테스트 방법
     - 구현 체크리스트
   - **특징**: 한 눈에 전체 구조를 파악 가능

### 2. **IMPLEMENTATION_PLAN_GRAPH_VISUALIZATION.md** (상세 구현 계획)
   - **목적**: 각 파일별 상세 코드 구현
   - **내용**:
     - 개요 및 현황
     - 아키텍처 설계 (데이터 흐름)
     - 백엔드 구현
       - Pydantic 모델 (완전한 코드)
       - GraphService 메서드 (완전한 코드)
       - API 엔드포인트 (완전한 코드)
     - 프론트엔드 구현
       - 타입 정의 (완전한 코드)
       - API 클라이언트 (완전한 코드)
       - GraphVisualization 컴포넌트 (완전한 코드)
       - ReportDetail 페이지 수정 (완전한 코드)
     - 라이브러리 설치
     - 구현 순서 (Phase 1-4)
     - Neo4j 쿼리 최적화
     - 테스트 케이스
     - 예상 결과
     - 주의사항
   - **특징**: 복사-붙여넣기 가능한 완전한 코드 제공

### 3. **DETAILED_RELATIONSHIP_DESIGN.md** (관계 데이터 설계)
   - **목적**: 관계 데이터 생성의 상세 기술 설계
   - **내용**:
     - 개요 및 전체 흐름도
     - PostgreSQL 단계 (Entity 모델, 쿼리)
     - Neo4j 단계 (그래프 구조, 3개 병렬 쿼리)
     - 데이터 변환 단계 (NodeAggregator 클래스)
     - 최적화 전략
       - 대용량 관계 처리 (페이지네이션)
       - 노드 타입별 필터링
       - 캐싱 전략
     - 에러 처리
     - 프론트엔드 데이터 변환
     - 성능 벤치마크
     - 테스트 데이터 (Neo4j)
     - 체크리스트
   - **특징**: 관계 데이터 생성의 가장 핵심적인 기술 내용 포함

---

## 📊 문서 선택 가이드

### 문서를 읽는 순서

```
1단계: IMPLEMENTATION_SUMMARY.md 읽기 (10분)
  └─ 전체 구조 이해, 개요 파악

2단계: 백엔드 구현
  ├─ IMPLEMENTATION_PLAN_GRAPH_VISUALIZATION.md [백엔드 섹션] 읽기 (30분)
  └─ DETAILED_RELATIONSHIP_DESIGN.md [Neo4j 쿼리, NodeAggregator] 읽기 (30분)
      └─ 코드 구현

3단계: 프론트엔드 구현
  ├─ IMPLEMENTATION_PLAN_GRAPH_VISUALIZATION.md [프론트엔드 섹션] 읽기 (30분)
  └─ 코드 구현

4단계: 테스트 및 배포
  ├─ IMPLEMENTATION_SUMMARY.md [테스트 섹션] 참고
  └─ 통합 테스트 및 배포
```

---

## 🎯 핵심 포인트

### 백엔드의 핵심 개념

1. **Entity 추출** (PostgreSQL)
   ```
   Report → Entities → Company/Industry/Theme 식별자 추출
   ```

2. **관계 조회** (Neo4j) - 3개 쿼리 병렬 실행
   ```
   Company -[rel]-> (* )
   Industry -[rel]-> (* )
   Theme -[rel]-> (* )
   ```

3. **노드 중복 제거** (Python)
   ```
   NodeAggregator: 같은 노드는 한 번만 표시
   ```

4. **데이터 제공** (FastAPI)
   ```
   GET /reports/{report_id}/graph/relationships
   → GraphVisualizationResponse (JSON)
   ```

### 프론트엔드의 핵심 개념

1. **타입 정의**
   ```typescript
   GraphNode, GraphRelationship, GraphVisualizationResponse
   ```

2. **Force Graph 데이터 변환**
   ```
   API Response → Force Graph 형식 변환
   ```

3. **3D 시각화**
   ```
   ForceGraph3D 라이브러리로 렌더링
   ```

4. **인터랙션**
   ```
   노드/관계 클릭 → 상세 정보 표시
   ```

---

## 🔄 데이터 흐름 예시

### 리포트 ID: "550e8400-e29b-41d4-a716-446655440000"

#### 1단계: PostgreSQL 쿼리
```sql
SELECT entity_type, name, properties
FROM entities
WHERE report_id = '550e8400-e29b-41d4-a716-446655440000'
```

**결과:**
```
Company: AAPL, {ticker: "AAPL", market: "NASDAQ"}
Company: MSFT, {ticker: "MSFT", market: "NASDAQ"}
Industry: Technology, {parent: "Information Technology"}
Theme: AI, {keywords: ["AI", "ML"]}
```

#### 2단계: Neo4j 쿼리 (3개 병렬)
```cypher
MATCH (c:Company)
WHERE c.ticker IN ["AAPL", "MSFT"]
MATCH (c)-[rel]-(connected)
RETURN ...
```

**결과:**
```
AAPL -[OPERATES_IN]-> Technology
AAPL -[MENTIONED_WITH]-> AI
MSFT -[OPERATES_IN]-> Technology
MSFT -[MENTIONED_WITH]-> Cloud
...
```

#### 3단계: 노드 중복 제거
```
Nodes: {
  "Company:AAPL": {id: "AAPL", label: "Apple", type: "Company"},
  "Company:MSFT": {id: "MSFT", label: "Microsoft", type: "Company"},
  "Industry:Technology": {id: "Technology", label: "Technology", type: "Industry"},
  "Theme:AI": {id: "AI", label: "Artificial Intelligence", type: "Theme"}
}

Relationships: [
  {source: "AAPL", target: "Technology", type: "OPERATES_IN"},
  {source: "AAPL", target: "AI", type: "MENTIONED_WITH"},
  ...
]
```

#### 4단계: API 응답 (JSON)
```json
{
  "report_id": "550e8400-e29b-41d4-a716-446655440000",
  "nodes": [
    {"id": "AAPL", "label": "Apple Inc.", "type": "Company"},
    {"id": "MSFT", "label": "Microsoft Corp.", "type": "Company"},
    {"id": "Technology", "label": "Technology", "type": "Industry"},
    {"id": "AI", "label": "Artificial Intelligence", "type": "Theme"}
  ],
  "relationships": [
    {
      "source_id": "AAPL",
      "source_type": "Company",
      "source_label": "Apple Inc.",
      "target_id": "Technology",
      "target_type": "Industry",
      "target_label": "Technology",
      "relationship_type": "OPERATES_IN"
    },
    ...
  ],
  "stats": {
    "node_count": 4,
    "relationship_count": 5,
    "node_types": {"Company": 2, "Industry": 1, "Theme": 1}
  }
}
```

#### 5단계: Force Graph 렌더링
```
사용자 브라우저에서 3D 그래프 표시
마우스로 회전, 줌 가능
노드 클릭 → 상세 정보 표시
```

---

## 🚀 빠른 시작

### 1. 백엔드 구현 (30분)

```bash
# 1. IMPLEMENTATION_PLAN_GRAPH_VISUALIZATION.md의 백엔드 섹션 읽기
# 2. backend/app/api/v1/reports.py에 추가:
#    - GraphNodeInfo, GraphRelationshipInfo, GraphVisualizationResponse 클래스 추가
#
# 3. backend/app/services/graph_service.py에 추가:
#    - get_report_relationships() 메서드
#    - get_report_graph_for_visualization() 메서드
#
# 4. backend/app/api/v1/reports.py에 추가:
#    - GET /reports/{report_id}/graph/relationships 엔드포인트
#
# 5. 테스트:
curl http://localhost:8000/api/v1/reports/{report_id}/graph/relationships
```

### 2. 프론트엔드 구현 (30분)

```bash
# 1. 라이브러리 설치
npm install 3d-force-graph
npm install --save-dev @types/3d-force-graph

# 2. frontend/src/api/types.ts에 추가:
#    - GraphNode, GraphRelationship, GraphVisualizationResponse 타입

# 3. frontend/src/api/reports.ts에 추가:
#    - getReportGraphVisualization() 메서드

# 4. frontend/src/components/GraphVisualization.tsx 생성:
#    - GraphVisualization 컴포넌트 구현

# 5. frontend/src/pages/ReportDetail.tsx 수정:
#    - GraphVisualization 컴포넌트 통합
```

### 3. 테스트 (15분)

```bash
# 1. 브라우저에서 리포트 상세보기 페이지 열기
# 2. "그래프 시각화" 섹션 확인
# 3. 노드 클릭, 관계 클릭 확인
# 4. 콘솔에서 에러 확인
```

---

## ⚙️ 선택사항 (차후 개선)

### Phase 3: 고급 기능
- [ ] 노드 타입별 필터링
- [ ] 줌/팬 제스처 개선
- [ ] 검색 기능
- [ ] 그래프 내보내기 (SVG, PNG)

### Phase 4: 성능 최적화
- [ ] 가상화 (500+ 노드)
- [ ] 캐싱 (클라이언트)
- [ ] 백그라운드 로딩
- [ ] 페이지네이션

---

## 📚 참고 자료

### Neo4j 관계 타입 (현재 사용 중)
- `HAS_OPINION`: Company → Opinion
- `HAS_TARGET_PRICE`: Company → TargetPrice
- `OPERATES_IN`: Company → Industry
- `MENTIONED_WITH`: Company → Theme
- `PARENT_OF`: Industry → Industry (상위 산업)

### Pydantic 모델 참고
```python
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class GraphNodeInfo(BaseModel):
    id: str
    label: str
    type: str
    properties: Dict[str, Any] = {}

class GraphRelationshipInfo(BaseModel):
    source_id: str
    source_type: str
    source_label: str
    target_id: str
    target_type: str
    target_label: str
    relationship_type: str
    properties: Dict[str, Any] = {}

class GraphVisualizationResponse(BaseModel):
    report_id: str
    nodes: List[GraphNodeInfo]
    relationships: List[GraphRelationshipInfo]
    stats: Dict[str, Any]
```

---

## ❓ 자주 묻는 질문

### Q1: 노드가 너무 많으면 어떻게 하나요?
**A:** DETAILED_RELATIONSHIP_DESIGN.md의 "대용량 관계 처리" 섹션 참고. 페이지네이션 또는 필터링 사용.

### Q2: 관계가 표시되지 않으면?
**A:**
1. Neo4j에서 관계가 실제로 존재하는지 확인
2. API 응답에서 relationships 배열이 비어있는지 확인
3. 브라우저 콘솔에서 에러 메시지 확인

### Q3: 그래프가 너무 느리면?
**A:**
1. Neo4j 인덱스 생성 확인: `CREATE INDEX IF NOT EXISTS FOR (c:Company) ON (c.ticker);`
2. LIMIT 값 조정
3. 필터링 추가 (특정 노드 타입만)

### Q4: 프론트엔드 라이브러리는 어떤 것을 선택하나요?
**A:**
- **3d-force-graph**: 3D, 더 시각적, 더 느림 (권장)
- **force-graph**: 2D, 더 가볍고 빠름, 더 지원 잘 됨

---

## ✅ 체크리스트

### 구현 전
- [ ] 세 문서를 모두 읽음
- [ ] 전체 데이터 흐름 이해
- [ ] 백엔드/프론트엔드 구현 범위 파악

### 백엔드 구현
- [ ] Pydantic 모델 추가
- [ ] GraphService 메서드 구현
- [ ] API 엔드포인트 추가
- [ ] curl로 API 테스트

### 프론트엔드 구현
- [ ] 라이브러리 설치
- [ ] 타입 정의 추가
- [ ] API 클라이언트 메서드 추가
- [ ] GraphVisualization 컴포넌트 작성
- [ ] ReportDetail 페이지 통합

### 테스트
- [ ] 브라우저에서 그래프 표시 확인
- [ ] 노드/관계 클릭 확인
- [ ] 콘솔 에러 없음 확인

---

## 📞 문제 해결

### Neo4j 쿼리가 느린 경우
```cypher
-- 인덱스 확인
SHOW INDEXES

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS FOR (c:Company) ON (c.ticker);
CREATE INDEX IF NOT EXISTS FOR (i:Industry) ON (i.name);
CREATE INDEX IF NOT EXISTS FOR (t:Theme) ON (t.name);
```

### API 응답이 비어있는 경우
```python
# GraphService.get_report_relationships() 로그 추가
logger.info(f"Company tickers: {company_tickers}")
logger.info(f"Industry names: {industry_names}")
logger.info(f"Theme names: {theme_names}")
logger.info(f"Relationships found: {len(relationships_data)}")
```

### 그래프가 렌더링되지 않는 경우
```typescript
// 브라우저 콘솔 확인
console.log('Graph data:', graphVisualization)
console.log('Force graph instance:', graphRef.current)
```

---

## 🎓 학습 리소스

### Neo4j
- [Neo4j Cypher 문서](https://neo4j.com/docs/cypher-manual/current/)
- [Neo4j 성능 최적화](https://neo4j.com/docs/operations-manual/current/performance/)

### Force Graph
- [3d-force-graph GitHub](https://github.com/vasturiano/3d-force-graph)
- [force-graph GitHub](https://github.com/vasturiano/force-graph)

### React + TypeScript
- [React 공식 문서](https://react.dev)
- [TypeScript 핸드북](https://www.typescriptlang.org/docs/)

---

**작성일**: 2024년 12월
**최종 업데이트**: 생성된 날짜
**상태**: 구현 준비 완료

