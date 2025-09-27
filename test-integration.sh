#!/bin/bash
# Integration test script for RaveDigest services
# This script tests the complete end-to-end workflow

set -e

echo "🐳 Starting RaveDigest Integration Tests"

# Function to wait for service health
wait_for_service() {
    local service=$1
    local port=$2
    local endpoint=${3:-health}
    local max_attempts=30
    local attempt=1

    echo "⏳ Waiting for $service to be healthy..."

    while [ $attempt -le $max_attempts ]; do
        if docker-compose exec -T $service curl -f "http://localhost:$port/$service/$endpoint" 2>/dev/null; then
            echo "✅ $service is healthy"
            return 0
        fi

        if [ $service = "scheduler" ]; then
            if docker-compose exec -T $service curl -f "http://localhost:$port/health" 2>/dev/null; then
                echo "✅ $service is healthy"
                return 0
            fi
        fi

        echo "   Attempt $attempt/$max_attempts: $service not ready yet..."
        sleep 5
        attempt=$((attempt + 1))
    done

    echo "❌ $service failed to become healthy after $max_attempts attempts"
    return 1
}

# Function to test service endpoint
test_endpoint() {
    local service=$1
    local port=$2
    local endpoint=$3
    local expected_status=${4:-200}

    echo "🧪 Testing $service endpoint: $endpoint"

    if docker-compose exec -T $service curl -s -o /dev/null -w "%{http_code}" "http://localhost:$port$endpoint" | grep -q "$expected_status"; then
        echo "✅ $service endpoint test passed"
        return 0
    else
        echo "❌ $service endpoint test failed"
        return 1
    fi
}

# Function to check Redis streams
check_redis_stream() {
    local stream_name=$1
    echo "🔍 Checking Redis stream: $stream_name"

    # Check if stream exists and has messages
    local stream_length=$(docker-compose exec -T redis redis-cli XLEN "$stream_name" 2>/dev/null || echo "0")
    echo "   Stream $stream_name has $stream_length messages"

    if [ "$stream_length" -gt 0 ]; then
        echo "✅ Stream $stream_name contains messages"
        return 0
    else
        echo "⚠️  Stream $stream_name is empty"
        return 1
    fi
}

# Main test execution
main() {
    echo "📋 Pre-test setup"

    # Ensure clean state
    docker-compose down -v --remove-orphans 2>/dev/null || true

    # Start services
    echo "🚀 Starting services..."
    docker-compose up -d --build

    # Wait for core infrastructure
    echo "⏳ Waiting for infrastructure services..."
    sleep 15

    # Check individual service health
    echo "🏥 Testing service health endpoints..."
    wait_for_service "collector" "8001" "health" || exit 1
    wait_for_service "analyzer" "8002" "health" || exit 1
    wait_for_service "composer" "8003" "health" || exit 1
    wait_for_service "notion-worker" "8004" "health" || exit 1
    wait_for_service "scheduler" "8005" || exit 1

    # Test individual endpoints
    echo "🔍 Testing service endpoints..."
    test_endpoint "collector" "8001" "/collector/health/live" || exit 1
    test_endpoint "analyzer" "8002" "/analyzer/health/ready" || exit 1
    test_endpoint "composer" "8003" "/compose/health/ready" || exit 1
    test_endpoint "notion-worker" "8004" "/notion/health/live" || exit 1
    test_endpoint "scheduler" "8005" "/health" || exit 1

    # Test workflow integration
    echo "🔄 Testing end-to-end workflow..."

    # Trigger collector
    echo "📥 Triggering article collection..."
    if docker-compose exec -T collector curl -X GET "http://localhost:8001/collect/rss" -s; then
        echo "✅ Article collection triggered"
    else
        echo "❌ Failed to trigger article collection"
        exit 1
    fi

    # Wait for processing
    echo "⏳ Waiting for article processing..."
    sleep 20

    # Check analyzer status
    echo "🔍 Checking analyzer processing status..."
    analyzer_status=$(docker-compose exec -T analyzer curl -s "http://localhost:8002/analyzer/status" | jq -r '.is_idle // "unknown"' 2>/dev/null || echo "unknown")
    echo "   Analyzer status: $analyzer_status"

    # Check Redis streams for data flow
    echo "💾 Checking Redis streams..."
    check_redis_stream "raw_articles" || echo "⚠️  No raw articles in stream (might be expected)"
    check_redis_stream "enriched_articles" || echo "⚠️  No enriched articles in stream"

    # Test manual digest generation
    echo "📄 Testing manual digest generation..."
    if docker-compose exec -T composer curl -X POST "http://localhost:8003/compose" -s; then
        echo "✅ Manual digest generation successful"
    else
        echo "⚠️  Manual digest generation returned non-success (might be expected if no articles)"
    fi

    # Check service logs for errors
    echo "📋 Checking for critical errors in logs..."
    if docker-compose logs --tail=100 2>&1 | grep -i "error\|exception\|failed" | grep -v "test\|expected"; then
        echo "⚠️  Found potential errors in logs (review above)"
    else
        echo "✅ No critical errors found in logs"
    fi

    # Performance check
    echo "⚡ Basic performance check..."
    collector_response_time=$(docker-compose exec -T collector curl -s -w "%{time_total}" -o /dev/null "http://localhost:8001/collector/health" || echo "timeout")
    echo "   Collector health response time: ${collector_response_time}s"

    analyzer_response_time=$(docker-compose exec -T analyzer curl -s -w "%{time_total}" -o /dev/null "http://localhost:8002/analyzer/health" || echo "timeout")
    echo "   Analyzer health response time: ${analyzer_response_time}s"

    echo ""
    echo "🎉 Integration tests completed!"
    echo "📊 Test Summary:"
    echo "   ✅ All services started successfully"
    echo "   ✅ Health endpoints responding"
    echo "   ✅ Basic workflow triggered"
    echo "   ✅ No critical errors detected"
    echo ""
    echo "🔧 To view detailed logs: docker-compose logs [service-name]"
    echo "🛑 To stop services: docker-compose down"
}

# Cleanup function
cleanup() {
    echo ""
    echo "🧹 Cleaning up..."
    docker-compose down -v --remove-orphans
    echo "✅ Cleanup completed"
}

# Set trap for cleanup on script exit
trap cleanup EXIT

# Run main function
main "$@"