.PHONY: frontend-build gen-types docs-build build downup rebuild updown lighthouse ui-screenshot reset-state first-run

frontend-build:
	./scripts/frontend_build.sh

gen-types:
	uv run python scripts/export_openapi.py
	npm --prefix frontend run gen:types

docs-build:
	$(MAKE) -C docs html

build:
	docker compose build --pull

rebuild: build downup

downup:
	docker compose down && docker compose up -d

lighthouse:
	docker compose -f docker-compose.yml -f docker-compose.lighthouse.yml up --build --abort-on-container-exit --exit-code-from lighthouse lighthouse

ui-screenshot:
	@set -eu; \
		docker run --rm \
		--user "$$(id -u):$$(id -g)" \
		-v "$$(pwd):/workspace" \
		-w /workspace \
		mcr.microsoft.com/playwright/python:v1.58.0-noble \
		bash -lc 'python -m pip install --quiet uv && export PATH="$$(python -m site --user-base)/bin:$$PATH" && uv sync --extra e2e && uv run pytest -m e2e tests/e2e/test_ui_screenshot.py -q'

reset-state:
	bash scripts/reset-state.sh

first-run:
	uv run scripts/first_run.py
