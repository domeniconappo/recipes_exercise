init_db:
	...

build:
	docker compose build app

run:
	docker compose up -d

stop:
	docker compose down

test:
	docker compose build test
	docker compose --profile test run --rm test

lint:
	uv run ruff check . --select I --fix
	uv run ruff format .

create_db_migration: run
	docker compose exec app /application/.venv/bin/alembic -c /application/alembic.ini revision --autogenerate
	make stop

migrate_db: run
	docker compose exec app /application/.venv/bin/alembic -c /application/alembic.ini upgrade head
	make stop
