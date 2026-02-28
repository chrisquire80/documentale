# Documentale Monitoring & Alerting

Complete monitoring setup for Documentale project.

## Quick Links

### Dashboards
- **GitHub Actions**: https://github.com/chrisquire80/documentale/actions
- **Codecov**: https://codecov.io/gh/chrisquire80/documentale
- **SonarQube**: http://localhost:9000 (self-hosted)
- **Local**: `monitoring/dashboards.md`

### Documentation
- [Codecov Setup](docs/CODECOV_SETUP.md) - Coverage tracking
- [Codecov Quickstart](docs/CODECOV_QUICKSTART.md) - 5-minute setup
- [SonarQube Setup](docs/SONARQUBE_SETUP.md) - Code quality
- [SonarQube Quickstart](docs/SONARQUBE_QUICKSTART.md) - Quick guide
- [Performance Testing](docs/PERFORMANCE_TESTING.md) - Load testing
- [Monitoring Setup](docs/MONITORING_SETUP.md) - Alerts & notifications

### Scripts
- `scripts/setup-sonarqube.sh` - SonarQube deployment
- `scripts/benchmark.sh` - Performance benchmarking
- `scripts/install-hooks.sh` - Git hooks setup

## What's Monitored

### ✅ API Health
- Endpoint availability
- Response times
- Error rates
- Database connectivity
- Cache status

### ✅ Performance
- P50, P95, P99 latencies
- Throughput (RPS)
- Resource usage
- Load capacity
- Baseline comparison

### ✅ Code Quality
- Test coverage
- Code smells
- Security issues
- Duplication
- Maintainability

### ✅ Releases
- Dependency updates
- Vulnerability scanning
- Deployment health
- Rollback capability

## Key Metrics

### Performance Targets
```
P95 Latency:  < 500ms ✅
P99 Latency:  < 1000ms ✅
Error Rate:   < 1% ✅
Throughput:   > 100 RPS ✅
```

### Coverage Targets
```
Backend:   60% (±5%) ✅
Frontend:  65% (±5%) ⏳
```

### Quality Targets
```
Code Smells: 0
Security Issues: 0
Duplicates: < 3%
Maintainability: A
```

## Workflows

### Daily (8 AM UTC)
- `monitoring-alerts.yml` - Health check
- Coverage trend analysis
- Performance metrics
- Quality metrics
- Dependency check
- Reports generation

### On Push
- `test.yml` - Backend tests
- `e2e.yml` - Frontend & E2E tests
- `sonarqube.yml` - Code quality
- `pr-checks.yml` - PR validation

### On Schedule
- `performance.yml` - Load testing
- `codecov-setup.yml` - Coverage validation

## Alert Types

### Critical 🚨
- API Down
- Database Error
- High Error Rate (>5%)
- Security Vulnerability

### Warning ⚠️
- High Latency (>1s)
- Coverage Drop (>5%)
- Memory Leak
- Dependency Issues

### Info ℹ️
- Performance Improvement
- Update Available
- New Test Coverage
- Metric Changes

## Setup Checklist

### Phase 1: Basic Monitoring ✅
- [x] Health checks configured
- [x] Metrics collection enabled
- [x] Dashboard created
- [x] Reports generation

### Phase 2: Coverage Tracking
- [ ] Codecov account setup (5 min)
- [ ] GitHub secrets configured
- [ ] Branch protection rules
- [ ] Dashboard integration

### Phase 3: Code Quality
- [ ] SonarCloud OR self-hosted (10 min)
- [ ] Project configuration
- [ ] Quality gates setup
- [ ] GitHub integration

### Phase 4: Notifications
- [ ] Email alerts (optional)
- [ ] Slack integration (optional)
- [ ] PagerDuty (optional)
- [ ] Custom notifications

## Implementation Status

| Component | Status | Next Step |
|-----------|--------|-----------|
| Health Checks | ✅ Ready | Review dashboards |
| Performance | ✅ Ready | Run benchmarks |
| Coverage | ⏳ Pending | Setup Codecov |
| Code Quality | ⏳ Pending | Setup SonarQube |
| Notifications | ⏳ Pending | Configure alerts |

## Quick Start (15 minutes)

### 1. Review Current Status
```bash
# View monitoring workflows
open https://github.com/chrisquire80/documentale/actions

# View dashboards
cat monitoring/dashboards.md
```

### 2. Setup Codecov (5 min)
```bash
# Follow: docs/CODECOV_QUICKSTART.md
# Takes: 5 minutes
# Result: Coverage tracking in PRs
```

### 3. Setup SonarQube (10 min)
```bash
# Choose:
# Option A: SonarCloud (free, 5 min)
# Option B: Self-hosted (10 min)

# Follow: docs/SONARQUBE_QUICKSTART.md
```

### 4. Configure Notifications (5 min)
```bash
# Optional but recommended
# Setup Slack or email alerts
# See: docs/MONITORING_SETUP.md
```

## Real-Time Monitoring

### Local Development
```bash
# Watch tests
npm test -- --watch

# Watch API health
while true; do curl http://localhost:8000/health; sleep 10; done

# Monitor logs
tail -f backend/logs/app.log
```

### GitHub Actions
```bash
# View workflow runs
https://github.com/chrisquire80/documentale/actions

# View artifacts
Actions > [Workflow] > Artifacts

# Trigger manually
Actions > [Workflow] > Run workflow
```

## Performance Baseline

Establish baseline metrics:

```bash
# Smoke test (quick validation)
./scripts/benchmark.sh http://localhost:8000 smoke

# Load test (normal operations)
./scripts/benchmark.sh http://localhost:8000 load

# Stress test (find breaking point)
./scripts/benchmark.sh http://localhost:8000 stress

# Soak test (long-running stability)
./scripts/benchmark.sh http://localhost:8000 soak
```

Results compared against:
- `performance/baseline.json` - Expected metrics

## Troubleshooting

### Workflow Not Running
1. Check workflow is enabled in GitHub
2. Verify schedule (daily 8 AM UTC)
3. Check for errors in workflow logs
4. Trigger manually from Actions tab

### Alerts Not Sending
1. Verify webhook/email configured
2. Check GitHub secrets set
3. Review workflow logs
4. Test with manual trigger

### Metrics Not Updating
1. Run workflow manually
2. Check artifacts uploaded
3. Verify data format
4. Review logs for errors

## Documentation

| Document | Purpose | Read Time |
|----------|---------|-----------|
| CODECOV_QUICKSTART.md | 5-min Codecov setup | 5 min |
| CODECOV_SETUP.md | Detailed setup guide | 15 min |
| SONARQUBE_QUICKSTART.md | 5-min SonarQube setup | 5 min |
| SONARQUBE_SETUP.md | Detailed setup guide | 20 min |
| PERFORMANCE_TESTING.md | Load testing guide | 20 min |
| MONITORING_SETUP.md | Alerts & notifications | 15 min |

## Support

Need help? Check:
1. Documentation in `docs/`
2. GitHub Actions logs
3. Tool-specific docs
4. GitHub Issues

## Next Steps

1. **Today**: Review current status
2. **This Week**: Setup Codecov + SonarQube
3. **Next Week**: Configure notifications
4. **Ongoing**: Monitor metrics, improve targets

---

**Status**: 🟢 Partially Deployed
**Coverage**: 60% Backend, Pending Frontend
**Performance**: Stable, Baseline Established
**Quality**: Ready for Code Analysis
**Alerts**: Ready for Configuration

Last Updated: 2026-02-28
