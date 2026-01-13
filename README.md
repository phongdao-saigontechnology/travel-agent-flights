# Travel Agent Flights

LangGraph-powered travel agent chatbot with Amadeus API integration. A conversational AI assistant that helps users search and book flights, hotels, and airport transfers.

## Features

- **Flight Search & Booking**: Search flights by origin, destination, dates, and passengers
- **Hotel Search**: Find accommodations with check-in/out dates and guest count
- **Airport Transfers**: Search and book transfers between airports and hotels
- **Conversational Interface**: Natural language interaction powered by LangGraph
- **Streaming Responses**: Real-time response streaming via Server-Sent Events
- **Conversation Memory**: Persistent conversation state across messages

## Tech Stack

- **Python 3.12+**
- **LangGraph/LangChain** - Agent orchestration
- **FastAPI** - REST API framework
- **Amadeus SDK** - Travel data and booking API
- **OpenAI** - LLM provider

## Installation

```bash
# Clone the repository
git clone https://github.com/your-username/travel-agent-flights.git
cd travel-agent-flights

# Install dependencies using uv
uv sync

# Install with dev dependencies
uv sync --all-extras
```

## Configuration

Copy the example environment file and configure your API keys:

```bash
cp .env.example .env
```

Required environment variables:

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key |
| `AMADEUS_CLIENT_ID` | Amadeus API client ID |
| `AMADEUS_CLIENT_SECRET` | Amadeus API client secret |
| `AMADEUS_HOSTNAME` | `test` for sandbox, `production` for live |

Optional:

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8000` | Server port |
| `MODEL_NAME` | `gpt-4o` | OpenAI model |
| `TEMPERATURE` | `0.1` | LLM temperature |
| `MAX_ITERATIONS` | `25` | Max agent loop iterations |

## Usage

Start the API server:

```bash
uv run python -m travel_agent.main
```

The API will be available at `http://localhost:8000`:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Chat

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/chat` | Send message and get response |
| `POST` | `/chat/stream` | Stream response via SSE |
| `POST` | `/chat/{thread_id}/confirm` | Confirm/reject pending booking |
| `GET` | `/chat/{thread_id}/state` | Get conversation state |
| `DELETE` | `/chat/{thread_id}` | Delete conversation thread |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | API information |
| `GET` | `/health` | Health check with service status |

### Example Request

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Find flights from New York to London on March 15"}'
```

### Example Response

```json
{
  "thread_id": "abc123",
  "response": "I found several flights from New York to London on March 15th...",
  "tool_calls": [
    {
      "name": "search_flights",
      "arguments": {
        "origin": "NYC",
        "destination": "LON",
        "departure_date": "2024-03-15"
      }
    }
  ],
  "pending_confirmation": null
}
```

## Development

```bash
# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=src/travel_agent

# Lint
uv run ruff check src/ tests/

# Format
uv run ruff format src/ tests/

# Type check
uv run mypy src/
```

## License

MIT
