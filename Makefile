.PHONY: dev-up dev-down migrate db-upgrade seed setup-qdrant setup-neo4j lint-fix format quality test ci-local worker

dev-up:
	docker-compose up -d postgres redis

dev-down:
	docker-compose down

migrate:
	uv run alembic revision --autogenerate -m "$(MSG)"

db-upgrade:
	uv run alembic upgrade head

seed:
	uv run python scripts/seed_dev_data.py

setup-qdrant:
	uv run python scripts/setup_qdrant.py

setup-neo4j:
	uv run python scripts/setup_neo4j.py

lint-fix:
	uv run ruff check src/ tests/ --fix

format:
	uv run ruff format src/ tests/

quality:
	uv run ruff check src/ tests/
	uv run ruff format --check src/ tests/
	uv run pyright src/

test:
	docker-compose up -d postgres redis
	uv run pytest tests/ -n auto --cov=src --cov-report=term-missing -q

ci-local: quality test
	@echo "CI passed locally"

worker:
	uv run arq src.workers.main.WorkerSettings --watch src/
