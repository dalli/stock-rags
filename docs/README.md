# Stock RAGs - GraphRAG 증권 리포트 분석 서비스

GraphRAG 기반 증권 리포트 심층 분석 서비스입니다.

## 프로젝트 개요

- **Vector DB**: Qdrant
- **Graph DB**: Neo4j
- **Relational DB**: PostgreSQL
- **Backend**: FastAPI + Python 3.11+
- **Frontend**: React + TypeScript
- **LLM Orchestration**: LangChain + LangGraph
- **프롬프트 관리**: YAML 기반 중앙 집중식 관리
- **LLM Provider**: 클라우드(Gemini, OpenAI, Anthropic) + 로컬(Ollama, LM Studio, vLLM) 지원

## 시작하기

### 사전 요구사항

- Docker & Docker Compose
- (선택) OpenAI/Anthropic/Google API Keys
- (선택) Ollama (로컬 LLM 사용 시)

### 환경 설정

1. `.env` 파일 생성:
```bash
cp .env.example .env
```

2. `.env` 파일 편집하여 API 키 설정:
```bash
# 최소한 하나의 LLM provider API 키 필요
OPENAI_API_KEY=sk-...
# 또는
ANTHROPIC_API_KEY=sk-ant-...
# 또는
GOOGLE_API_KEY=...
```

### 실행

#### 개발 환경

```bash
# 프로젝트 초기화 (빌드 + 실행 + health check)
make init

# 또는 개별 명령어
make build    # Docker 이미지 빌드
make up       # 서비스 시작 (백그라운드)
make up-dev   # 개발 모드로 시작 (로그 출력)
```

#### 서비스 확인

```bash
# Health check
make health

# 또는 직접 curl
curl http://localhost:8000/api/v1/health/ready

# 로그 확인
make logs
make logs-backend
make logs-frontend
```

#### 서비스 중지

```bash
make down     # 서비스 중지
make clean    # 서비스 중지 + 볼륨 삭제
```

## 주요 명령어

```bash
make help              # 사용 가능한 명령어 확인
make build             # Docker 이미지 빌드
make up                # 서비스 시작
make down              # 서비스 중지
make restart           # 서비스 재시작
make logs              # 로그 확인
make health            # Health check
make db-migrate        # DB 마이그레이션 실행
make test              # 테스트 실행
make lint              # 린터 실행
make format            # 코드 포맷팅
```

## API 엔드포인트

### Health Check
- `GET /health` - 기본 health check
- `GET /api/v1/health/ready` - 전체 시스템 health check (DB + LLM 포함)

### Models
- `GET /api/v1/models` - 사용 가능한 LLM/Embedding 모델 목록
- `PUT /api/v1/models/default` - 기본 모델 설정

## 서비스 포트

- **Backend API**: http://localhost:8000
- **Frontend**: http://localhost:3000
- **PostgreSQL**: localhost:5432
- **Neo4j Browser**: http://localhost:7474
- **Neo4j Bolt**: bolt://localhost:7687
- **Qdrant**: http://localhost:6333
- **Redis**: localhost:6379

## Phase 1 완료 항목

✅ Docker 환경 설정 (docker-compose.yml)
✅ PostgreSQL 스키마 및 모델 정의
✅ Neo4j 연결 및 인덱스 설정
✅ Qdrant 컬렉션 스키마
✅ Redis 연결
✅ LLM Provider 추상화 (Base classes, Router)
✅ LLM Provider 구현 (OpenAI, Anthropic, Gemini, Ollama, LM Studio, vLLM)
✅ Embedding Provider 구현 (OpenAI, Ollama)
✅ 프롬프트 관리 시스템 (YAML 기반)
✅ FastAPI 기본 애플리케이션
✅ Health check 엔드포인트
✅ Models API 엔드포인트
✅ Alembic 마이그레이션 설정

## 다음 단계 (Phase 2)

Phase 2에서는 다음 기능을 구현할 예정입니다:

- PDF 파싱 및 메타데이터 추출
- Celery 작업 큐 설정
- 엔티티/관계 추출 서비스
- 그래프 빌딩 서비스
- 벡터 임베딩 저장
- 전체 Ingestion 파이프라인

## 개발 가이드

### 데이터베이스 마이그레이션

```bash
# 마이그레이션 생성
make db-revision message="description"

# 마이그레이션 적용
make db-migrate

# 마이그레이션 롤백
make db-downgrade
```

### 테스트

```bash
# 전체 테스트 실행
make test

# 특정 테스트 실행
docker-compose exec backend pytest tests/test_specific.py
```

### 코드 품질

```bash
# 린터 실행
make lint

# 코드 포맷팅
make format
```

## 트러블슈팅

### 서비스가 시작되지 않는 경우

1. 포트 충돌 확인:
```bash
# 포트 사용 확인
lsof -i :8000  # Backend
lsof -i :3000  # Frontend
lsof -i :5432  # PostgreSQL
```

2. 로그 확인:
```bash
make logs
```

3. 컨테이너 재시작:
```bash
make restart
```

### Health check 실패

1. 모든 서비스가 실행 중인지 확인:
```bash
make status
```

2. API 키가 올바르게 설정되었는지 확인:
```bash
cat .env | grep API_KEY
```

3. 데이터베이스 연결 확인:
```bash
make shell-db  # PostgreSQL
make neo4j-shell  # Neo4j
```

## 라이센스

MIT
