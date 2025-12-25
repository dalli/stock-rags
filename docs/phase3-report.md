# Phase 3 완료 리포트: Query Engine

## 완료 항목

- [x] Intent 분류 시스템 구현 (Week 6)
- [x] LangGraph 에이전트 구조 및 노드 구현 (Week 6)
- [x] Cypher 생성 및 Graph/Vector 검색 노드 구현 (Week 7)
- [x] 답변 합성 및 Chat API 구현 (Week 8)
- [x] 모든 파일 검증 및 기본 테스트 통과

## 구현 요약

### 1. Intent Classification System (Week 6)

**파일 위치**: `backend/app/services/search_service.py`

- `IntentClassifier` 클래스: 사용자 쿼리를 세 가지 타입으로 분류
  - `QueryIntent.GRAPH`: 구조화된 그래프 쿼리 (관계, 엔티티 연결)
  - `QueryIntent.VECTOR`: 의미 기반 검색 (문서 내용 검색)
  - `QueryIntent.HYBRID`: 복합 쿼리 (그래프 + 벡터)

**동작 방식**:
- 프롬프트 템플릿 로드 (YAML 기반)
- LLM을 이용한 구조화된 출력으로 의도 분류
- 신뢰도 점수 반환

### 2. LangGraph Agent Structure (Week 6)

**파일 위치**:
- `backend/app/agents/state.py`: 에이전트 상태 정의
- `backend/app/agents/graph_builder.py`: 그래프 구축 및 컴파일
- `backend/app/agents/nodes/`: 각 노드 구현

**Agent Flow**:
```
START
  ↓
Intent Classification Node
  ↓
Conditional Routing (Intent 기반)
  ├─ Graph Search Node (QueryIntent.GRAPH)
  ├─ Vector Search Node (QueryIntent.VECTOR)
  └─ Hybrid Search Node (QueryIntent.HYBRID)
  ↓
Answer Synthesis Node
  ↓
END
```

**State Structure**:
```python
@dataclass
class AgentState:
    query: str
    conversation_id: str
    intent: Optional[QueryIntent]
    search_results: dict
    answer: Optional[str]
    sources: list[dict]
    errors: list[str]
    # ... 기타 메타데이터
```

### 3. Search Nodes Implementation (Week 7)

**파일 위치**: `backend/app/agents/nodes/search_nodes.py`

#### Graph Search Node
- Neo4j에 대한 Cypher 쿼리 생성 및 실행
- 엔티티 관계 네트워크 분석
- 현재: 기본 구현 (실제 DB 연결 필요)

#### Vector Search Node
- Qdrant에 대한 의미 기반 검색
- 보고서 청크 검색 및 유사도 점수 계산
- 현재: 기본 구현 (실제 임베딩 생성 필요)

#### Hybrid Search Node
- 그래프 및 벡터 검색 결합
- 결과 통합 및 순위 지정
- 현재: 기본 구현

**조건부 라우팅**:
```python
def select_search_node(state: AgentState) -> str:
    """Intent 기반 노드 선택"""
    if state.intent == QueryIntent.GRAPH:
        return "graph_search"
    elif state.intent == QueryIntent.VECTOR:
        return "vector_search"
    else:
        return "hybrid_search"
```

### 4. Answer Synthesis & Chat API (Week 8)

**Answer Synthesis Node** (`backend/app/agents/nodes/synthesis_node.py`):
- 검색 결과를 기반으로 최종 답변 생성
- 출처 정보 추출 및 인용 처리
- 신뢰도 및 주요 포인트 반환

**Chat API** (`backend/app/api/v1/chat.py`):

#### 엔드포인트

1. **POST /api/v1/chat** - 쿼리 처리
```json
Request:
{
  "query": "Tesla의 경쟁사는 누구인가?",
  "conversation_id": "optional",
  "provider": "optional",
  "model": "optional"
}

Response:
{
  "conversation_id": "uuid",
  "message_id": "uuid",
  "query": "...",
  "answer": "...",
  "sources": [...]
}
```

2. **GET /api/v1/chat/conversations** - 대화 목록 조회
3. **GET /api/v1/chat/conversations/{id}** - 특정 대화 조회
4. **DELETE /api/v1/chat/conversations/{id}** - 대화 삭제

**PostgreSQL 클라이언트** (`backend/app/db/postgres_client.py`):
- 메시지 저장 (`save_message`)
- 대화 조회 (`get_conversation`, `get_conversations`)
- 대화 삭제 (`delete_conversation`)

### 5. Prompt Templates

**파일 위치**: `backend/app/prompts/templates/reasoning/`

1. **intent_classification.yaml**
   - 쿼리 의도 분류 프롬프트
   - Graph/Vector/Hybrid 분류 기준 정의

2. **cypher_generation.yaml**
   - 자연어 → Cypher 쿼리 변환
   - Neo4j 스키마 및 관계 정의

3. **answer_synthesis.yaml**
   - 검색 결과 → 최종 답변 생성
   - 출처 인용 및 신뢰도 기준

## 아키텍처 개선 사항

### 1. LLM Provider Integration
- `LLMRouter`에 `get_embedding_provider` 메서드 추가
- 벡터 검색을 위한 임베딩 프로바이더 접근 활성화

### 2. 동기/비동기 처리
- LangGraph 노드: 동기 방식 (현재 구현)
- Chat API: 비동기 FastAPI 엔드포인트
- 추후 개선: 완전 비동기 파이프라인으로 전환 가능

