# API Design & Endpoints

**Version:** 1.0
**Last Updated:** November 2025
**Parent Doc:** [00-overview.md](00-overview.md)

---

## Overview

Bandicoot exposes a RESTful API built with FastAPI for:
1. **Batch Training** - Weekly model updates
2. **Real-Time Recommendations** - Get top-K priority caregivers
3. **State Management** - Update caregiver engagement states
4. **Health/Monitoring** - Service status and metrics

**Base URL:** `https://bandicoot-api.run.app` (Cloud Run)

---

## Authentication

### API Key (Phase 1)
```http
Authorization: Bearer <API_KEY>
```

**Implementation:**
```python
from fastapi import Security, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verify API key from Authorization header."""
    if credentials.credentials != os.getenv("BANDICOOT_API_KEY"):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials.credentials
```

**Deployment:**
- Store API key in Google Secret Manager
- Rotate keys quarterly
- Rate limit: 100 req/min per key

---

## Endpoints

### 1. POST `/train_clusters`

**Purpose:** Trigger clustering and MDP learning from historical data.

**Access:** Admin only (batch job)

**Request:**
```json
{
  "data_start_date": "2025-05-01",
  "data_end_date": "2025-11-01",
  "num_clusters": 20,  // Optional, uses elbow method if null
  "force_retrain": false  // Skip if trained recently
}
```

**Response:**
```json
{
  "job_id": 12345,
  "status": "running",
  "started_at": "2025-11-22T10:00:00Z",
  "estimated_duration_minutes": 30,
  "num_caregivers": 185000
}
```

**Implementation:**
```python
from fastapi import BackgroundTasks

@app.post("/train_clusters")
async def train_clusters(
    request: TrainClustersRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key)
):
    """Trigger clustering and MDP learning."""

    # Create training job record
    job_id = create_training_job(
        job_type='clustering',
        input_data_start=request.data_start_date,
        input_data_end=request.data_end_date
    )

    # Run training in background
    background_tasks.add_task(
        run_clustering_pipeline,
        job_id=job_id,
        num_clusters=request.num_clusters
    )

    return {
        "job_id": job_id,
        "status": "running",
        "started_at": datetime.now()
    }
```

**Error Codes:**
- `400`: Invalid date range
- `409`: Training already in progress
- `500`: Internal error

---

### 2. POST `/precompute_indices`

**Purpose:** Compute and cache Whittle indices for all (cluster, state) pairs.

**Access:** Admin only (runs after `/train_clusters`)

**Request:**
```json
{
  "model_version": "v1.0.2",
  "gamma": 0.95  // Discount factor
}
```

**Response:**
```json
{
  "job_id": 12346,
  "num_indices_computed": 40,  // 20 clusters × 2 states
  "computation_time_seconds": 420,
  "indices_cached_to_redis": true
}
```

**Implementation:**
```python
@app.post("/precompute_indices")
async def precompute_indices(
    request: PrecomputeIndicesRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key)
):
    """Compute Whittle indices and cache in Redis."""

    # Load cluster MDP parameters
    cluster_mdps = load_cluster_mdps(request.model_version)

    indices = {}
    for cluster_id, mdp_params in cluster_mdps.items():
        for state in ['Responsive', 'Unresponsive']:
            index = compute_whittle_index(mdp_params, state, gamma=request.gamma)
            indices[(cluster_id, state)] = index

    # Save to PostgreSQL and Redis
    save_indices_to_db(indices, request.model_version)
    save_indices_to_redis(indices, request.model_version)

    return {
        "num_indices_computed": len(indices),
        "indices_cached_to_redis": True
    }
```

---

### 3. POST `/assign_cluster`

**Purpose:** Assign caregiver(s) to clusters using FO mapper.

**Access:** Admin/ETL pipeline

**Request:**
```json
{
  "caregivers": [
    {
      "caregiver_id": "CG-12345",
      "age": 28,
      "district": "Bihar-Patna",
      "parity": 2,
      "phone_reliable": true,
      "enrollment_source": "hospital"
    }
  ]
}
```

**Response:**
```json
{
  "assignments": [
    {
      "caregiver_id": "CG-12345",
      "cluster_id": 5,
      "confidence": 0.87,
      "warmup_end_date": "2026-01-03"
    }
  ]
}
```

**Implementation:**
```python
@app.post("/assign_cluster")
async def assign_cluster(
    request: AssignClusterRequest,
    api_key: str = Depends(verify_api_key)
):
    """Assign caregivers to clusters using FO mapper."""

    # Load FO mapper from Redis
    fo_model = load_fo_mapper_from_redis()

    assignments = []
    for caregiver in request.caregivers:
        cluster_id = fo_model.predict([caregiver.dict()])[0]
        confidence = fo_model.predict_proba([caregiver.dict()]).max()

        # Calculate warmup end date
        warmup_end = assign_warmup_end_date(caregiver.enrolled_at)

        assignments.append({
            "caregiver_id": caregiver.caregiver_id,
            "cluster_id": int(cluster_id),
            "confidence": float(confidence),
            "warmup_end_date": warmup_end.isoformat()
        })

        # Save to database
        save_caregiver_state(caregiver.caregiver_id, cluster_id, warmup_end)

    return {"assignments": assignments}
```

