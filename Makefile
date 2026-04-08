export COMPOSE_NAME=barramento_de_mensagens
export COMPOSE_TEST_NAME=$(COMPOSE_NAME)_test

# ── Lint & Quality ──────────────────────────────────────────────────
ruff:
	uv run ruff format . && uv run ruff check . --fix

lint: ruff

mypy:
	uv run mypy business_contexts/ infra/ messagebus/ libs/

ty:
	uv run ty check

typecheck: mypy

check: lint typecheck
	@echo "✔ Lint (ruff) e type-check (mypy) passaram."

# ── Aplicação ───────────────────────────────────────────────────────
run:
	uv run uvicorn business_contexts.main:app --host 0.0.0.0 --port 8000 --reload

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

# ── Migrações ───────────────────────────────────────────────────────
upgrade:
	uv run alembic upgrade head

downgrade:
	uv run alembic downgrade -1

migration:
	uv run alembic revision -m "$(m)"

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
	docker compose -f docker-compose.test.yml -p $(COMPOSE_TEST_NAME) down -v

# ── Testes ──────────────────────────────────────────────────────────
test-unit:
	uv run python -m pytest tests/unit/ -v

test-integration: test-env
	uv run python -m pytest tests/integration/ -v; \
	$(MAKE) test-env-down

test-all: test-env
	uv run python -m pytest tests/ -v; \
	$(MAKE) test-env-down

test-cov: test-env
	uv run python -m pytest tests/ -v --cov=business_contexts --cov=infra --cov=messagebus --cov-report=term-missing; \
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
	@echo "  Migrações"
	@echo "  ──────────────────────────────────────────────────"
	@echo "  make upgrade           → Aplica migrações Alembic até head"
	@echo "  make downgrade         → Reverte uma revisão Alembic"
	@echo "  make migration m=nome  → Cria nova revisão Alembic"
	@echo ""
	@echo "  Deploy (Docker)"
	@echo "  ──────────────────────────────────────────────────"
	@echo "  make run               → Roda API local com reload"
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
	@echo "  make mypy              → Verifica tipos com mypy"
	@echo "  make ty                → Verifica tipos com ty"
	@echo "  make typecheck         → Verifica tipos com mypy"
	@echo ""
	@echo "  Limpeza"
	@echo "  ──────────────────────────────────────────────────"
	@echo "  make docker-clean      → Remove containers/imagens não usados"
	@echo ""
