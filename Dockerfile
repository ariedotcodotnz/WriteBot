# Multi-stage Dockerfile for WriteBot (CPU version)
# For GPU support with RTX 50/40/30 series, use Dockerfile.gpu instead

FROM python:3.10-slim AS builder

# Set working directory
WORKDIR /app

# Install system dependencies needed for building
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libhdf5-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libhdf5-310 \
    libhdf5-hl-310 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p webapp/instance webapp/logs webapp/job_storage model/data

# Set environment variables
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/api/health', timeout=5)" || exit 1

# Run database initialization and start the application
CMD ["bash", "-c", "python webapp/init_db.py --auto && gunicorn --bind 0.0.0.0:5000 --workers 4 --threads 2 --timeout 120 --access-logfile - --error-logfile - webapp.app:app"]
