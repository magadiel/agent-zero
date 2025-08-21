#!/bin/bash

# Integration Tests for Multi-Container Agile AI System
# This script tests container communication, resource allocation, and network security

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0

# Configuration
COMPOSE_FILE="docker-compose.yml"
TIMEOUT=300  # 5 minutes timeout for container startup
HEALTH_CHECK_INTERVAL=5

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    
    if [ "$status" = "PASS" ]; then
        echo -e "${GREEN}✓${NC} $message"
        ((TESTS_PASSED++))
    elif [ "$status" = "FAIL" ]; then
        echo -e "${RED}✗${NC} $message"
        ((TESTS_FAILED++))
    elif [ "$status" = "INFO" ]; then
        echo -e "${YELLOW}ℹ${NC} $message"
    fi
}

# Function to check if a service is healthy
check_service_health() {
    local service=$1
    local max_attempts=$((TIMEOUT / HEALTH_CHECK_INTERVAL))
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if docker-compose ps | grep -q "$service.*healthy"; then
            return 0
        fi
        sleep $HEALTH_CHECK_INTERVAL
        ((attempt++))
    done
    
    return 1
}

# Function to test HTTP endpoint
test_http_endpoint() {
    local endpoint=$1
    local expected_status=$2
    local description=$3
    
    response=$(curl -s -o /dev/null -w "%{http_code}" "$endpoint" 2>/dev/null || echo "000")
    
    if [ "$response" = "$expected_status" ]; then
        print_status "PASS" "$description (HTTP $response)"
        return 0
    else
        print_status "FAIL" "$description (Expected: $expected_status, Got: $response)"
        return 1
    fi
}

# Function to test container communication
test_container_communication() {
    local from_container=$1
    local to_container=$2
    local to_port=$3
    local description=$4
    
    if docker exec "$from_container" curl -s -f "http://$to_container:$to_port/health" >/dev/null 2>&1; then
        print_status "PASS" "$description"
        return 0
    else
        print_status "FAIL" "$description"
        return 1
    fi
}

# Function to test resource limits
test_resource_limits() {
    local container=$1
    local expected_cpu=$2
    local expected_memory=$3
    local description=$4
    
    # Get actual resource limits
    cpu_limit=$(docker inspect "$container" --format='{{.HostConfig.NanoCpus}}' | awk '{print $1/1000000000}')
    memory_limit=$(docker inspect "$container" --format='{{.HostConfig.Memory}}' | awk '{print $1/1073741824}')
    
    # Compare with expected (allowing small variance)
    cpu_ok=$(echo "$cpu_limit <= $expected_cpu * 1.1" | bc -l)
    memory_ok=$(echo "$memory_limit <= $expected_memory * 1.1" | bc -l)
    
    if [ "$cpu_ok" = "1" ] && [ "$memory_ok" = "1" ]; then
        print_status "PASS" "$description (CPU: ${cpu_limit}cores, Memory: ${memory_limit}GB)"
        return 0
    else
        print_status "FAIL" "$description (Expected CPU: ${expected_cpu}, Got: ${cpu_limit}; Expected Memory: ${expected_memory}GB, Got: ${memory_limit}GB)"
        return 1
    fi
}

# Function to test network isolation
test_network_isolation() {
    local container=$1
    local network=$2
    local should_have_access=$3
    local description=$4
    
    networks=$(docker inspect "$container" --format='{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}')
    
    if [[ $networks == *"$network"* ]]; then
        if [ "$should_have_access" = "true" ]; then
            print_status "PASS" "$description - Container has access to $network"
            return 0
        else
            print_status "FAIL" "$description - Container should NOT have access to $network"
            return 1
        fi
    else
        if [ "$should_have_access" = "false" ]; then
            print_status "PASS" "$description - Container correctly isolated from $network"
            return 0
        else
            print_status "FAIL" "$description - Container should have access to $network"
            return 1
        fi
    fi
}

