#!/bin/bash

# Build script for Control Layer Docker container
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="development"
BUILD_ONLY=false
NO_CACHE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --prod|--production)
            ENVIRONMENT="production"
            shift
            ;;
        --build-only)
            BUILD_ONLY=true
            shift
            ;;
        --no-cache)
            NO_CACHE=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --prod, --production  Build for production environment"
            echo "  --build-only         Only build, don't start containers"
            echo "  --no-cache          Build without cache"
            echo "  --help              Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}Building Control Layer Docker Container${NC}"
echo "Environment: $ENVIRONMENT"

# Check for .env file
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo -e "${YELLOW}Warning: .env file not found. Copying from .env.example${NC}"
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    echo -e "${YELLOW}Please update .env with your configuration${NC}"
fi

# Build command
BUILD_CMD="docker-compose -f docker-compose.control.yml"

if [ "$ENVIRONMENT" = "development" ]; then
    BUILD_CMD="$BUILD_CMD -f docker-compose.dev.yml"
fi

# Add no-cache flag if requested
if [ "$NO_CACHE" = true ]; then
    BUILD_FLAGS="--no-cache"
else
    BUILD_FLAGS=""
fi

# Change to docker directory
cd "$SCRIPT_DIR"

# Build the containers
echo -e "${GREEN}Building containers...${NC}"
$BUILD_CMD build $BUILD_FLAGS

if [ "$BUILD_ONLY" = true ]; then
    echo -e "${GREEN}Build complete!${NC}"
    exit 0
fi

# Start the containers
echo -e "${GREEN}Starting containers...${NC}"
$BUILD_CMD up -d

# Wait for services to be ready
echo -e "${GREEN}Waiting for services to be ready...${NC}"
sleep 5

# Check health
echo -e "${GREEN}Checking service health...${NC}"
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}Control Layer API is healthy!${NC}"
    echo -e "${GREEN}API Documentation: http://localhost:8000/docs${NC}"
else
    echo -e "${RED}Control Layer API health check failed${NC}"
    echo "Checking logs..."
    $BUILD_CMD logs control-layer | tail -20
    exit 1
fi

echo -e "${GREEN}Control Layer is running!${NC}"
echo ""
echo "Available endpoints:"
echo "  - API: http://localhost:8000"
echo "  - Docs: http://localhost:8000/docs"
echo "  - Health: http://localhost:8000/health"
echo ""
echo "To view logs: docker-compose -f docker-compose.control.yml logs -f"
echo "To stop: docker-compose -f docker-compose.control.yml down"