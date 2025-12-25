# [PRD] GraphRAG 기반 증권 리포트 심층 분석 서비스

**버전:** 1.0  
**상태:** Draft  
**작성일:** 2025년 1월  
**주요 기술:** Python, LangChain, LangGraph, Neo4j, Vector DB, Docker

---

## 목차

1. [Executive Summary](#1-executive-summary)
2. [프로젝트 개요](#2-프로젝트-개요)
3. [타겟 유저](#3-타겟-유저)
4. [리포트 유형 분류 및 처리 전략](#4-리포트-유형-분류-및-처리-전략)
5. [핵심 기능](#5-핵심-기능-core-features)
6. [기술 스택](#6-기술-스택)
7. [시스템 아키텍처](#7-시스템-아키텍처)
8. [Docker Compose 개발 환경](#8-docker-compose-개발-환경)
9. [API 설계](#9-api-설계)
10. [데이터 모델 (온톨로지)](#10-데이터-모델-온톨로지)
11. [추가 고려사항](#11-추가-고려사항)
12. [사용자 시나리오](#12-사용자-시나리오)
13. [개발 로드맵](#13-개발-로드맵)
14. [리스크 및 완화 방안](#14-리스크-및-완화-방안)
15. [성공 지표 (KPI)](#15-성공-지표-kpi)
16. [용어 정의](#16-용어-정의)
17. [참고 문서](#17-참고-문서)

---

## 1. Executive Summary

본 문서는 지식 그래프(Knowledge Graph)와 벡터 검색을 결합한 하이브리드 RAG 시스템을 통해 증권사 리포트의 심층 분석을 제공하는 서비스의 제품 요구사항을 정의합니다.

### 1.1 핵심 가치 제안

- **연결된 인사이트(Connected Insight):** 단순 키워드 검색이 아닌, 산업 밸류체인과 재무 인과관계를 추론하는 분석 도구
- **시계열 추적:** 목표주가, 투자의견의 변화 이력을 추적하여 트렌드 분석 지원
- **다중 리포트 통합 분석:** 여러 증권사 리포트를 통합하여 컨센서스 및 차별화된 시각 도출

### 1.2 기대 효과

- 리포트 분석 시간 70% 단축
- 기업 간 연관관계 파악을 통한 투자 인사이트 발굴
- 섹터별 투자의견 트렌드의 시각적 이해

---

## 2. 프로젝트 개요

### 2.1 배경

기존 Vector RAG 방식은 개별 문서 내 유사도 기반 검색에는 효과적이나, 여러 리포트에 흩어진 기업-산업 간의 상관관계나 시계열적 수치 변화를 파악하는 데 근본적인 한계가 있습니다. 증권 분석에서는 공급망 관계, 경쟁사 분석, 산업 트렌드 등 엔티티 간의 관계 파악이 핵심이며, 이를 위해 지식 그래프 기반 접근이 필요합니다.

### 2.2 목적

1. 지식 그래프를 활용하여 리포트 내 엔티티(기업, 지표, 산업) 간의 관계를 구조화
2. LangGraph 에이전트를 통해 전문가 수준의 심층 답변 제공
3. 다양한 유형의 증권 리포트를 통합 관리하고 분석
4. 개발 환경에서 Docker Compose를 통한 손쉬운 배포 및 테스트 지원

### 2.3 범위 (Scope)

#### In Scope (MVP)

- PDF 리포트 업로드 및 파싱
- 지식 그래프 자동 구축 (엔티티/관계 추출)
- 하이브리드 검색 (Graph + Vector)
- 자연어 질의응답
- 기본 그래프 시각화
- Docker Compose 개발 환경

#### Out of Scope (향후 버전)

- 실시간 주가 데이터 연동
- 백테스팅 기능
- 알림 서비스
- 멀티 테넌시

---

## 3. 타겟 유저

| 유저 유형 | 특성 | 주요 니즈 |
|-----------|------|-----------|
| **개인 투자자** | 수많은 리포트를 읽을 시간 부족 | 핵심 요약과 관계망 빠른 파악 |
| **전업 투자자** | 특정 섹터 심층 분석 필요 | 섹터 내 기업 간 영향력 시각적 확인 |
| **리서치 애널리스트** | 대량의 리포트 커버 필요 | 경쟁사 대비 차별화된 인사이트 |
| **펀드 매니저** | 포트폴리오 내 기업 모니터링 | 투자의견 변동 추적 및 알림 |

---

## 4. 리포트 유형 분류 및 처리 전략

증권사 리포트는 목적과 내용에 따라 다양한 유형으로 분류되며, 각 유형별로 추출해야 할 핵심 정보와 처리 전략이 다릅니다.

### 4.1 리포트 유형별 특성

| 리포트 유형 | 주요 내용 | 핵심 추출 정보 | 갱신 주기 |
|-------------|----------|----------------|-----------|
| **시황 리포트** | 시장 전반 동향, 지수 전망 | 시장 센티먼트, 주요 이벤트 | 일간/주간 |
| **투자정보 리포트** | 투자 전략, 포트폴리오 제안 | 추천 종목, 비중 조절 | 수시 |
| **종목 분석 리포트** | 개별 기업 실적, 밸류에이션 | 목표주가, 투자의견, 재무지표 | 실적 발표 시 |
| **산업 분석 리포트** | 산업 트렌드, 밸류체인 분석 | 산업 전망, 수혜/피해주 | 분기/반기 |
| **경제 분석 리포트** | 거시경제 지표, 정책 분석 | 금리, 환율, GDP 전망 | 월간/분기 |

### 4.2 리포트 유형별 온톨로지 확장

각 리포트 유형에 맞는 특화된 노드와 엣지를 정의하여 정보 추출의 정확도를 높입니다.

#### 종목 분석 리포트 온톨로지

- **노드:** Company, TargetPrice, InvestmentOpinion, FinancialMetric, Analyst, SecurityFirm
- **엣지:** HAS_TARGET_PRICE, HAS_OPINION, COVERS, PUBLISHES, COMPETES_WITH

#### 산업 분석 리포트 온톨로지

- **노드:** Industry, Theme, SupplyChain, MarketTrend
- **엣지:** BELONGS_TO, SUPPLIES_TO, BENEFITS_FROM, AFFECTED_BY

#### 경제 분석 리포트 온톨로지

- **노드:** MacroIndicator, Policy, Country, Forecast
- **엣지:** INFLUENCES, FORECASTS, IMPLEMENTS

---

## 5. 핵심 기능 (Core Features)

### 5.1 온톨로지 기반 지식 추출 (Extraction)

#### PDF 파싱 파이프라인

- **텍스트 추출:** PyMuPDF, pdfplumber를 활용한 텍스트 및 레이아웃 추출
- **테이블 추출:** Camelot, tabula-py를 활용한 재무제표 및 데이터 테이블 추출
- **이미지/차트 처리:** Vision LLM을 활용한 차트 데이터 추출 (Optional)
- **메타데이터 추출:** 발행일, 증권사명, 애널리스트명 자동 인식

#### 엔티티/관계 추출

- LLMGraphTransformer를 활용한 구조화된 정보 추출
- 리포트 유형 자동 분류 후 해당 온톨로지 적용
- 신뢰도 점수(Confidence Score) 부여로 추출 품질 관리

#### 엔티티 정규화 (Entity Resolution)

- 유사 명칭 통합: '삼성전자', '삼전', 'Samsung Electronics' → 단일 노드
- 종목코드 기반 정규화: KRX 종목코드 매핑
- 별칭(Alias) 관리: 다양한 표기법을 노드 속성으로 저장

### 5.2 LangGraph 기반 지능형 에이전트 (Reasoning)

#### 질문 의도 파악 (Intent Classification)

- **사실 확인형:** "삼성전자 목표주가가 뭐야?" → Vector Search
- **관계 추론형:** "HBM 관련주 중 투자의견 상향된 기업은?" → Graph Query
- **복합형:** "반도체 섹터에서 실적 대비 저평가된 종목과 그 이유" → Hybrid

#### 하이브리드 검색 전략

| 검색 유형 | 적용 쿼리 예시 | 처리 방식 |
|-----------|----------------|-----------|
| **Graph Store** | 공급망에 속한 업체들의 투자의견 | Cypher 쿼리로 관계 탐색 |
| **Vector Store** | 리포트에서 언급된 매수 근거 | 시맨틱 유사도 검색 |
| **Hybrid** | AI 반도체 수혜주 분석과 전망 | Graph + Vector 결과 병합 |

#### Multi-hop Reasoning

복잡한 질문에 대해 여러 단계의 추론을 수행하여 심층적인 답변을 생성합니다.

예: "HBM 관련주 중 투자의견 상향 기업" 
→ HBM 노드 탐색 → 연결된 기업 노드 수집 → 각 기업의 투자의견 변화 분석 → 상향 사유 텍스트 추출

### 5.3 인터랙티브 지식 맵 (Visualization)

- **그래프 시각화:** 답변과 관련된 엔티티 간 관계망을 인터랙티브 그래프로 제공
- **시계열 추이:** 목표주가 및 투자의견 변경 이력 타임라인
- **필터링:** 산업, 기간, 투자의견 유형별 필터
- **드릴다운:** 노드 클릭 시 상세 정보 및 연관 리포트 표시

---

## 6. 기술 스택

| 구분 | 기술 | 비고 |
|------|------|------|
| Language | Python 3.11+ | Type hints, async/await 활용 |
| Orchestration | LangChain, LangGraph | 에이전트 워크플로우 제어 |
| LLM | GPT-4o / Claude 3.5 Sonnet | 구조화 추출 및 추론 |
| Database (Graph) | Neo4j 5.x | 지식 그래프, Cypher 쿼리 |
| Database (Vector) | Chroma / Qdrant | 시맨틱 검색용 |
| Database (Cache) | Redis 7.x | 세션, 캐싱 |
| Backend Framework | FastAPI | 비동기 API |
| Task Queue | Celery + Redis | PDF 처리 비동기화 |
| Frontend | React + TypeScript | React-force-graph, Recharts |
| Container | Docker, Docker Compose | 개발 환경 구성 |
| Monitoring | Prometheus + Grafana | 메트릭 수집 및 시각화 |

---

## 7. 시스템 아키텍처

### 7.1 High-Level Architecture

시스템은 크게 Ingestion Pipeline과 Inference Pipeline으로 구성됩니다.

#### Ingestion Pipeline

```
PDF Upload → File Storage → Celery Worker → PDF Parser → LLM Extractor → Graph Builder → Neo4j / Vector DB
```

#### Inference Pipeline

```
User Query → API Gateway → LangGraph Agent → Intent Router → [Graph Query / Vector Search] → Result Merger → LLM Synthesizer → Response Generator
```

### 7.2 서비스 구성

| 서비스 | 포트 | 역할 |
|--------|------|------|
| api-gateway | 8000 | FastAPI 기반 REST API 제공 |
| worker | - | Celery 워커, PDF 처리 및 그래프 구축 |
| neo4j | 7474, 7687 | 지식 그래프 저장소 |
| qdrant | 6333 | 벡터 검색 엔진 |
| redis | 6379 | 메시지 브로커 및 캐시 |
| frontend | 3000 | React 웹 애플리케이션 |
| prometheus | 9090 | 메트릭 수집 |
| grafana | 3001 | 모니터링 대시보드 |

---

## 8. Docker Compose 개발 환경

### 8.1 디렉토리 구조

```
graphrag-securities/
├── docker-compose.yml
├── docker-compose.override.yml  # 개발용 오버라이드
├── .env.example
├── backend/
│   ├── Dockerfile
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── core/
│   │   ├── services/
│   │   └── workers/
│   └── requirements.txt
├── frontend/
│   ├── Dockerfile
│   └── src/
├── config/
│   ├── neo4j/
│   ├── prometheus/
│   └── grafana/
├── data/  # 볼륨 마운트용
└── scripts/
```

### 8.2 환경 변수 설정

`.env` 파일에서 관리되는 주요 환경 변수:

| 변수명 | 설명 | 예시 값 |
|--------|------|---------|
| OPENAI_API_KEY | OpenAI API 키 | sk-xxx... |
| ANTHROPIC_API_KEY | Anthropic API 키 | sk-ant-xxx... |
| NEO4J_URI | Neo4j 연결 URI | bolt://neo4j:7687 |
| NEO4J_USER | Neo4j 사용자명 | neo4j |
| NEO4J_PASSWORD | Neo4j 비밀번호 | password |
| REDIS_URL | Redis 연결 URL | redis://redis:6379 |
| QDRANT_HOST | Qdrant 호스트 | qdrant |
| QDRANT_PORT | Qdrant 포트 | 6333 |

### 8.3 Docker Compose 파일

```yaml
# docker-compose.yml
version: '3.8'

services:
  api-gateway:
    build: ./backend
    ports:
      - "8000:8000"
    depends_on:
      - neo4j
      - qdrant
      - redis
    env_file: .env
    volumes:
      - ./data/uploads:/app/uploads
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  worker:
    build: ./backend
    command: celery -A app.workers worker -l info -c 2
    depends_on:
      - redis
      - neo4j
      - qdrant
    env_file: .env
    volumes:
      - ./data/uploads:/app/uploads

  neo4j:
    image: neo4j:5.15-community
    ports:
      - "7474:7474"
      - "7687:7687"
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
    environment:
      - NEO4J_AUTH=${NEO4J_USER}/${NEO4J_PASSWORD}
      - NEO4J_PLUGINS=["apoc"]
    healthcheck:
      test: ["CMD", "neo4j", "status"]
      interval: 30s
      timeout: 10s
      retries: 5

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage
    environment:
      - QDRANT__SERVICE__GRPC_PORT=6334

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - api-gateway
    environment:
      - REACT_APP_API_URL=http://localhost:8000

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./config/prometheus:/etc/prometheus
      - prometheus_data:/prometheus

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    volumes:
      - ./config/grafana:/etc/grafana/provisioning
      - grafana_data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin

volumes:
  neo4j_data:
  neo4j_logs:
  qdrant_data:
  redis_data:
  prometheus_data:
  grafana_data:
```

### 8.4 개발용 오버라이드

```yaml
# docker-compose.override.yml
version: '3.8'

services:
  api-gateway:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    volumes:
      - ./backend/app:/app/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    environment:
      - DEBUG=true

  worker:
    volumes:
      - ./backend/app:/app/app
    command: watchmedo auto-restart --directory=/app --pattern=*.py --recursive -- celery -A app.workers worker -l info

  frontend:
    volumes:
      - ./frontend/src:/app/src
    environment:
      - CHOKIDAR_USEPOLLING=true
```

### 8.5 개발 환경 실행 명령

```bash
# 환경 변수 설정
cp .env.example .env
# .env 파일 편집하여 API 키 등 설정

# 전체 서비스 시작
docker compose up -d

# 로그 확인
docker compose logs -f api-gateway

# 개발 모드 (핫 리로드)
docker compose -f docker-compose.yml -f docker-compose.override.yml up -d

# 특정 서비스만 재시작
docker compose restart api-gateway

# 서비스 재빌드
docker compose build --no-cache api-gateway

# 전체 종료 및 볼륨 삭제
docker compose down -v
```

### 8.6 Health Check 엔드포인트

- **API Gateway:** http://localhost:8000/health
- **Neo4j Browser:** http://localhost:7474
- **Qdrant Dashboard:** http://localhost:6333/dashboard
- **Grafana:** http://localhost:3001 (admin/admin)
- **Prometheus:** http://localhost:9090

---

## 9. API 설계

### 9.1 주요 엔드포인트

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/v1/reports/upload` | PDF 리포트 업로드 |
| GET | `/api/v1/reports/{id}/status` | 처리 상태 조회 |
| GET | `/api/v1/reports` | 리포트 목록 조회 |
| DELETE | `/api/v1/reports/{id}` | 리포트 삭제 |
| POST | `/api/v1/chat` | 질의응답 (스트리밍) |
| GET | `/api/v1/chat/history` | 대화 이력 조회 |
| GET | `/api/v1/graph/entities` | 엔티티 목록 조회 |
| GET | `/api/v1/graph/entities/{id}` | 엔티티 상세 조회 |
| GET | `/api/v1/graph/relations` | 관계망 조회 |
| GET | `/api/v1/companies/{ticker}/timeline` | 투자의견 이력 조회 |
| GET | `/api/v1/sectors/{name}/analysis` | 섹터 분석 조회 |
| GET | `/api/v1/themes` | 테마 목록 조회 |

### 9.2 API 요청/응답 예시

#### 리포트 업로드

```bash
POST /api/v1/reports/upload
Content-Type: multipart/form-data

file: [PDF 파일]
report_type: "stock_analysis"  # optional, 자동 감지
```

```json
{
  "id": "rpt_abc123",
  "status": "processing",
  "filename": "삼성전자_실적분석_20250115.pdf",
  "created_at": "2025-01-15T10:30:00Z"
}
```

#### 질의응답

```bash
POST /api/v1/chat
Content-Type: application/json

{
  "query": "HBM 관련주 중 최근 투자의견이 상향된 기업들과 그 이유를 알려줘",
  "stream": true
}
```

```json
{
  "answer": "HBM 관련주 중 최근 투자의견이 상향된 기업은...",
  "sources": [
    {"report_id": "rpt_abc123", "title": "SK하이닉스 분석", "page": 3}
  ],
  "graph_data": {
    "nodes": [...],
    "edges": [...]
  }
}
```

### 9.3 WebSocket 이벤트

- **chat.stream:** 실시간 답변 스트리밍
- **report.progress:** 리포트 처리 진행률
- **graph.update:** 그래프 업데이트 알림

---

## 10. 데이터 모델 (온톨로지)

### 10.1 노드 (Node) 정의

| 노드 유형 | 속성 | 예시 |
|-----------|------|------|
| Company | ticker, name, aliases, sector, market_cap | 삼성전자 |
| Industry | name, description, parent_industry | 반도체 |
| Theme | name, keywords, start_date | HBM |
| Report | id, title, publish_date, source, type | 삼성전자 실적분석 |
| Analyst | name, firm, specialty | 홍길동 |
| SecurityFirm | name, code | 미래에셋증권 |
| TargetPrice | value, date, change_type | 95,000원 |
| Opinion | rating, date, previous_rating | 매수 |
| FinancialMetric | name, value, period, unit | 영업이익률 15% |
| MacroIndicator | name, value, date, country | 기준금리 3.5% |

### 10.2 엣지 (Relationship) 정의

| 관계 유형 | 연결 | 속성 |
|-----------|------|------|
| BELONGS_TO | Company → Industry | - |
| RELATED_TO | Company → Theme | relation_type (수혜/관련/피해) |
| HAS_TARGET_PRICE | Company → TargetPrice | date, source_report |
| HAS_OPINION | Company → Opinion | date, source_report |
| SUPPLIES_TO | Company → Company | product, share |
| COMPETES_WITH | Company → Company | overlap_area |
| MENTIONED_IN | Company → Report | context, sentiment |
| AUTHORED_BY | Report → Analyst | - |
| PUBLISHED_BY | Report → SecurityFirm | - |
| INFLUENCES | MacroIndicator → Industry | direction (positive/negative) |

### 10.3 Neo4j 인덱스 설정

```cypher
// 주요 인덱스 생성
CREATE INDEX company_ticker IF NOT EXISTS FOR (c:Company) ON (c.ticker);
CREATE INDEX company_name IF NOT EXISTS FOR (c:Company) ON (c.name);
CREATE INDEX report_date IF NOT EXISTS FOR (r:Report) ON (r.publish_date);
CREATE INDEX theme_name IF NOT EXISTS FOR (t:Theme) ON (t.name);
CREATE INDEX industry_name IF NOT EXISTS FOR (i:Industry) ON (i.name);

// Full-text 인덱스
CREATE FULLTEXT INDEX company_search IF NOT EXISTS FOR (c:Company) ON EACH [c.name, c.aliases];
```

---

## 11. 추가 고려사항

### 11.1 데이터 품질 관리

1. **추출 신뢰도 임계값:** LLM 추출 결과에 신뢰도 점수를 부여하고, 0.7 미만은 수동 검토 대상으로 분류
2. **중복 리포트 감지:** 동일 리포트의 중복 업로드 방지를 위한 해시 기반 중복 체크
3. **엔티티 충돌 해결:** 동일 기업의 다른 목표주가가 있을 경우 날짜별 이력으로 관리
4. **정기적 데이터 정합성 검사:** 고아 노드, 불완전한 관계 탐지 및 알림

### 11.2 성능 최적화

1. **그래프 쿼리 최적화:** Neo4j 인덱스 생성 (Company.ticker, Report.publish_date 등)
2. **캐싱 전략:** 자주 조회되는 엔티티 정보 및 관계망 Redis 캐싱
3. **배치 처리:** 대량 리포트 업로드 시 청크 단위 비동기 처리
4. **벡터 검색 최적화:** HNSW 인덱스 파라미터 튜닝

### 11.3 보안 및 규정 준수

1. **저작권 관리:** 증권사 리포트 저작권 정책 확인 및 사용 범위 명시
2. **데이터 보존:** 리포트 원본 및 추출 데이터의 보존 기간 정책 수립
3. **접근 제어:** 역할 기반 접근 제어(RBAC) 구현
4. **감사 로그:** 사용자 활동 및 시스템 이벤트 로깅

### 11.4 확장성 고려

1. **수평 확장:** Celery 워커 스케일 아웃, Neo4j Cluster 구성 가능성
2. **데이터 파티셔닝:** 기간별/섹터별 그래프 분할 전략
3. **멀티 테넌시:** 향후 B2B SaaS 전환을 위한 테넌트 분리 설계

### 11.5 PDF 처리 관련 고려사항

1. **다양한 PDF 포맷:** 증권사별 상이한 레이아웃 대응 (템플릿 기반 추출 규칙)
2. **스캔 PDF 처리:** OCR 적용 필요 여부 자동 감지
3. **테이블 구조 보존:** 재무제표 등 복잡한 테이블의 구조 유지
4. **차트/이미지 처리:** 그래프, 차트 내 데이터 추출 전략

### 11.6 LLM 관련 고려사항

1. **모델 선택:** 추출 정확도 vs 비용 트레이드오프 (GPT-4o, Claude Sonnet 비교)
2. **프롬프트 버저닝:** 추출용 프롬프트 버전 관리 및 A/B 테스트
3. **할루시네이션 방지:** 출처 기반 검증, Grounding 강화
4. **비용 최적화:** 청크 크기 조절, 필요시 Fallback 모델 사용

---

## 12. 사용자 시나리오

### 12.1 시나리오 1: 개인 투자자의 종목 분석

- **상황:** 삼성전자 투자를 고려 중인 개인 투자자
- **행동:** 최근 삼성전자 리포트 5건 업로드 후 "삼성전자의 최근 투자의견 변화와 이유를 알려줘" 질문
- **결과:** 증권사별 목표주가 변동 타임라인과 주요 상향/하향 사유 요약 제공

### 12.2 시나리오 2: 섹터 분석

- **상황:** 반도체 섹터에 집중 투자하는 전업 투자자
- **행동:** "HBM 테마 수혜주 중 공급망 위치별로 분류해줘" 질문
- **결과:** HBM 밸류체인 그래프 (장비 → 소재 → 반도체 → 고객사) 시각화와 각 위치별 종목 목록

### 12.3 시나리오 3: 컨센서스 분석

- **상황:** 여러 증권사 의견을 비교하고 싶은 펀드 매니저
- **행동:** "SK하이닉스에 대한 증권사별 목표주가와 의견을 비교해줘" 질문
- **결과:** 증권사별 목표주가 분포, 컨센서스 평균, 이탈 의견 하이라이트

### 12.4 시나리오 4: 거시경제 영향 분석

- **상황:** 금리 인상이 포트폴리오에 미칠 영향을 파악하고 싶은 투자자
- **행동:** "금리 인상 시 영향받는 섹터와 종목을 분석해줘" 질문
- **결과:** 금리 민감도가 높은 섹터(금융, 부동산 등) 및 관련 종목 그래프, 각 리포트에서 언급된 영향 분석

---

## 13. 개발 로드맵

| Phase | 기간 | 주요 산출물 |
|-------|------|-------------|
| **Phase 1** | 2주 | Docker Compose 환경, PDF 파싱, 기본 온톨로지 정의 |
| **Phase 2** | 3주 | LLM 기반 엔티티 추출, Neo4j 연동, 기본 Cypher 쿼리 |
| **Phase 3** | 3주 | LangGraph 에이전트, 하이브리드 검색, 질의응답 API |
| **Phase 4** | 2주 | React 프론트엔드, 그래프 시각화, MVP 완성 |

### Phase 1 상세 (2주)

- Week 1: 프로젝트 구조 설정, Docker Compose 환경 구축
- Week 2: PDF 파싱 파이프라인, 온톨로지 스키마 정의

### Phase 2 상세 (3주)

- Week 3: LLMGraphTransformer 연동, 기본 추출 로직
- Week 4: Neo4j 연동, 그래프 저장 로직
- Week 5: 엔티티 정규화, 벡터 DB 연동

### Phase 3 상세 (3주)

- Week 6: LangGraph 에이전트 기본 구조
- Week 7: 하이브리드 검색 로직, Intent Router
- Week 8: 질의응답 API, 스트리밍 응답

### Phase 4 상세 (2주)

- Week 9: React 프론트엔드 기본 UI
- Week 10: 그래프 시각화, 통합 테스트, MVP 완성

---

## 14. 리스크 및 완화 방안

| 리스크 | 영향도 | 완화 방안 |
|--------|--------|-----------|
| PDF 파싱 품질 저하 | 높음 | 증권사별 템플릿 분석, Fallback OCR 적용 |
| LLM 추출 오류 | 높음 | 신뢰도 점수 기반 필터링, 수동 검증 프로세스 |
| 그래프 쿼리 성능 | 중간 | 인덱스 최적화, 쿼리 결과 캐싱 |
| API 비용 증가 | 중간 | 청크 최적화, 필요시 오픈소스 모델 적용 |
| 저작권 이슈 | 중간 | 이용약관 명시, 개인용 한정 사용 |
| 데이터 정합성 | 중간 | 정기 검증 배치, 알림 시스템 |

---

## 15. 성공 지표 (KPI)

| 지표 | 목표값 | 측정 방법 |
|------|--------|-----------|
| 엔티티 추출 정밀도 | 85% 이상 | 수동 샘플링 검증 (100건/주) |
| 관계 추출 정밀도 | 80% 이상 | 수동 샘플링 검증 |
| 질의 응답 정확도 | 75% 이상 | 사용자 피드백 (Thumbs up/down) |
| 응답 지연시간 | 15초 이내 | API 응답 시간 모니터링 |
| PDF 처리 시간 | 2분 이내 | Worker 처리 시간 로깅 |
| 시스템 가용성 | 99% 이상 | Uptime 모니터링 |

---

## 16. 용어 정의

| 용어 | 정의 |
|------|------|
| GraphRAG | 지식 그래프와 벡터 검색을 결합한 검색 증강 생성 방식 |
| 온톨로지 | 도메인 내 개념과 관계를 정의한 체계적 모델 |
| 엔티티 | 그래프 내 노드로 표현되는 개별 객체 (기업, 산업 등) |
| Cypher | Neo4j의 그래프 질의 언어 |
| Multi-hop Reasoning | 여러 관계를 거쳐 추론하는 방식 |
| LangGraph | LangChain 기반의 에이전트 워크플로우 프레임워크 |
| 투자의견 | 증권사가 제시하는 종목별 투자 판단 (매수/중립/매도 등) |
| 목표주가 | 증권사가 예상하는 향후 주가 수준 |

---

## 17. 참고 문서

- LangChain Documentation: https://python.langchain.com
- LangGraph Documentation: https://langchain-ai.github.io/langgraph
- Neo4j Graph Database: https://neo4j.com/docs
- Microsoft GraphRAG Paper: https://arxiv.org/abs/2404.16130
- FastAPI Documentation: https://fastapi.tiangolo.com
- Qdrant Documentation: https://qdrant.tech/documentation
- Docker Compose Documentation: https://docs.docker.com/compose

---

## Appendix A: .env.example

```bash
# LLM API Keys
OPENAI_API_KEY=sk-your-openai-api-key
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key

# Neo4j Configuration
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-secure-password

# Redis Configuration
REDIS_URL=redis://redis:6379/0

# Qdrant Configuration
QDRANT_HOST=qdrant
QDRANT_PORT=6333

# Application Settings
DEBUG=false
LOG_LEVEL=INFO
MAX_UPLOAD_SIZE=50MB

# Celery Configuration
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
```

---

## Appendix B: 샘플 Cypher 쿼리

```cypher
// 특정 테마(HBM) 관련 기업 및 최근 투자의견 조회
MATCH (t:Theme {name: 'HBM'})<-[:RELATED_TO]-(c:Company)
MATCH (c)-[:HAS_OPINION]->(o:Opinion)
WHERE o.date >= date() - duration('P3M')
RETURN c.name, c.ticker, o.rating, o.date
ORDER BY o.date DESC;

// 특정 기업의 공급망 관계 조회
MATCH path = (c:Company {ticker: '005930'})-[:SUPPLIES_TO*1..3]->(customer:Company)
RETURN path;

// 증권사별 목표주가 컨센서스
MATCH (c:Company {ticker: '000660'})-[:HAS_TARGET_PRICE]->(tp:TargetPrice)
MATCH (r:Report)-[:PUBLISHED_BY]->(sf:SecurityFirm)
WHERE tp.source_report = r.id
RETURN sf.name, tp.value, tp.date
ORDER BY tp.date DESC;

// 투자의견 상향된 기업 목록
MATCH (c:Company)-[:HAS_OPINION]->(o:Opinion)
WHERE o.previous_rating IN ['중립', '매도'] AND o.rating = '매수'
  AND o.date >= date() - duration('P1M')
RETURN c.name, c.ticker, o.previous_rating, o.rating, o.date;
```

---

*문서 끝*