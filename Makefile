.PHONY: frontend-build docs-build build downup rebuild updown

frontend-build:
	./scripts/frontend_build.sh

docs-build:
	$(MAKE) -C docs html

build:
	docker compose build --pull

rebuild: build downup

downup:
	docker compose down && docker compose up -d
