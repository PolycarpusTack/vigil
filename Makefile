.PHONY: help install test test-unit test-integration lint collector agent docker-up docker-down clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# --- Installation ---

install: ## Install all dependencies for local development
	pip install -e ".[dev,database,web]"
	pip install -r collector/requirements.txt
	pip install -r agent/requirements.txt

install-sdk-python: ## Install Python SDK
	pip install -e sdks/python/

install-sdk-ts: ## Install TypeScript SDK dependencies
	cd sdks/typescript && npm install

# --- Testing ---

test: test-unit ## Run all tests

test-unit: ## Run unit tests
	pytest tests/unit/ -v

test-integration: ## Run integration tests (requires collector running)
	pytest tests/integration/ -v

test-sql: ## Run SQL storage tests
	pytest tests/unit/test_sql_storage.py -v

# --- Linting ---

lint: ## Run linters
	black --check vigil/ collector/ agent/ tests/
	isort --check vigil/ collector/ agent/ tests/
	flake8 vigil/ collector/ agent/

format: ## Auto-format code
	black vigil/ collector/ agent/ tests/
	isort vigil/ collector/ agent/ tests/

# --- Services ---

collector: ## Run collector service locally
	uvicorn collector.main:app --host 0.0.0.0 --port 8080 --reload

agent: ## Run monitoring agent locally
	python3 -m agent.main

# --- Docker ---

docker-up: ## Start all services with Docker Compose
	docker compose up --build -d

docker-down: ## Stop all Docker Compose services
	docker compose down

docker-logs: ## Tail logs from all services
	docker compose logs -f

# --- Cleanup ---

clean: ## Remove build artifacts and caches
	rm -rf __pycache__ */__pycache__ */*/__pycache__
	rm -rf .pytest_cache htmlcov .coverage
	rm -rf dist build *.egg-info
	rm -f audit_collector.db audit.db
