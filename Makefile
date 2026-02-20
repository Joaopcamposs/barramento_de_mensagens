export COMPOSE_NAME=barramento_de_mensagens
export COMPOSE_TEST_NAME=$(COMPOSE_NAME)_test

# ── Lint & Quality ──────────────────────────────────────────────────
ruff:
	ruff format . && ruff check . --fix

lint: ruff

mypy:
	mypy business_contexts/ infra/ messagebus/ libs/

typecheck: mypy

check: lint typecheck
	@echo "✔ Lint (ruff) e type-check (mypy) passaram."

# ── Banco de dados (postgres) ────────────────────────────────────────────────────
postgres-up:
	docker compose -f docker-compose.yml --env-file .env -p $(COMPOSE_NAME) up --build -d postgres
	@echo "✔ Postgres rodando em localhost:54322"

postgres-down:
	docker compose -f docker-compose.yml -p $(COMPOSE_NAME) down postgres

postgres-destroy:
	docker compose -f docker-compose.yml -p $(COMPOSE_NAME) down postgres -v

postgres-logs:
	docker compose -f docker-compose.yml -p $(COMPOSE_NAME) logs postgres -f

# ── Deploy: App (porta 8000) ──────────────────────────────────
compose:
	docker compose -f docker-compose.yml --env-file .env -p $(COMPOSE_NAME) up --build -d

compose-down:
	docker compose -f docker-compose.yml --env-file .env -p $(COMPOSE_NAME) down

compose-logs:
	docker compose -f docker-compose.yml --env-file .env -p $(COMPOSE_NAME) logs -f

# ── Docker (testes) ─────────────────────────────────────────────────
test-env:
	docker compose -f docker-compose.test.yml -p $(COMPOSE_TEST_NAME) up -d --wait

test-env-down:
	docker compose -f $(INFRA)/docker-compose.test.yml -p $(COMPOSE_TEST_NAME) down -v

# ── Testes ──────────────────────────────────────────────────────────
test-unit:
	python -m pytest tests/unit/ -v

test-integration: test-env
	python -m pytest tests/integration/ -v; \
	$(MAKE) test-env-down

test-all: test-env
	python -m pytest tests/ -v; \
	$(MAKE) test-env-down

test-cov: test-env
	python -m pytest tests/ -v --cov=business_contexts --cov=infra --cov=messagebus --cov-report=term-missing; \
	$(MAKE) test-env-down

# ── Limpeza ─────────────────────────────────────────────────────────
docker-clean:
	docker system prune -f

# ── Help ────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  Infraestrutura - Banco de Dados"
	@echo "  ──────────────────────────────────────────────────"
	@echo "  make postgres-up       → Sobe Postgres compartilhado (:54322)"
	@echo "  make postgres-down     → Para Postgres (preserva dados)"
	@echo "  make postgres-logs     → Logs Postgres"
	@echo "  make postgres-destroy  → Para Postgres e remove volumes"
	@echo ""
	@echo "  Deploy (Docker)"
	@echo "  ──────────────────────────────────────────────────"
	@echo "  make compose           → Sobe API + Postgres (:8000)"
	@echo "  make compose-down      → Para todos os containers"
	@echo "  make compose-logs      → Logs dos containers"
	@echo ""
	@echo "  Testes"
	@echo "  ──────────────────────────────────────────────────"
	@echo "  make test-env          → Iniciar banco de testes (:54323)"
	@echo "  make test-env-down     → Encerrar banco de testes"
	@echo "  make test-unit         → Testes unitários"
	@echo "  make test-integration  → Testes de integração"
	@echo "  make test-all          → Todos os testes"
	@echo "  make test-cov          → Testes com cobertura"
	@echo ""
	@echo "  Qualidade"
	@echo "  ──────────────────────────────────────────────────"
	@echo "  make lint              → Formata e corrige lint com ruff"
	@echo "  make typecheck         → Verifica tipos com mypy"
	@echo ""
	@echo "  Limpeza"
	@echo "  ──────────────────────────────────────────────────"
	@echo "  make docker-clean      → Remove containers/imagens não usados"
	@echo ""