# Main test execution
main() {
    echo "=========================================="
    echo "Agile AI Multi-Container Integration Tests"
    echo "=========================================="
    echo ""
    
    # Step 1: Build and start containers
    print_status "INFO" "Building and starting containers..."
    docker-compose -f "$COMPOSE_FILE" build --quiet
    docker-compose -f "$COMPOSE_FILE" up -d
    
    # Step 2: Wait for services to be healthy
    print_status "INFO" "Waiting for services to be healthy..."
    
    services=("control-layer" "coordinator" "redis" "postgres")
    for service in "${services[@]}"; do
        if check_service_health "$service"; then
            print_status "PASS" "$service is healthy"
        else
            print_status "FAIL" "$service failed health check"
        fi
    done
    
    echo ""
    echo "=== Testing Container Communication ==="
    
    # Step 3: Test API endpoints
    test_http_endpoint "http://localhost:8000/health" "200" "Control Layer API"
    test_http_endpoint "http://localhost:8001/health" "200" "Coordinator WebUI"
    test_http_endpoint "http://localhost:9090" "200" "Prometheus Metrics"
    test_http_endpoint "http://localhost:3000" "200" "Grafana Dashboard"
    
    # Step 4: Test inter-container communication
    test_container_communication "coordinator" "control-layer" "8000" "Coordinator → Control Layer"
    test_container_communication "team-customer-agent-1" "coordinator" "8002" "Customer Team → Coordinator"
    test_container_communication "team-operations-agent-1" "coordinator" "8002" "Operations Team → Coordinator"
    
    # Test Redis connectivity
    if docker exec agile-ai-redis redis-cli ping | grep -q PONG; then
        print_status "PASS" "Redis is accessible"
    else
        print_status "FAIL" "Redis connection failed"
    fi
    
    # Test PostgreSQL connectivity
    if docker exec agile-ai-postgres pg_isready -U agile_user | grep -q "accepting connections"; then
        print_status "PASS" "PostgreSQL is accessible"
    else
        print_status "FAIL" "PostgreSQL connection failed"
    fi
    
    echo ""
    echo "=== Testing Resource Allocation ==="
    
    # Step 5: Test resource limits
    test_resource_limits "agile-ai-control" "2.0" "2" "Control Layer resources"
    test_resource_limits "agile-ai-coordinator" "2.0" "3" "Coordinator resources"
    test_resource_limits "team-customer-agent-1" "1.0" "2" "Customer Agent 1 resources"
    test_resource_limits "team-operations-agent-1" "1.0" "2" "Operations Agent 1 resources"
    
    echo ""
    echo "=== Testing Network Security ==="
    
    # Step 6: Test network isolation
    test_network_isolation "agile-ai-control" "control-network" "true" "Control Layer network access"
    test_network_isolation "agile-ai-control" "coordination-network" "true" "Control Layer coordination access"
    test_network_isolation "agile-ai-control" "execution-network" "false" "Control Layer execution isolation"
    
    test_network_isolation "agile-ai-coordinator" "coordination-network" "true" "Coordinator network access"
    test_network_isolation "agile-ai-coordinator" "execution-network" "true" "Coordinator execution access"
    
    test_network_isolation "team-customer-agent-1" "execution-network" "true" "Customer Team network access"
    test_network_isolation "team-customer-agent-1" "control-network" "false" "Customer Team control isolation"
    
    echo ""
    echo "=== Testing Data Persistence ==="
    
    # Step 7: Test volume mounts
    volumes=("control-storage" "coordinator-storage" "redis-data" "postgres-data" "shared-data")
    for volume in "${volumes[@]}"; do
        if docker volume ls | grep -q "$volume"; then
            print_status "PASS" "Volume $volume exists"
        else
            print_status "FAIL" "Volume $volume not found"
        fi
    done
    
    echo ""
    echo "=== Testing Security Features ==="
    
    # Test JWT authentication on Control API
    response=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer invalid_token" "http://localhost:8000/api/v1/ethics/validate" 2>/dev/null || echo "000")
    if [ "$response" = "401" ] || [ "$response" = "403" ]; then
        print_status "PASS" "Control API authentication working (HTTP $response)"
    else
        print_status "FAIL" "Control API authentication not enforced (HTTP $response)"
    fi
    
    # Test read-only filesystem where applicable
    if docker exec agile-ai-control touch /app/control/config/test.txt 2>/dev/null; then
        print_status "FAIL" "Control config should be read-only"
        docker exec agile-ai-control rm /app/control/config/test.txt 2>/dev/null
    else
        print_status "PASS" "Control config is read-only"
    fi
    
    echo ""
    echo "=== Testing Scaling Capabilities ==="
    
    # Test scaling innovation team
    print_status "INFO" "Testing horizontal scaling of innovation team..."
    docker-compose -f "$COMPOSE_FILE" up -d --scale team-innovation=10
    sleep 10
    
    innovation_count=$(docker-compose ps | grep -c "team-innovation" || echo 0)
    if [ "$innovation_count" -ge 7 ]; then
        print_status "PASS" "Innovation team scaled to $innovation_count instances"
    else
        print_status "FAIL" "Innovation team scaling failed (Expected: >=7, Got: $innovation_count)"
    fi
    
    echo ""
    echo "=========================================="
    echo "Test Results Summary"
    echo "=========================================="
    echo -e "${GREEN}Passed:${NC} $TESTS_PASSED"
    echo -e "${RED}Failed:${NC} $TESTS_FAILED"
    
    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "\n${GREEN}All tests passed successfully!${NC}"
        exit_code=0
    else
        echo -e "\n${RED}Some tests failed. Please review the output above.${NC}"
        exit_code=1
    fi
    
    # Cleanup option
    read -p "Do you want to stop and remove containers? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "INFO" "Cleaning up..."
        docker-compose -f "$COMPOSE_FILE" down
    fi
    
    exit $exit_code
}

# Run main function
main "$@"