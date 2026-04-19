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
	trap 'COMPOSE_PROJECT_NAME=corvix-screenshot docker compose -f docker-compose.lighthouse.yml down --volumes --remove-orphans' EXIT; \
	COMPOSE_PROJECT_NAME=corvix-screenshot docker compose -f docker-compose.lighthouse.yml up --build -d --wait web-lighthouse; \
	if [ "$${UI_SCREENSHOT_INSTALL_DEPS:-0}" = "1" ]; then \
		uv sync --extra e2e; \
		uv run playwright install chromium; \
	fi; \
	uv run pytest -m e2e tests/e2e/test_ui_screenshot.py -q
