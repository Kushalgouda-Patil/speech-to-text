.PHONY: install install-dev run dev test lint format docker-build docker-up docker-down clean

# ── Setup ─────────────────────────────────────────────────────────────────────

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt -r requirements-dev.txt

# ── Run ───────────────────────────────────────────────────────────────────────

run:
	uvicorn app.main:app --host 0.0.0.0 --port 8000

dev:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# ── Test ──────────────────────────────────────────────────────────────────────

test:
	pytest tests/ -v

# ── Code quality ──────────────────────────────────────────────────────────────

lint:
	ruff check app/ tests/

format:
	ruff format app/ tests/

# ── Docker ────────────────────────────────────────────────────────────────────

docker-build:
	docker build -t voice-stt:latest .

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

# ── Misc ──────────────────────────────────────────────────────────────────────

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	find . -name "*.pyc" -delete 2>/dev/null; true
