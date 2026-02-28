#!/bin/bash
# Performance Benchmarking Script

set -e

echo "⚡ Documentale Performance Benchmarking"
echo "========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
API_URL="${1:-http://localhost:8000}"
TEST_TYPE="${2:-smoke}"
RESULTS_DIR="performance/results"
BASELINE_FILE="performance/baseline.json"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create results directory
mkdir -p "$RESULTS_DIR"

echo -e "${BLUE}Configuration:${NC}"
echo "  API URL: $API_URL"
echo "  Test Type: $TEST_TYPE"
echo "  Results Dir: $RESULTS_DIR"
echo ""

# Check if k6 is installed
if ! command -v k6 &> /dev/null; then
  echo -e "${RED}❌ k6 is not installed${NC}"
  echo "Install k6 from: https://k6.io/docs/getting-started/installation/"
  exit 1
fi

echo -e "${GREEN}✅ k6 found${NC}"

# Function to run k6 test
run_k6_test() {
  local test_type=$1
  local output_file="$RESULTS_DIR/k6-${test_type}-${TIMESTAMP}.json"

  echo ""
  echo -e "${BLUE}Running k6 ${test_type} test...${NC}"

  case $test_type in
    smoke)
      k6 run \
        -u 1 -d 10s \
        -e BASE_URL="$API_URL" \
        -o json="$output_file" \
        performance/k6-tests.js
      ;;
    load)
      k6 run \
        -u 50 -d 5m \
        -e BASE_URL="$API_URL" \
        -o json="$output_file" \
        performance/k6-tests.js
      ;;
    stress)
      k6 run \
        --stage 10s:0 \
        --stage 30s:50 \
        --stage 1m:100 \
        --stage 1m:200 \
        --stage 30s:0 \
        -e BASE_URL="$API_URL" \
        -o json="$output_file" \
        performance/k6-tests.js
      ;;
    soak)
      echo -e "${YELLOW}⚠️  Soak test will run for 1 hour${NC}"
      k6 run \
        -u 50 -d 1h \
        -e BASE_URL="$API_URL" \
        -o json="$output_file" \
        performance/k6-tests.js
      ;;
    *)
      echo -e "${RED}Unknown test type: $test_type${NC}"
      exit 1
      ;;
  esac

  echo -e "${GREEN}✅ Test completed: $output_file${NC}"
}

# Function to generate report
generate_report() {
  local test_type=$1
  local output_file="$RESULTS_DIR/k6-${test_type}-${TIMESTAMP}.json"

  if [ ! -f "$output_file" ]; then
    echo -e "${RED}Results file not found: $output_file${NC}"
    return 1
  fi

  echo ""
  echo -e "${BLUE}═════════════════════════════════════════════${NC}"
  echo -e "${BLUE}Performance Test Report: $test_type${NC}"
  echo -e "${BLUE}═════════════════════════════════════════════${NC}"

  # Extract key metrics
  echo ""
  echo -e "${BLUE}Response Times (ms):${NC}"

  if command -v jq &> /dev/null; then
    jq '.data.result[0].data.summary |
      {
        "avg": .avg_request_duration,
        "min": .min_request_duration,
        "max": .max_request_duration,
        "p95": .p95_request_duration,
        "p99": .p99_request_duration
      }' "$output_file" 2>/dev/null || echo "  (Use jq to parse results)"
  else
    echo "  Install jq for detailed results: https://stedolan.github.io/jq/"
  fi

  echo ""
  echo -e "${BLUE}Error Rate:${NC}"
  echo "  Check results file for error details"

  echo ""
  echo -e "${BLUE}Results File:${NC}"
  echo "  $output_file"
}

# Function to compare with baseline
compare_baseline() {
  local test_type=$1

  echo ""
  echo -e "${BLUE}═════════════════════════════════════════════${NC}"
  echo -e "${BLUE}Baseline Comparison${NC}"
  echo -e "${BLUE}═════════════════════════════════════════════${NC}"

  if [ ! -f "$BASELINE_FILE" ]; then
    echo -e "${YELLOW}⚠️  Baseline file not found: $BASELINE_FILE${NC}"
    return 1
  fi

  echo ""
  echo -e "${BLUE}Expected Performance Targets:${NC}"

  if command -v jq &> /dev/null; then
    echo "Response Time Thresholds:"
    jq '.baselines.performance_thresholds.response_time' "$BASELINE_FILE"

    echo ""
    echo "Error Rate Thresholds:"
    jq '.baselines.performance_thresholds.errors' "$BASELINE_FILE"
  else
    echo "View baseline.json for targets"
  fi
}

# Main execution
echo -e "${BLUE}Starting benchmark...${NC}"
echo ""

# Run k6 test
run_k6_test "$TEST_TYPE"

# Generate report
generate_report "$TEST_TYPE"

# Compare with baseline
compare_baseline "$TEST_TYPE"

# Create summary
echo ""
echo -e "${BLUE}═════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Benchmarking Complete!${NC}"
echo -e "${BLUE}═════════════════════════════════════════════${NC}"

echo ""
echo "📊 Results Summary:"
echo "  Test Type: $TEST_TYPE"
echo "  Timestamp: $TIMESTAMP"
echo "  Results: $RESULTS_DIR/k6-${TEST_TYPE}-${TIMESTAMP}.json"
echo ""

echo "📈 Next Steps:"
echo "  1. Review results in $RESULTS_DIR"
echo "  2. Compare against baseline.json"
echo "  3. Identify bottlenecks"
echo "  4. Optimize code if needed"
echo ""

echo "📚 Documentation:"
echo "  - Guide: docs/PERFORMANCE_TESTING.md"
echo "  - README: performance/README.md"
echo ""

# Prompt for test type
if [ "$TEST_TYPE" = "smoke" ]; then
  echo "💡 For more comprehensive testing:"
  echo "  ./scripts/benchmark.sh $API_URL load"
  echo "  ./scripts/benchmark.sh $API_URL stress"
fi
