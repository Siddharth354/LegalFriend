.PHONY: api web docker-up docker-down docker-logs ingest test lint

api:
	cd backend && uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

web:
	@if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null || lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null; then \
		echo "Web/API is already running. Attaching to live logs..."; \
		touch .web.log; \
		tail -f .web.log; \
	else \
		echo "Starting API and Web servers in background..." > .web.log; \
		($(MAKE) api >> .web.log 2>&1 &) ; \
		(cd frontend && bun run dev >> ../.web.log 2>&1 &) ; \
		echo "Servers started. Tailing logs (Press Ctrl+C to stop tailing, servers will keep running). Run 'make stop' to kill them." ; \
		tail -f .web.log; \
	fi

stop:
	@echo "Stopping web and api..."
	@-lsof -Pi :8000 -sTCP:LISTEN -t | xargs kill -9 2>/dev/null || true
	@-lsof -Pi :3000 -sTCP:LISTEN -t | xargs kill -9 2>/dev/null || true
	@echo "Stopped."

docker-up:
	docker compose up --build

docker-down:
	docker compose down

docker-logs:
	docker compose logs --follow

ingest:
	cd backend && uv run python -m src.ingestion.chunk_bns
	cd backend && uv run python -m src.ingestion.chunk_rbi_directions
	cd backend && uv run python -m src.ingestion.chunk_rbi_recovery_agents
	cd backend && uv run python -m src.ingestion.chunk_usurious_loans_act
	cd backend && uv run python -m src.ingestion.chunk_ni_act

test:
	cd backend && uv run ruff check .
	cd backend && uv run ty check .

lint:
	cd backend && uv run ruff check --fix .
	cd backend && uv run ruff format .
