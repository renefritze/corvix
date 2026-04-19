.PHONY: frontend-build docs-build build downup rebuild updown lighthouse ui-screenshot

frontend-build:
	./scripts/frontend_build.sh

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
