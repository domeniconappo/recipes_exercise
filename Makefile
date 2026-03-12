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

api_specs: run
	docker compose exec app python -c " \
		import json, yaml\
		from app.main import app\
		from fastapi.openapi.utils import get_openapi\
		schema = get_openapi(\
			title=app.title,\
			version=app.version,\
			description=app.description,\
			routes=app.routes,\
		)\
		with open('/application/openapi.yaml', 'w') as f:\
			yaml.dump(schema, f, allow_unicode=True, sort_keys=False)\
		print('openapi.yaml written')\
		"
