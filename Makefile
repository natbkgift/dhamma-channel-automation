# Makefile for Dhamma Channel Automation project
.PHONY: help install lint format test test-cov docs serve-docs agent preflight quick mypy clean

# Default target
help:
	@echo "🙏 Dhamma Channel Automation - Available Commands"
	@echo "=================================================="
	@echo ""
	@echo "📦 Setup & Dependencies:"
	@echo "  install     - Install project in development mode"
	@echo ""
	@echo "🔍 Code Quality:"
	@echo "  lint        - Run ruff linter"
	@echo "  format      - Format code with ruff"
	@echo "  mypy        - Run type checking (non-strict)"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  test        - Run pytest (quick)"
	@echo "  test-cov    - Run pytest with coverage"
	@echo ""
	@echo "📚 Documentation:"
	@echo "  docs        - Build documentation"
	@echo "  serve-docs  - Serve documentation locally"
	@echo ""
	@echo "🤖 Agent:"
	@echo "  agent       - Run TrendScout agent with mock data"
	@echo ""
	@echo "🚀 Preflight:"
	@echo "  preflight   - Full preflight check (before PR)"
	@echo "  quick       - Quick preflight check (pre-commit)"
	@echo ""
	@echo "🧹 Cleanup:"
	@echo "  clean       - Remove cache and build artifacts"

install:
	pip install -e ".[dev]"

lint:
	ruff check .

format:
	ruff format .

test:
	pytest -q

test-cov:
	pytest --cov=src --cov-report=term-missing -q

docs:
	mkdocs build --strict

serve-docs:
	mkdocs serve

agent:
	python -m cli.main trend-scout \
		--input src/agents/trend_scout/mock_input.json \
		--out output/result.json

preflight:
	bash scripts/preflight.sh

quick:
	bash scripts/preflight_quick.sh

mypy:
	mypy src || true

clean:
	@echo "🧹 Cleaning up..."
	rm -rf .pytest_cache
	rm -rf .mypy_cache  
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf site
	rm -rf build
	rm -rf dist
	rm -rf *.egg-info
	@echo "✅ Cleanup completed"