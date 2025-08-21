# Multi-stage build for optimized production image
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/controluser/.local/bin:${PATH}" \
    CONTROL_ENV=production

# Create non-root user for security
RUN useradd -m -u 1000 controluser && \
    mkdir -p /app/control /app/logs /app/storage && \
    chown -R controluser:controluser /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder --chown=controluser:controluser /root/.local /home/controluser/.local

# Set working directory
WORKDIR /app/control

# Copy application code
COPY --chown=controluser:controluser . .

# Create necessary directories
RUN mkdir -p config storage logs tests && \
    chown -R controluser:controluser /app

# Switch to non-root user
USER controluser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Set entrypoint
ENTRYPOINT ["/app/control/entrypoint.sh"]

# Default command
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]