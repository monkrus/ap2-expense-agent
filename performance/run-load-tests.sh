#!/bin/bash
# Run comprehensive load tests for AP2 Expense Agent
# Usage: ./run-load-tests.sh [environment] [test-type]
# Example: ./run-load-tests.sh staging smoke

set -e

ENVIRONMENT="${1:-staging}"
TEST_TYPE="${2:-standard}"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Set base URL based on environment
case $ENVIRONMENT in
  local)
    BASE_URL="http://localhost:8000"
    ;;
  staging)
    BASE_URL="https://staging.your-domain.com"
    ;;
  production)
    BASE_URL="https://your-domain.com"
    ;;
  *)
    echo -e "${RED}Unknown environment: $ENVIRONMENT${NC}"
    echo "Valid environments: local, staging, production"
    exit 1
    ;;
esac

echo -e "${GREEN}Running load tests for AP2 Expense Agent${NC}"
echo -e "Environment: ${YELLOW}${ENVIRONMENT}${NC}"
echo -e "Base URL: ${YELLOW}${BASE_URL}${NC}"
echo -e "Test Type: ${YELLOW}${TEST_TYPE}${NC}"
echo ""

# Create results directory
RESULTS_DIR="./results/$(date +%Y%m%d_%H%M%S)_${ENVIRONMENT}_${TEST_TYPE}"
mkdir -p $RESULTS_DIR

# Test configuration based on type
case $TEST_TYPE in
  smoke)
    USERS=10
    DURATION="5m"
    SPAWN_RATE=1
    ;;
  standard)
    USERS=100
    DURATION="30m"
    SPAWN_RATE=10
    ;;
  stress)
    USERS=500
    DURATION="1h"
    SPAWN_RATE=50
    ;;
  soak)
    USERS=200
    DURATION="4h"
    SPAWN_RATE=20
    ;;
  *)
    echo -e "${RED}Unknown test type: $TEST_TYPE${NC}"
    echo "Valid types: smoke, standard, stress, soak"
    exit 1
    ;;
esac

# Step 1: Run Locust test
echo -e "${GREEN}[1/3] Running Locust load test...${NC}"
echo -e "Users: ${USERS}, Duration: ${DURATION}, Spawn Rate: ${SPAWN_RATE}"

locust -f locust-load-test.py \
  --host=$BASE_URL \
  --users $USERS \
  --spawn-rate $SPAWN_RATE \
  --run-time $DURATION \
  --headless \
  --html $RESULTS_DIR/locust-report.html \
  --csv $RESULTS_DIR/locust \
  2>&1 | tee $RESULTS_DIR/locust.log

if [ $? -eq 0 ]; then
  echo -e "${GREEN}✓ Locust test completed${NC}"
else
  echo -e "${RED}✗ Locust test failed${NC}"
fi

# Step 2: Run K6 test
echo ""
echo -e "${GREEN}[2/3] Running K6 load test...${NC}"

BASE_URL=$BASE_URL k6 run k6-load-test.js \
  --out json=$RESULTS_DIR/k6-results.json \
  --summary-export=$RESULTS_DIR/k6-summary.json \
  2>&1 | tee $RESULTS_DIR/k6.log

if [ $? -eq 0 ]; then
  echo -e "${GREEN}✓ K6 test completed${NC}"
else
  echo -e "${RED}✗ K6 test failed${NC}"
fi

# Step 3: Generate summary report
echo ""
echo -e "${GREEN}[3/3] Generating summary report...${NC}"

cat > $RESULTS_DIR/SUMMARY.md <<EOF
# Load Test Summary

**Environment**: $ENVIRONMENT
**Base URL**: $BASE_URL
**Test Type**: $TEST_TYPE
**Date**: $(date)

## Test Configuration

- Users: $USERS
- Duration: $DURATION
- Spawn Rate: $SPAWN_RATE/sec

## Results

### Locust Results

\`\`\`
$(tail -n 20 $RESULTS_DIR/locust.log)
\`\`\`

See detailed report: [locust-report.html](./locust-report.html)

### K6 Results

\`\`\`
$(tail -n 30 $RESULTS_DIR/k6.log)
\`\`\`

See detailed results: [k6-results.json](./k6-results.json)

## Metrics Summary

| Metric | Target | Result | Status |
|--------|--------|--------|--------|
| P95 Latency | < 2s | TBD | ⚠️ Manual review |
| Error Rate | < 5% | TBD | ⚠️ Manual review |
| Throughput | > 100 req/s | TBD | ⚠️ Manual review |

## Recommendations

- Review detailed reports for performance bottlenecks
- Check error logs for any issues
- Monitor database performance during peak load
- Review auto-scaling behavior

## Files

- \`locust-report.html\` - Locust web report
- \`locust_stats.csv\` - Detailed statistics
- \`locust_failures.csv\` - Failure records
- \`k6-results.json\` - K6 detailed results
- \`k6-summary.json\` - K6 summary
- \`locust.log\` - Locust console output
- \`k6.log\` - K6 console output
EOF

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Load testing completed!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Results saved to: ${YELLOW}${RESULTS_DIR}${NC}"
echo ""
echo -e "Next steps:"
echo -e "1. Review reports: ${YELLOW}open ${RESULTS_DIR}/locust-report.html${NC}"
echo -e "2. Check summary: ${YELLOW}cat ${RESULTS_DIR}/SUMMARY.md${NC}"
echo -e "3. Analyze failures: ${YELLOW}cat ${RESULTS_DIR}/locust_failures.csv${NC}"
echo ""

# Check for critical issues
LOCUST_FAIL_RATE=$(grep -oP 'Fail %: \K[0-9.]+' $RESULTS_DIR/locust.log | tail -1 || echo "0")
if (( $(echo "$LOCUST_FAIL_RATE > 5" | bc -l) )); then
  echo -e "${RED}⚠️  WARNING: Error rate exceeds 5% ($LOCUST_FAIL_RATE%)${NC}"
  exit 1
fi

echo -e "${GREEN}✓ All tests passed${NC}"
