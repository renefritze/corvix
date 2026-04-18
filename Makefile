.PHONY: frontend-build docs-build build downup rebuild updown lighthouse

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
