.PHONY: help build up down restart logs clean test lint format

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Build all Docker containers
	docker-compose build

up: ## Start all services
	docker-compose up -d

up-dev: ## Start all services in development mode
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

down: ## Stop all services
	docker-compose down

restart: ## Restart all services
	docker-compose restart

logs: ## Show logs from all services
	docker-compose logs -f

logs-backend: ## Show backend logs
	docker-compose logs -f backend

logs-frontend: ## Show frontend logs
	docker-compose logs -f frontend

clean: ## Remove all containers, volumes, and networks
	docker-compose down -v --remove-orphans

db-migrate: ## Run database migrations
	docker-compose exec backend alembic upgrade head

db-downgrade: ## Rollback last migration
	docker-compose exec backend alembic downgrade -1

db-revision: ## Create new migration (usage: make db-revision message="description")
	docker-compose exec backend alembic revision --autogenerate -m "$(message)"

test: ## Run tests
	docker-compose exec backend pytest

lint: ## Run linters
	docker-compose exec backend ruff check app/
	docker-compose exec backend mypy app/

format: ## Format code
	docker-compose exec backend black app/
	docker-compose exec backend ruff check --fix app/

shell-backend: ## Open shell in backend container
	docker-compose exec backend /bin/bash

shell-db: ## Open PostgreSQL shell
	docker-compose exec postgres psql -U stockrags -d stockrags

neo4j-shell: ## Open Neo4j Cypher shell
	docker-compose exec neo4j cypher-shell -u neo4j -p secret

health: ## Check health of all services
	@curl -s http://localhost:8000/api/v1/health/ready | python -m json.tool

status: ## Show status of all services
	docker-compose ps

init: build up ## Initialize project (build and start services)
	@echo "Waiting for services to be ready..."
	@sleep 10
	@make health
