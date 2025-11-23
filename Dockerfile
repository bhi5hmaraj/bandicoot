# Multi-stage Dockerfile for Bandicoot RMAB API
# Optimized for production deployment on Google Cloud Run

# =============================================================================
# Stage 1: Builder
# =============================================================================
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# =============================================================================
# Stage 2: Runtime
# =============================================================================
FROM python:3.11-slim

WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY bandicoot/ /app/bandicoot/
COPY app/ /app/app/

# Set Python path
ENV PYTHONPATH=/app:$PYTHONPATH

# Create non-root user for security (Cloud Run best practice)
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Expose port (Cloud Run uses PORT env var, defaults to 8080)
ENV PORT=8080
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/api/v1/health')"

# Run the application
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 1
