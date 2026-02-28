# Performance Testing Guide

This guide explains how to run performance tests using k6 and Locust.

## Tools Overview

### k6 - Go-based Load Testing
- **Language**: JavaScript
- **Best for**: API load testing, quick scripts
- **Output**: Real-time metrics, JSON reports
- **CI/CD**: Native GitHub Actions support

### Locust - Python-based Load Testing
- **Language**: Python
- **Best for**: Complex scenarios, web UI
- **Output**: Web dashboard, CSV reports
- **CI/CD**: Docker support

## Installation

### k6 Installation

**macOS:**
```bash
brew install k6
```

**Ubuntu/Debian:**
```bash
sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3232A
echo "deb https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6-stable.list
sudo apt-get update
sudo apt-get install k6
```

**Windows:**
```bash
choco install k6
```

**Or download:** https://k6.io/open-source/

### Locust Installation

```bash
pip install locust
```

## Running Tests

### k6 Tests

**Basic run:**
```bash
k6 run performance/k6-tests.js
```

**With custom configuration:**
```bash
k6 run -u 100 -d 30s performance/k6-tests.js
```

**Options:**
- `-u`: Number of virtual users
- `-d`: Test duration
- `-s`: Test stages (ramp up/down)
- `--vus`: Virtual users
- `--duration`: Duration
- `-o`: Output format (json, csv, influxdb)

**Advanced example:**
```bash
k6 run \
  -u 50 \
  -d 5m \
  --vus-max 100 \
  -o json=results.json \
  performance/k6-tests.js
```

**With environment variables:**
```bash
k6 run \
  -e BASE_URL=https://api.example.com \
  -e API_KEY=your-token \
  performance/k6-tests.js
```

**With different stages:**
```bash
k6 run \
  --stage 30s:20 \
  --stage 1m30s:20 \
  --stage 30s:0 \
  performance/k6-tests.js
```

### Locust Tests

**Web UI (recommended):**
```bash
locust -f performance/locustfile.py --host=http://localhost:8000
```
Then open http://localhost:8089

**Headless mode:**
```bash
locust -f performance/locustfile.py \
  --host=http://localhost:8000 \
  --users 100 \
  --spawn-rate 10 \
  --run-time 5m \
  --headless
```

**With CSV output:**
```bash
locust -f performance/locustfile.py \
  --host=http://localhost:8000 \
  -u 100 \
  -r 10 \
  -t 5m \
  --headless \
  --csv=results
```

**Options:**
- `-u`: Number of concurrent users
- `-r`: Spawn rate (users per second)
- `-t`: Run time (e.g., 5m, 30s)
- `--headless`: Run without web UI
- `--csv`: CSV report output

## Performance Metrics

### Key Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| P95 Latency | < 500ms | 95th percentile response time |
| P99 Latency | < 1000ms | 99th percentile response time |
| Error Rate | < 1% | Failed requests percentage |
| Throughput | > 100 RPS | Requests per second |
| CPU | < 80% | Server CPU usage |
| Memory | < 80% | Server memory usage |

### Understanding Results

**k6 Output:**
```
✓ status is 200
✓ response time < 500ms
✓ has documents

  http_req_duration..........: avg=245ms, min=100ms, med=220ms, max=890ms, p(90)=400ms, p(95)=450ms
  http_req_failed............: 0.5%
  http_req_received..........: 5 kB avg per request
  http_req_sent..............: 2 kB avg per request
```

**Locust Dashboard:**
- Response Times: Histogram of response times
- Charts: Real-time graphs of RPS and response times
- Failures: Error tracking and logging

## Test Scenarios

### Scenario 1: Smoke Test
```bash
# Quick validation that API works
k6 run -u 1 -d 10s performance/k6-tests.js
```

### Scenario 2: Load Test
```bash
# Sustained load to find baseline performance
k6 run -u 50 -d 5m performance/k6-tests.js
```

### Scenario 3: Stress Test
```bash
# Increase load until system breaks
k6 run \
  --stage 10s:0 \
  --stage 30s:50 \
  --stage 1m:100 \
  --stage 1m:200 \
  --stage 30s:0 \
  performance/k6-tests.js
```

### Scenario 4: Spike Test
```bash
# Sudden traffic spike
k6 run \
  --stage 30s:10 \
  --stage 10s:100 \
  --stage 30s:10 \
  performance/k6-tests.js
```

### Scenario 5: Soak Test
```bash
# Long-running test for memory leaks
k6 run \
  -u 50 \
  -d 2h \
  performance/k6-tests.js
```

## Performance Thresholds

Current thresholds in k6-tests.js:

```javascript
thresholds: {
  http_req_duration: ['p(95)<500', 'p(99)<1000'],
  http_req_failed: ['rate<0.1'],
  errors: ['rate<0.05'],
}
```

### Interpreting Results

- ✅ **Passed**: All thresholds met
- ❌ **Failed**: One or more thresholds exceeded
- ⚠️ **Warning**: Close to threshold

## Optimization Tips

### API Level
1. **Caching**: Implement caching headers
2. **Pagination**: Use reasonable limits
3. **Indexes**: Add database indexes
4. **Compression**: Enable gzip/brotli

### Code Level
1. **Connection pooling**: Reuse connections
2. **Query optimization**: Use efficient queries
3. **Async operations**: Non-blocking calls
4. **Monitoring**: Track slow operations

### Infrastructure
1. **Load balancing**: Distribute requests
2. **Horizontal scaling**: Add more servers
3. **Caching layer**: Redis/Memcached
4. **CDN**: Static content delivery

## CI/CD Integration

### GitHub Actions

Create `.github/workflows/performance.yml`:

```yaml
name: Performance Tests

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  performance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run k6 tests
        run: |
          docker run --rm -v $(pwd):/scripts \
            loadimpact/k6 run /scripts/performance/k6-tests.js

      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: performance-results
          path: results/
```

## Common Issues

### "Connection refused"
- Ensure API is running
- Check host URL is correct
- Verify firewall rules

### "High error rate"
- Check API logs
- Verify database connections
- Test with lower load first

### "Memory leak detected"
- Monitor server memory during test
- Review application logs
- Run soak tests to identify leaks

### "Inconsistent results"
- Use longer test duration
- Run multiple times
- Check for external factors

## Best Practices

1. **Baseline First**: Establish baseline metrics
2. **Incremental Load**: Gradually increase users
3. **Realistic Scenarios**: Simulate actual usage
4. **Regular Testing**: Run tests regularly
5. **Monitor Trends**: Track performance over time
6. **Document Results**: Keep performance records
7. **Alert on Degradation**: Set up alerts for drops

## References

- [k6 Documentation](https://k6.io/docs/)
- [Locust Documentation](https://docs.locust.io/)
- [Performance Testing Guide](https://performancetesting.guide/)
- [Web Performance](https://web.dev/performance/)
