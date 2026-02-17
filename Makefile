# E-Commerce Multi-Agent System Makefile

PYTHON = python
PIP = pip
PYTEST = pytest
RUFF = ruff
DOCKER_COMPOSE = docker-compose

.PHONY: help install test lint docker-up docker-down docker-logs clean

help:
	@echo "Available commands:"
	@echo "  make install      - Install project dependencies"
	@echo "  make test         - Run integration tests (requires docker-up)"
	@echo "  make lint         - Run linting checks"
	@echo "  make docker-up    - Start all services with Docker Compose"
	@echo "  make docker-down  - Stop all services"
	@echo "  make docker-logs  - View real-time logs"
	@echo "  make clean        - Remove python cache files"

install:
	$(PIP) install -e ".[dev]"

test:
	$(PYTEST) tests/test_integration.py -v

lint:
	$(RUFF) check .
	$(RUFF) format --check .

docker-up:
	$(DOCKER_COMPOSE) up -d

docker-down:
	$(DOCKER_COMPOSE) down

docker-logs:
	$(DOCKER_COMPOSE) logs -f

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
