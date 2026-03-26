**Multi-Agents Chatbot**

Small multi-agent chatbot project combining FastAPI backend, lightweight vector stores, and a minimal frontend for demonstrations.

**Repository Structure**
- **`app/`**: FastAPI application and API routes.
- **`multi_agents/`**: Orchestration, agent definitions, prompts and tools used by the multi-agent runner.
- **`database/`**, **`faiss_cache/`**, **`multi_vector_db/`**: Local vector DB files and caches used by agents.
- **`frontend/`**: Simple static frontend (HTML/JS/CSS) served by the FastAPI app.
- **`tests/`**: Unit tests for agents and integration checks.

**Features**
- Multi-agent orchestration with separate agent roles (booking, FAQ, IT support, ticketing).
- Simple REST API for conversation and authentication.
- Static frontend served at the root path by FastAPI.
- Local vector stores and FAISS cache to support retrieval.

**Prerequisites**
- Python 3.10+ installed.
- Git (if you cloned the repo).
- Redis server available locally or via Docker (required by the app).

**Install Python dependencies**
1. Create and activate a virtual environment:

```
python3 -m venv venv
source venv/bin/activate
```

2. Install requirements:

```
pip install -r requirements.txt
```

**Redis: install & run**
The application uses Redis (see `app/core/config.py`) and expects `REDIS_URL` (default `redis://localhost:6379/0`). Choose one of the options below:

- Debian/Ubuntu (system package):

```
sudo apt update
sudo apt install redis-server
sudo systemctl enable --now redis
sudo systemctl status redis
```

- macOS (Homebrew):

```
brew install redis
brew services start redis
```

- Docker (recommended if you don't want to install locally):

```
docker run -p 6379:6379 --name redis -d redis:7
```

Verify Redis is reachable at `localhost:6379` or change `REDIS_URL` accordingly.

**Environment configuration**
- Copy and edit the repository environment file located at `multi_agents/.env` (the app loads this file by default): set your keys and secrets such as `OPENAI_API_KEY`, `TAVILY_API_KEY`, `LANGCHAIN_API_KEY`, `SECRET_KEY`, and `REDIS_URL`.

**Database / Vector stores**
- The project uses local SQLite/Chroma/FAISS artifacts under `multi_vector_db/` and `faiss_cache/` directories. These are generally created/managed by the app or provided in the repo.

**Run the application (development)**
From the repository root (the folder that contains `app/`), run:

```
uvicorn app.main:app --reload
```

Open the app in your browser at http://127.0.0.1:8000 — the FastAPI app serves the static frontend at the root path.

**Running tests**
Run unit tests with pytest:

```
pytest -q
```

**Notes & Troubleshooting**
- If the app cannot connect to Redis, ensure the service is running and `REDIS_URL` is correct.
- If you use Docker for Redis, map the port `6379` as shown above.
- If you see missing model files (e.g., `model.keras`), ensure required model artifacts are present in the repo or update configuration to use remote models.

**Contributing**
- Feel free to open issues or PRs. Keep changes small and focused.

**License**
- Check repository root for license or contact the maintainer.
