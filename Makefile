.PHONY: help config install test lint eval-plan docker-init docker-start docker-stop docker-logs

help:
	@echo 'REAL-MED: config, install, test, lint, eval-plan, docker-start, docker-stop'

config:
	@test -f .env || cp .env.example .env
	@test -f config.yaml || cp config.example.yaml config.yaml

install:
	uv sync --project backend --group dev

test:
	cd backend && PYTHONPATH=packages/harness:. uv run pytest tests/ -q

lint:
	uv run --project backend ruff check backend

eval-plan:
	uv run --project backend python scripts/run_batch_eval.py evals/experiments/exp_realmed_405case_11model.yaml --dry-run

docker-init:
	docker pull ghcr.io/agent-infra/sandbox:latest

docker-start:
	./scripts/docker.sh start

docker-stop:
	./scripts/docker.sh stop

docker-logs:
	./scripts/docker.sh logs
