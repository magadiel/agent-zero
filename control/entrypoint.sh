#!/bin/bash
set -e

# Function to wait for dependencies
wait_for_service() {
    local host=$1
    local port=$2
    local service=$3
    
    echo "Waiting for $service at $host:$port..."
    while ! nc -z "$host" "$port"; do
        sleep 1
    done
    echo "$service is ready!"
}

# Environment setup
export PYTHONPATH=/app/control:$PYTHONPATH

# Create necessary directories if they don't exist
mkdir -p /app/control/storage /app/control/logs /app/control/config

# Initialize database if needed
if [ ! -f "/app/control/storage/audit.db" ]; then
    echo "Initializing audit database..."
    python -c "
from audit_logger import AuditLogger
logger = AuditLogger()
print('Audit database initialized')
"
fi

# Check if we need to wait for other services
if [ -n "$WAIT_FOR_SERVICES" ]; then
    IFS=',' read -ra SERVICES <<< "$WAIT_FOR_SERVICES"
    for service in "${SERVICES[@]}"; do
        IFS=':' read -ra ADDR <<< "$service"
        wait_for_service "${ADDR[0]}" "${ADDR[1]}" "$service"
    done
fi

# Run migrations if needed (placeholder for future)
# python manage.py migrate

# Start the application
echo "Starting Control Layer API..."
exec "$@"