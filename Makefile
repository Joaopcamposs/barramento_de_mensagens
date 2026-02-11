export COMPOSE_NAME=barramento_de_mensagens
export COMPOSE_TEST_NAME=$(COMPOSE_NAME)_test

# ── Lint & Quality ──────────────────────────────────────────────────
ruff:
	ruff format . && ruff check . --fix

lint:
	ruff format --check . && ruff check .

typecheck:
	mypy business_contexts/ infra/ messagebus/ libs/

check: lint typecheck
	@echo "✔ Lint e type-check passaram."

# ── Docker (app) ────────────────────────────────────────────────────
compose:
	docker compose -f docker-compose.yml --env-file .env -p $(COMPOSE_NAME) up --build -d

postgres:
	docker compose -f docker-compose.yml --env-file .env -p $(COMPOSE_NAME) up --build -d postgres

# ── Docker (testes) ─────────────────────────────────────────────────
test-env:
	docker compose -f docker-compose.test.yml -p $(COMPOSE_TEST_NAME) rm -f && \
	docker compose -f docker-compose.test.yml -p $(COMPOSE_TEST_NAME) up

test-db-up:
	docker compose -f docker-compose.test.yml -p $(COMPOSE_TEST_NAME) up -d --wait

test-db-down:
	docker compose -f docker-compose.test.yml -p $(COMPOSE_TEST_NAME) down -v

# ── Testes ──────────────────────────────────────────────────────────
test-unit:
	python -m pytest tests/unit/ -v

test-integration: test-db-up
	python -m pytest tests/integration/ -v; \
	$(MAKE) test-db-down

test-all: test-db-up
	python -m pytest tests/ -v; \
	$(MAKE) test-db-down

test-cov: test-db-up
	python -m pytest tests/ -v --cov=business_contexts --cov=infra --cov=messagebus --cov-report=term-missing; \
	$(MAKE) test-db-down

# ── Limpeza ─────────────────────────────────────────────────────────
docker-clean:
	docker system prune -f