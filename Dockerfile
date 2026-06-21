FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency definitions first for better layer caching
COPY pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir -e "." && \
    pip install --no-cache-dir uvicorn[standard]

# Copy application code
COPY . .

# Create non-root user
RUN useradd -r -s /bin/false appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose API port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8080/health/ || exit 1

# Run the API server
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