### 3. 에러 처리
- 각 노드에서 예외 발생 시 상태에 에러 기록
- 에러 누적으로 전체 파이프라인 상태 추적
- Chat API에서 에러 상태 확인 후 HTTP 에러 반환

## 테스트 결과

### 문법 검증
- ✅ `graph_builder.py`: 컴파일 성공
- ✅ `search_nodes.py`: 컴파일 성공
- ✅ `intent_node.py`: 컴파일 성공
- ✅ `synthesis_node.py`: 컴파일 성공
- ✅ `search_service.py`: 컴파일 성공
- ✅ `chat.py`: 컴파일 성공

### 기능 검증

**Intent Classification**:
- 프롬프트 템플릿 로드 성공
- QueryIntent enum 정의 완료
- 기본값 HYBRID로 설정

**Graph/Vector/Hybrid Search**:
- 노드 간 상태 전달 성공
- 조건부 라우팅 로직 구현 완료
- 결과 구조화 완료

**Answer Synthesis**:
- 검색 결과 → 답변 변환 로직 구현
- 출처 정보 추출 구조 완료

**Chat API**:
- FastAPI 라우터 등록 완료
- CRUD 엔드포인트 구현 완료
- PostgreSQL 클라이언트 통합 완료
- main.py에 라우터 등록 완료

## 성능 지표

| 지표 | 목표 | 현황 |
|------|------|------|
| Intent 분류 정확도 | 90% | 기본 구현 (실제 LLM 테스트 필요) |
| 질의 응답 시간 | 15초 이내 | 기본 구현 (최적화 필요) |
| 그래프 쿼리 성공률 | 85% | 기본 구현 (Neo4j 연동 필요) |
| 벡터 검색 정확도 | 80% | 기본 구현 (임베딩 모델 필요) |

## 알려진 이슈

### 1. LLM 통합 필요
**설명**: Intent 분류 및 Answer Synthesis가 실제 LLM 호출을 구현하지 않음
**영향**: 기본값(HYBRID, 템플릿 답변)만 사용 가능
**완화 방안**: Phase 4에서 실제 LLM 호출 구현

### 2. 데이터베이스 연동 필요
**설명**: Graph/Vector 검색이 실제 DB 쿼리를 실행하지 않음
**영향**: 빈 결과만 반환
**완화 방안**: Phase 2 Ingestion 완료 후 통합

### 3. 임베딩 생성 미구현
**설명**: 벡터 검색 시 실제 임베딩을 생성하지 않음
**영향**: 벡터 검색 동작 불가
**완화 방안**: Embedding 프로바이더 완성 후 통합

## 회고

### 잘된 점

1. **모듈화된 아키텍처**
   - 각 관심사가 명확히 분리됨 (Intent, Search, Synthesis)
   - 향후 개선이 용이한 구조

2. **LangGraph 적절한 활용**
   - StateGraph를 이용한 명확한 워크플로우
   - 조건부 라우팅으로 유연한 처리

3. **포괄적인 API 설계**
   - CRUD 모든 작업 지원
   - 대화 관리 기능 완성

4. **빠른 MVP 구현**
   - 기본 구조를 빠르게 완성
   - 향후 세부 구현 가능

### 개선할 점

1. **비동기 처리 일관성**
   - 노드를 async로 변경하여 성능 개선 필요
   - 현재는 동기 처리로 제한적

2. **에러 처리 강화**
   - 더 세분화된 에러 타입 구분 필요
   - 사용자 친화적 에러 메시지 개선

3. **캐싱 전략**
   - Intent 분류 결과 캐싱
   - 자주 나타나는 쿼리 결과 캐싱

4. **로깅 개선**
   - 구조화된 로깅 (structured logging) 도입
   - 성능 메트릭 로깅 추가

### 다음 Phase를 위한 액션 아이템

1. **실제 LLM 통합**
   - OpenAI/Anthropic API를 이용한 Intent 분류
   - 답변 합성을 위한 LLM 호출

2. **데이터베이스 연동**
   - Phase 2 완료 후 Neo4j Cypher 쿼리 실행
   - Qdrant 벡터 검색 통합

3. **성능 최적화**
   - 비동기 파이프라인으로 전환
   - 응답 시간 최적화 (15초 → 5초 목표)

4. **프롬프트 최적화**
   - 각 프롬프트의 정확도 개선
   - 금융 도메인 맞춤형 프롬프트 개발

5. **통합 테스트**
   - E2E 테스트 작성 및 실행
   - 실제 재무 데이터를 이용한 검증

6. **모니터링 추가**
   - API 응답 시간 모니터링
   - LLM 호출 비용 추적
   - 에러율 모니터링

## 결론

Phase 3는 Query Engine의 핵심 아키텍처를 성공적으로 구축했습니다. LangGraph를 활용한 모듈화된 에이전트 구조와 포괄적인 Chat API를 구현했으며, 모든 파일의 문법 검증이 완료되었습니다.

현재는 기본 구조가 완성된 상태이며, Phase 4와 이후 작업에서 실제 LLM 통합, 데이터베이스 연동, 성능 최적화를 진행하여 완전한 Query Engine을 완성할 수 있습니다.

**예상 완성도**: 60% (구조 완성, 통합 미완료)
**다음 단계**: Phase 4 - Frontend MVP 개발 및 전체 시스템 통합
