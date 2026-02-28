# Performance Testing

This directory contains performance and load testing scripts for the Documentale API.

## Structure

- `k6-tests.js` - k6 load testing script
- `locustfile.py` - Locust load testing script
- `requirements.txt` - Python dependencies for Locust

## Quick Start

### Using k6

```bash
# Install k6
brew install k6  # macOS
sudo apt-get install k6  # Ubuntu

# Run tests
k6 run k6-tests.js

# With custom load
k6 run -u 100 -d 5m k6-tests.js
```

### Using Locust

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests with web UI
locust -f locustfile.py --host=http://localhost:8000

# Headless mode
locust -f locustfile.py \
  --host=http://localhost:8000 \
  -u 100 -r 10 -t 5m \
  --headless
```

## Test Scenarios

### Supported Endpoints

- `GET /api/documents` - List documents
- `GET /api/documents/search` - Search documents
- `GET /api/documents/fts` - Full-text search
- `GET /api/documents/:id` - Get document details
- `GET /api/documents?status=*` - Filter documents
- `GET /api/analytics/stats` - Analytics

### User Types

**k6:**
- Generic API user
- Simulates realistic user behavior

**Locust:**
- `DocumentAPIUser` - Regular user (75% of load)
- `AdminUser` - Admin operations (25% of load)

## Performance Targets

| Metric | Target |
|--------|--------|
| P95 Latency | < 500ms |
| P99 Latency | < 1000ms |
| Error Rate | < 1% |
| Throughput | > 100 RPS |

## Load Test Stages

### Smoke Test
- Users: 1
- Duration: 10s
- Purpose: Validate basic functionality

### Load Test
- Users: 50
- Duration: 5 minutes
- Purpose: Find baseline performance

### Stress Test
- Users: Ramp from 0 to 200
- Duration: 3 minutes
- Purpose: Find breaking point

### Soak Test
- Users: 50
- Duration: 2 hours
- Purpose: Detect memory leaks

## Interpreting Results

### k6 Output

```
✓ status is 200
✓ response time < 500ms

http_req_duration: avg=245ms, min=100ms, max=890ms, p(95)=450ms
http_req_failed: 0.5%
iterations: 1500
```

### Locust Web UI

- **Statistics Tab**: Response times and request counts
- **Charts Tab**: Real-time performance graphs
- **Failures Tab**: Errors and exceptions
- **Current RPS**: Requests per second

## Best Practices

1. **Baseline First**: Establish metrics before optimization
2. **Incremental Load**: Gradually increase users
3. **Monitor System**: Check CPU, memory, database
4. **Identify Bottlenecks**: Use profiling tools
5. **Document Results**: Keep historical records
6. **Regular Testing**: Run tests automatically

## Troubleshooting

### API Errors

```bash
# Check API is running
curl http://localhost:8000/api/documents

# Check logs
tail -f ../backend/logs/app.log
```

### Connection Issues

```bash
# Test connectivity
ping localhost
curl -v http://localhost:8000/health
```

### Low Performance

1. Check database indexes
2. Review slow query logs
3. Enable caching
4. Check for memory leaks

## Continuous Integration

Performance tests run on schedule:
- Daily at 2 AM UTC
- On manual trigger
- On code changes

Results are uploaded as artifacts and compared against baseline.

## References

- [k6 Documentation](https://k6.io/docs/)
- [Locust Documentation](https://docs.locust.io/)
- [Performance Testing Guide](../docs/PERFORMANCE_TESTING.md)

## Support

For issues or questions, refer to:
- GitHub Issues
- Performance Testing documentation
- Individual tool documentation
