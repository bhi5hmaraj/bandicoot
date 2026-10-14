# Bandicoot API service

A FastAPI service and web UI around the `bandicoot` library. It is a prototype. `/train_clusters` fits the model on synthetic data, and `/recommend` uses mock participants when the request has none. [Architecture](../docs/architecture.md) has the full design and the known limits.

## Run locally

Run these commands from the repository root. The app loads `app/templates` and `app/static` by relative path.

```bash
pip install -r requirements.txt jinja2
uvicorn app.main:app --reload --port 8000
```

The app does not start without `jinja2`, and `requirements.txt` does not list it. `python -m app.main` also starts the server, on host 0.0.0.0 and port 8000, with reload.

Then open `http://localhost:8000/` for the web UI and `http://localhost:8000/docs` for the OpenAPI UI.

The web pages return HTTP 500 with Starlette 1.x (tested with FastAPI 0.143.0). For the web UI, install `fastapi==0.115.6` (Starlette 0.41.3). The API works with both versions.

## Try the API

```bash
# Fit a model on synthetic data (100 participants, 30 periods; see app/api/routes.py).
curl -X POST http://localhost:8000/api/v1/train_clusters \
  -H "Content-Type: application/json" -d '{"n_clusters": 5}'

# Rank 3 participants with a budget of 2 contacts.
curl -X POST http://localhost:8000/api/v1/recommend \
  -H "Content-Type: application/json" \
  -d '{"budget": 2, "caregiver_ids": ["a", "b", "c"], "current_states": [0, 1, 1]}'
```

The synthetic model does not know these IDs. So all 3 get the median index and `cluster_id` -1.

## Configuration

Copy `.env.example` to `.env` in the repository root. Restart the server after a change. The main settings:

| Variable | Default | Effect |
|---|---|---|
| `REQUIRE_AUTH` | `false` | Turns on the `X-API-Key` check |
| `API_KEY` | unset | Expected `X-API-Key` value |
| `GAMMA` | `0.99` | Discount factor |
| `LOG_LEVEL` | `INFO` | `DEBUG` adds the exception text to unhandled-error responses |

The full table is in [architecture: configuration](../docs/architecture.md#configuration).

## Endpoints

All paths start with `/api/v1`. With `REQUIRE_AUTH=true`, all endpoints except `/health` need the `X-API-Key` header.

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Status and `model_loaded` |
| POST | `/train_clusters` | Fit a new in-memory model on synthetic data |
| POST | `/recommend` | Top-K participants by Whittle index |
| POST | `/precompute_indices` | Report index counts (computes nothing) |
| POST | `/update_state` | Check and log state updates (stores nothing) |

Request fields, errors, and limits: [architecture: service](../docs/architecture.md#service).

## Tests

```bash
pip install -r requirements.txt jinja2
pytest tests/
```

Two tests in `tests/test_api_integration.py` fail. `test_root_endpoint` expects JSON at `/`, but that route serves the HTML dashboard. `test_complete_workflow` expects an unfitted model, but earlier tests fit the shared in-memory model.

## Docker

```bash
docker build -t bandicoot-api .
docker run -p 8080:8080 bandicoot-api
```

The container listens on `$PORT` (default 8080). The image installs only `requirements.txt`, which does not list `jinja2`. So the app import fails and the container stops. The `HEALTHCHECK` command needs `requests`, which is also not installed.

## Layout

| Path | Content |
|---|---|
| `main.py` | App, middleware, and router mounts |
| `config.py` | Settings from the environment |
| `dependencies.py` | In-memory model and API key check |
| `models.py` | Pydantic request and response models |
| `api/routes.py` | API endpoints |
| `web/routes.py`, `templates/`, `static/` | Web UI |