---

### 4. POST `/update_state`

**Purpose:** Update caregiver engagement states (bulk or single).

**Access:** ETL pipeline

**Request:**
```json
{
  "updates": [
    {
      "caregiver_id": "CG-12345",
      "new_state": "Responsive",
      "reason": "SMS opened",
      "timestamp": "2025-11-22T09:30:00Z"
    },
    {
      "caregiver_id": "CG-67890",
      "new_state": "Unresponsive",
      "reason": "No interaction 7+ days"
    }
  ]
}
```

**Response:**
```json
{
  "updated": 2,
  "failed": 0,
  "errors": []
}
```

**Implementation:**
```python
@app.post("/update_state")
async def update_state(
    request: UpdateStateRequest,
    api_key: str = Depends(verify_api_key)
):
    """Bulk update caregiver states."""

    updated = 0
    failed = 0
    errors = []

    for update in request.updates:
        try:
            # Update PostgreSQL
            update_caregiver_state_db(
                update.caregiver_id,
                update.new_state,
                update.timestamp
            )

            # Update Redis cache
            update_caregiver_state_redis(
                update.caregiver_id,
                update.new_state
            )

            updated += 1

        except Exception as e:
            failed += 1
            errors.append({
                "caregiver_id": update.caregiver_id,
                "error": str(e)
            })

    return {
        "updated": updated,
        "failed": failed,
        "errors": errors
    }
```

---

### 5. GET `/recommend`

**Purpose:** Get top-K priority caregivers for outreach.

**Access:** Public (with API key)

**Query Parameters:**
- `budget` (required): Number of caregivers to return (K)
- `district` (optional): Filter by district
- `exclude_control` (optional): Exclude A/B test control group (default: true)
- `model_version` (optional): Use specific model version (default: latest)

**Request:**
```http
GET /recommend?budget=100&district=Bihar-Patna&exclude_control=true
```

**Response:**
```json
{
  "recommendations": [
    {
      "caregiver_id": "CG-12345",
      "priority_score": 0.87,
      "current_state": "Unresponsive",
      "cluster_id": 5,
      "reason": "High dropout risk, responsive to interventions",
      "district": "Bihar-Patna",
      "last_vaccination": "2025-10-15",
      "days_since_contact": 12
    }
  ],
  "metadata": {
    "total_evaluated": 45000,
    "budget": 100,
    "filters_applied": {"district": "Bihar-Patna"},
    "generated_at": "2025-11-22T10:30:00Z",
    "model_version": "v1.0.2",
    "cached": false
  }
}
```

**Implementation:**
```python
@app.get("/recommend")
async def recommend(
    budget: int,
    district: Optional[str] = None,
    exclude_control: bool = True,
    model_version: Optional[str] = None,
    api_key: str = Depends(verify_api_key)
):
    """Generate top-K priority recommendations."""

    # Check cache
    cache_key = f"recommend:{date.today()}:{budget}:{hash(filters)}"
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    # Fetch caregiver states
    query = """
        SELECT cs.caregiver_id, cs.cluster_id, cs.current_state,
               cs.district, cs.last_vaccination, cs.last_sms_sent
        FROM caregiver_states cs
        WHERE cs.warmup_end_date <= CURRENT_DATE
    """

    if exclude_control:
        query += " AND (cs.ab_test_group IS NULL OR cs.ab_test_group = 'treatment')"

    if district:
        query += f" AND cs.district = '{district}'"

    caregivers = db.execute(query).fetchall()

    # Lookup Whittle indices from Redis
    recommendations = []
    for cg in caregivers:
        index_key = f"whittle:{model_version}:{cg.cluster_id}:{cg.current_state}"
        priority_score = float(redis_client.get(index_key) or 0)

        recommendations.append({
            "caregiver_id": cg.caregiver_id,
            "priority_score": priority_score,
            "current_state": cg.current_state,
            "cluster_id": cg.cluster_id,
            "district": cg.district,
            "last_vaccination": cg.last_vaccination,
            "days_since_contact": (date.today() - cg.last_sms_sent).days
        })

    # Sort by priority_score descending
    recommendations.sort(key=lambda x: x['priority_score'], reverse=True)

    # Return top-K
    top_k = recommendations[:budget]

    # Add reason (simple heuristic for MVP)
    for rec in top_k:
        if rec['current_state'] == 'Unresponsive':
            rec['reason'] = "High dropout risk, responsive to interventions"
        else:
            rec['reason'] = "Maintain engagement, prevent lapse"

    result = {
        "recommendations": top_k,
        "metadata": {
            "total_evaluated": len(caregivers),
            "budget": budget,
            "generated_at": datetime.now().isoformat(),
            "model_version": model_version or get_latest_model_version(),
            "cached": False
        }
    }

    # Cache for 1 hour
    redis_client.setex(cache_key, 3600, json.dumps(result))

    return result
```

