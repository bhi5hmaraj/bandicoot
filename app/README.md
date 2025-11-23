# Bandicoot RMAB API

FastAPI service for generating caregiver intervention recommendations using Restless Multi-Armed Bandits (RMAB).

## Quick Start

### Local Development

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Run the server:**
```bash
python -m app.main
```

Or with uvicorn directly:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

3. **View API docs:**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Docker Deployment

1. **Build the image:**
```bash
docker build -t bandicoot-api .
```

2. **Run the container:**
```bash
docker run -p 8080:8080 bandicoot-api
```

3. **Access the API:**
- http://localhost:8080

## API Endpoints

### Public Endpoints

#### GET /health
Health check and model status.

```bash
curl http://localhost:8000/api/v1/health
```

Response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "model_loaded": true,
  "timestamp": "2025-11-23T10:30:00Z"
}
```

### Protected Endpoints

**Authentication:** Include `X-API-Key` header when `REQUIRE_AUTH=true`

#### POST /train_clusters
Train the clustering model and learn MDP parameters from historical data.

```bash
curl -X POST http://localhost:8000/api/v1/train_clusters \
  -H "Content-Type: application/json" \
  -d '{
    "n_clusters": 20,
    "min_observations": 10
  }'
```

Response:
```json
{
  "status": "success",
  "n_clusters": 20,
  "n_caregivers": 1500,
  "silhouette_score": 0.65,
  "clusters": [
    {
      "cluster_id": 0,
      "n_caregivers": 150,
      "w_responsive": 0.35,
      "w_unresponsive": 0.85,
      "retention_R": 0.82,
      "recovery_U": 0.34
    }
  ],
  "trained_at": "2025-11-23T10:30:00Z",
  "model_version": "1.0.0"
}
```

#### POST /recommend
Generate top-K caregiver recommendations.

```bash
curl -X POST http://localhost:8000/api/v1/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "budget": 100
  }'
```

Response:
```json
{
  "recommendations": [
    {
      "caregiver_id": "CG-12345",
      "priority_score": 0.87,
      "current_state": "Unresponsive",
      "cluster_id": 5,
      "reason": "High dropout risk, needs immediate attention"
    }
  ],
  "metadata": {
    "total_evaluated": 150000,
    "budget": 100,
    "generated_at": "2025-11-23T10:30:00Z",
    "model_version": "1.0.0"
  }
}
```

#### POST /precompute_indices
Precompute Whittle indices for all (cluster, state) pairs.

```bash
curl -X POST http://localhost:8000/api/v1/precompute_indices
```

#### POST /update_state
Update engagement states for caregivers.

```bash
curl -X POST http://localhost:8000/api/v1/update_state \
  -H "Content-Type: application/json" \
  -d '{
    "updates": [
      {"caregiver_id": "CG-12345", "state": 0},
      {"caregiver_id": "CG-67890", "state": 1}
    ]
  }'
```

## Configuration

Create a `.env` file (copy from `.env.example`):

```bash
# Authentication
REQUIRE_AUTH=false
API_KEY=your-secret-api-key-here

# Model Settings
N_CLUSTERS=20
GAMMA=0.99
ALPHA=1.0
MIN_OBSERVATIONS=10

# Logging
LOG_LEVEL=INFO
```

## Testing

Run the integration tests:

```bash
PYTHONPATH=/path/to/bandicoot pytest tests/test_api_integration.py -v
```

## Architecture

```
app/
├── __init__.py           # Package initialization
├── main.py               # FastAPI application
├── config.py             # Settings and configuration
├── dependencies.py       # Dependency injection and auth
├── models.py             # Pydantic request/response models
└── api/
    ├── __init__.py
    └── routes.py         # API endpoint handlers
```

## Deployment

### Google Cloud Run

1. **Build and push image:**
```bash
gcloud builds submit --tag gcr.io/PROJECT_ID/bandicoot-api
```

2. **Deploy:**
```bash
gcloud run deploy bandicoot-api \
  --image gcr.io/PROJECT_ID/bandicoot-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

3. **Set environment variables:**
```bash
gcloud run services update bandicoot-api \
  --set-env-vars="REQUIRE_AUTH=true,API_KEY=your-secret-key"
```

## Production Checklist

Before deploying to production:

- [ ] Set `REQUIRE_AUTH=true` in environment
- [ ] Generate secure API key: `openssl rand -hex 32`
- [ ] Configure PostgreSQL connection (DATABASE_URL)
- [ ] Set up Redis cache (REDIS_URL)
- [ ] Configure monitoring and alerting
- [ ] Set up CI/CD pipeline
- [ ] Load test with production-scale data
- [ ] Document API for stakeholders
- [ ] Train legal/ethics review for A/B testing

## Support

For issues and questions:
- GitHub Issues: https://github.com/anthropics/bandicoot/issues
- Documentation: /docs
