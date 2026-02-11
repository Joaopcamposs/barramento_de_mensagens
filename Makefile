export COMPOSE_NAME=barramento_de_mensagens

ruff:
	ruff format . && ruff check . --fix

compose:
	docker-compose -f docker-compose.yml --env-file .env -p $(COMPOSE_NAME) up --build -d

postgres:
	docker-compose -f docker-compose.yml --env-file .env -p $(COMPOSE_NAME) up --build -d postgres

test-db-up:
	docker-compose -f docker-compose.test.yml -p $(COMPOSE_NAME)_test up -d --wait

test-db-down:
	docker-compose -f docker-compose.test.yml -p $(COMPOSE_NAME)_test down -v

test-unit:
	python -m pytest tests/unit/ -v

test-integration: test-db-up
	python -m pytest tests/integration/ -v; \
	$(MAKE) test-db-down

test-all: test-db-up
	python -m pytest tests/ -v; \
	$(MAKE) test-db-down

docker-clean:
	docker system prune -f