**Performance Target:** <500ms p95 for budget=100

---

### 6. GET `/health`

**Purpose:** Health check for uptime monitoring.

**Access:** Public (no auth)

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.2",
  "timestamp": "2025-11-22T10:30:00Z",
  "checks": {
    "database": "ok",
    "redis": "ok",
    "latest_model": "v1.0.2"
  }
}
```

**Implementation:**
```python
@app.get("/health")
async def health():
    """Health check endpoint."""
    checks = {
        "database": check_database_connection(),
        "redis": check_redis_connection(),
        "latest_model": get_latest_model_version()
    }

    status = "healthy" if all(v != "error" for v in checks.values()) else "degraded"

    return {
        "status": status,
        "version": os.getenv("APP_VERSION", "unknown"),
        "timestamp": datetime.now().isoformat(),
        "checks": checks
    }
```

---

### 7. GET `/metrics`

**Purpose:** Prometheus metrics export.

**Access:** Internal only (GCP monitoring)

**Response:**
```
# HELP rmab_recommendations_total Total recommendations generated
# TYPE rmab_recommendations_total counter
rmab_recommendations_total{ab_group="treatment"} 12450

# HELP rmab_api_latency_seconds API endpoint latency
# TYPE rmab_api_latency_seconds histogram
rmab_api_latency_seconds_bucket{endpoint="/recommend",le="0.5"} 8234
rmab_api_latency_seconds_bucket{endpoint="/recommend",le="1.0"} 8901
```

**Implementation:**
```python
from prometheus_client import Counter, Histogram, generate_latest

recommendations_total = Counter('rmab_recommendations_total', 'Total recommendations', ['ab_group'])
api_latency = Histogram('rmab_api_latency_seconds', 'API latency', ['endpoint'])

@app.get("/metrics")
async def metrics():
    """Export Prometheus metrics."""
    return Response(generate_latest(), media_type="text/plain")
```

---

## Rate Limiting

### Strategy: Token Bucket

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/recommend")
@limiter.limit("100/minute")
async def recommend(...):
    ...
```

**Limits:**
- `/recommend`: 100 req/min per API key
- `/update_state`: 1000 req/min (bulk updates)
- `/train_*`: 1 req/hour (admin endpoints)

---

## Error Handling

### Standard Error Response

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Budget must be between 1 and 1000",
    "details": {
      "field": "budget",
      "value": 5000
    }
  },
  "timestamp": "2025-11-22T10:30:00Z",
  "request_id": "abc-123-def"
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_REQUEST` | 400 | Validation error |
| `UNAUTHORIZED` | 401 | Missing/invalid API key |
| `NOT_FOUND` | 404 | Resource not found |
| `TRAINING_IN_PROGRESS` | 409 | Cannot retrain while job running |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |
| `SERVICE_UNAVAILABLE` | 503 | Database/Redis down |

---

## OpenAPI Documentation

FastAPI auto-generates docs at `/docs` (Swagger UI) and `/redoc`.

**Example:**
```python
@app.get("/recommend", summary="Get priority recommendations")
async def recommend(
    budget: int = Query(..., ge=1, le=1000, description="Number of caregivers to return"),
    district: Optional[str] = Query(None, description="Filter by district"),
    ...
):
    """
    Returns top-K caregivers prioritized by Whittle index.

    The recommendations are based on pre-computed indices from the latest trained model.
    Caregivers still in warmup period (< 6 weeks) are excluded.
    """
    ...
```

---

## Versioning

### URL Versioning (Future)
```
/v1/recommend
/v2/recommend  # Breaking changes
```

For MVP: Use single version, add versioning when needed.

### Model Versioning
- Stored in `model_version` field (e.g., `v1.0.2`)
- Semantic versioning: `MAJOR.MINOR.PATCH`
- Default to latest unless specified

---

## CORS & Security

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://suvita.org"],  # Whitelist Suvita's domain
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization"]
)
```

---

## Testing

### Unit Tests
```python
from fastapi.testclient import TestClient

client = TestClient(app)

def test_recommend_endpoint():
    response = client.get("/recommend?budget=10", headers={"Authorization": "Bearer test_key"})
    assert response.status_code == 200
    assert len(response.json()["recommendations"]) == 10
```

### Load Tests
```bash
# Using Locust
locust -f tests/load_test.py --host https://bandicoot-api.run.app
```

**Target:** 1000 concurrent users, p95 latency <500ms.

---

## Next Steps
1. Implement FastAPI endpoints with Pydantic models
2. Add comprehensive request validation
3. Set up API key rotation in Secret Manager
4. Deploy to Cloud Run staging
5. Load test and optimize caching strategy
