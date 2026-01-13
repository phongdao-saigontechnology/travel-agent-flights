# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LangGraph-powered travel agent chatbot with Amadeus API integration. Python 3.12+ FastAPI application enabling conversational travel planning and booking for flights, hotels, and airport transfers.

## Commands

```bash
# Install dependencies
uv sync

# Run API server
uv run python -m travel_agent.main

# Tests
uv run pytest                              # all tests
uv run pytest tests/test_api/              # specific directory
uv run pytest tests/test_api/test_chat.py  # single file
uv run pytest -k "test_search"             # by name pattern
uv run pytest --cov=src/travel_agent       # with coverage

# Code quality
uv run ruff check src/ tests/              # lint
uv run ruff format src/ tests/             # format
uv run mypy src/                           # type check
```

## Architecture

### LangGraph Agent Flow
```
START → agent node → tools_condition → tools node → agent → END
                         ↓
                    (loop if tool calls needed)
```

The agent uses `MessagesState` from LangGraph with a `MemorySaver` checkpointer for conversation persistence. System prompt is prepended on first message.

### Key Components

- **`src/travel_agent/agent/graph.py`**: Agent graph definition, `create_travel_agent()` factory
- **`src/travel_agent/agent/state.py`**: State schema with `TravelAgentState` TypedDict
- **`src/travel_agent/api/routes/chat.py`**: Chat endpoints (sync POST `/chat`, streaming POST `/chat/stream`)
- **`src/travel_agent/clients/amadeus_client.py`**: Amadeus API wrapper with retry logic (tenacity)
- **`src/travel_agent/tools/`**: 15 LangChain tools organized by domain (flight, hotel, car, utility)

### Configuration Pattern

Always use `get_settings()` singleton from `travel_agent.config` - never instantiate Settings directly. Configuration loaded from environment variables (see `.env.example`).

Required env vars: `OPENAI_API_KEY`, `AMADEUS_CLIENT_ID`, `AMADEUS_CLIENT_SECRET`, `AMADEUS_HOSTNAME`

## Tech Stack

- **LangGraph/LangChain**: Agent orchestration
- **FastAPI + uvicorn**: REST API with SSE streaming
- **Amadeus SDK**: Travel data API
- **Pydantic**: Settings and data validation
- **structlog**: Structured JSON logging
- **tenacity**: Retry logic for API calls
