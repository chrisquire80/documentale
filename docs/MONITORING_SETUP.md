# Monitoring Setup Guide

Complete guide for setting up monitoring and alerts.

## Overview

Monitoring includes:
- API health checks
- Performance metrics
- Code quality tracking
- Dependency security
- Coverage trends
- Alerts and notifications

## Automated Monitoring ✅

Already Configured:
- `.github/workflows/monitoring-alerts.yml` - Daily checks
- `monitoring/dashboards.md` - Dashboard overview
- `monitoring/metrics/` - Metric storage
- `monitoring/reports/` - Health reports

## Quick Start (5 minutes)

### 1. Enable Monitoring Workflow
```bash
# Workflow runs automatically daily
# Or trigger manually from GitHub Actions
```

### 2. View Dashboard
```bash
# Dashboard: GitHub Actions artifacts
# Location: Actions > Monitoring & Alerts > Artifacts
```

### 3. Set Up Notifications

#### Email Alerts
```bash
# Settings > Secrets and variables > Actions
# Add: ALERT_EMAIL
# Value: your-email@example.com
```

#### Slack Integration
```bash
# Create Slack webhook
# https://api.slack.com/apps

# Settings > Secrets
# Add: SLACK_WEBHOOK
# Value: https://hooks.slack.com/services/...

# Enable in monitoring-alerts.yml
```

## Key Metrics

### API Performance
```
P50 Latency: < 300ms
P95 Latency: < 500ms ✅
P99 Latency: < 1000ms ✅
Error Rate: < 1% ✅
Throughput: > 100 RPS ✅
```

### Code Quality
```
Code Smells: 0
Security Issues: 0
Duplications: < 3%
Maintainability: A
```

### Coverage
```
Backend: 60-70%
Frontend: 65-75%
```

## Monitoring Points

### Health Checks
- API endpoints responding
- Database connected
- Cache working
- Services healthy

### Performance
- Response times (P50, P95, P99)
- Throughput (RPS)
- Error rates
- Resource usage

### Quality
- Test coverage
- Code smells
- Security issues
- Dependencies

### Trends
- Coverage history
- Performance changes
- Error rate trends
- Dependency updates

## Setting Up External Tools

### Slack Notifications

1. **Create Slack App**
   - Go to https://api.slack.com/apps
   - Click "Create New App"
   - Choose "From scratch"
   - Name: "Documentale Alerts"
   - Workspace: Your workspace

2. **Create Webhook**
   - Go to "Incoming Webhooks"
   - Click "Add New Webhook to Workspace"
   - Select channel: #alerts
   - Copy webhook URL

3. **Add to GitHub**
   - Settings > Secrets and variables > Actions
   - New secret: `SLACK_WEBHOOK`
   - Value: [paste webhook URL]

4. **Enable in Workflow**
   - Uncomment Slack step in monitoring-alerts.yml
   - Test by pushing changes

### Email Alerts

1. **Gmail Setup** (recommended)
   - Enable 2-factor authentication
   - Create App Password
   - Save password

2. **Add to GitHub**
   - Settings > Secrets
   - New secret: `EMAIL_PASSWORD`
   - Value: [app password]

3. **Configure Recipient**
   - Settings > Secrets
   - New secret: `ALERT_EMAIL`
   - Value: your-email@example.com

### PagerDuty Integration

1. **Create PagerDuty Account**
   - https://www.pagerduty.com

2. **Create Integration**
   - Services > New Service
   - Name: "Documentale"
   - Create integration key

3. **Add to GitHub**
   - Settings > Secrets
   - New secret: `PAGERDUTY_KEY`
   - Value: [integration key]

## Monitoring Dashboards

### GitHub Actions Dashboard
- Location: Actions tab
- View: Monitoring & Alerts workflow
- Artifacts: Daily reports

### Codecov Dashboard
- URL: https://codecov.io/gh/chrisquire80/documentale
- Metrics: Coverage trends
- Alerts: Coverage drops

### SonarQube Dashboard
- URL: http://localhost:9000 (self-hosted)
- Metrics: Code quality
- Alerts: Quality gate failures

## Alert Thresholds

### Critical (Page On-Call)
```
- API Down (response timeout)
- Database Error
- Error Rate > 5%
- Memory Leak Detected
```

### Warning (Email)
```
- P95 Latency > 1000ms
- Coverage Drop > 5%
- Security Issue Found
- Dependency Vulnerability
```

### Info (Log Only)
```
- Performance Improvement
- New Vulnerability (patched)
- Dependency Update Available
```

## Customization

### Add Custom Metrics

1. Edit `monitoring/metrics/` directory
2. Create JSON file:
   ```json
   {
     "name": "metric_name",
     "value": 123,
     "threshold": 100,
     "status": "ok"
   }
   ```

3. Add check in monitoring-alerts.yml

### Create Custom Dashboards

Create dashboard markdown files:
```bash
monitoring/dashboards/
├── performance.md
├── coverage.md
├── security.md
└── custom.md
```

### Extend Notifications

Add custom notification channels:
```yaml
- name: Custom Notification
  if: failure()
  run: |
    # Custom notification logic
    curl -X POST https://your-service/webhook
```

## Troubleshooting

### "Notifications not received"

1. Verify webhook URL is correct
2. Check GitHub secrets are set
3. Verify channel/email exists
4. Check workflow logs

### "Metrics not updating"

1. Verify workflow is enabled
2. Check schedule (daily at 8 AM UTC)
3. View workflow runs in Actions tab
4. Check artifacts are uploaded

### "False alarms"

1. Adjust thresholds in baseline.json
2. Update alert conditions
3. Test thresholds locally first

## Best Practices

1. **Set Realistic Thresholds**
   - Based on historical data
   - Gradual improvements
   - Not too strict initially

2. **Monitor Trends**
   - Track over time
   - Identify patterns
   - Prevent regressions

3. **Act on Alerts**
   - Investigate immediately
   - Document findings
   - Fix root causes

4. **Regular Review**
   - Weekly: Check metrics
   - Monthly: Update baselines
   - Quarterly: Review alerts

5. **Communicate**
   - Share dashboards
   - Discuss alerts in team
   - Plan improvements

## References

- [GitHub Actions](https://docs.github.com/en/actions)
- [Slack API](https://api.slack.com/)
- [PagerDuty API](https://developer.pagerduty.com/)
- [Codecov](https://docs.codecov.io/)
- [SonarQube](https://docs.sonarqube.org/)

## Support

For setup help:
1. Check docs/ directory
2. Review GitHub Actions logs
3. Check tool documentation
4. Create GitHub issue

---

⏱️ **Setup Time**: 5-15 minutes
✅ **Status**: Ready
🔔 **Alerts**: Configured
📊 **Dashboard**: Available
