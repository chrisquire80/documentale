# SonarQube Setup Guide

This guide explains how to set up SonarQube for code quality analysis.

## Options

Choose one of the following based on your needs:

### Option 1: SonarCloud (Recommended for Open Source)

**Pros:**
- Free for public projects
- No server to maintain
- GitHub integration built-in
- Real-time analysis on PRs

**Setup:**

1. **Create SonarCloud Account**
   - Go to https://sonarcloud.io
   - Sign up with GitHub
   - Authorize access

2. **Import Repository**
   - In SonarCloud dashboard
   - Click "Import project"
   - Select `documentale`
   - Configure quality gates

3. **Add GitHub Secrets**
   - Go to GitHub repo Settings > Secrets
   - Add `SONAR_TOKEN_CLOUD`:
     - Get from SonarCloud > My Account > Security

4. **Workflow Integration**
   - Already configured in `.github/workflows/sonarqube.yml`
   - Runs on push and pull requests

5. **View Results**
   - Dashboard: https://sonarcloud.io/project/overview?id=chrisquire80_documentale
   - PR Comments: Auto-posted on each PR

### Option 2: Self-Hosted SonarQube Server

**Pros:**
- Full control
- Private analysis
- Custom quality gates
- Advanced features

**Setup:**

1. **Install SonarQube Server**

   Using Docker:
   ```bash
   docker run -d --name sonarqube \
     -p 9000:9000 \
     -e SONAR_JDBC_URL=jdbc:postgresql://db:5432/sonar \
     -e SONAR_JDBC_USERNAME=sonar \
     -e SONAR_JDBC_PASSWORD=sonar \
     sonarqube:latest
   ```

   Or traditional installation:
   - Download from https://www.sonarsource.com/products/sonarqube/downloads/
   - Install Java
   - Configure database
   - Start service

2. **Generate Token**
   - Access http://localhost:9000 (admin/admin)
   - Go to My Account > Security
   - Generate token
   - Copy token

3. **Configure Repository**
   - Create project in SonarQube
   - Note project key
   - Set up quality gates

4. **Add GitHub Secrets**
   - `SONAR_TOKEN`: Token from step 2
   - `SONAR_HOST_URL`: http://your-server:9000

5. **Run Analysis**
   ```bash
   ./scripts/sonar-scan.sh
   ```

## Local Analysis

### Install Scanner

```bash
# macOS
brew install sonar-scanner

# Ubuntu
sudo apt-get install sonar-scanner

# Or download from https://docs.sonarqube.org/latest/analysis/scan/sonarscanner/
```

### Run Analysis Locally

```bash
# Backend only
cd backend
python -m pytest tests/ --cov=app --cov-report=xml
sonar-scanner -Dsonar.projectKey=documentale-backend

# Frontend only
cd frontend
npm run test:coverage
sonar-scanner -Dsonar.projectKey=documentale-frontend
```

## Configuration

### Quality Gates

Quality gates define the criteria for "passed" code:

```yaml
# Edit in SonarQube UI or via API
Rules:
- Coverage: >= 60%
- Code Smells: 0 (blocker)
- Security Issues: 0
- Duplicates: < 3%
- Maintainability: A
```

### Custom Rules

Create custom rules for your project:

1. Go to Quality Profiles
2. Create new profile
3. Add/modify rules
4. Assign to project

### Exclusions

Files to exclude from analysis (in sonar-project.properties):

```properties
sonar.exclusions=\
    **/migrations/**,\
    **/tests/**,\
    **/dist/**,\
    **/node_modules/**
```

## CI/CD Integration

### GitHub Actions

The workflow runs on:
- Push to main and claude/* branches
- Pull requests to main

Commands executed:
1. Checkout code
2. Set up Python/Node
3. Run tests with coverage
4. Execute SonarQube scan
5. Check quality gate

### Manual Trigger

Force analysis:
```bash
git push origin main
# Workflow runs automatically
```

## Monitoring

### Dashboard Metrics

- **Code Coverage**: Current and trend
- **Code Smells**: Technical debt
- **Security Hotspots**: Vulnerabilities
- **Duplications**: Code reuse
- **Complexity**: Cyclomatic complexity
- **Maintainability**: Overall rating

### Reports

- **Executive**: Overview for management
- **Detailed**: Component analysis
- **Time Machine**: Historical trends
- **Custom**: Create custom reports

### Notifications

Set up email notifications:
1. My Account > Notifications
2. Enable for Quality Gate Failures
3. Get notified on violations

## Best Practices

1. **Regular Analysis**: Run after each commit
2. **Review Issues**: Check dashboard weekly
3. **Fix High Priority**: Address blockers immediately
4. **Track Trends**: Monitor coverage over time
5. **Set Realistic Gates**: Gradually improve targets

## Troubleshooting

### No Coverage Data

- Ensure `coverage.xml` is generated
- Check coverage path in configuration
- Verify file exists: `ls coverage.xml`

### Quality Gate Failing

- Run analysis locally:
  ```bash
  sonar-scanner -Dsonar.login=YOUR_TOKEN
  ```
- Review violations in dashboard
- Update code to fix issues

### Connection Issues

- Verify server is running
- Check token validity
- Ensure firewall allows access
- Verify URL configuration

## References

- [SonarQube Docs](https://docs.sonarqube.org)
- [SonarCloud Docs](https://docs.sonarcloud.io)
- [Quality Gates](https://docs.sonarqube.org/latest/user-guide/quality-gates/)
- [Analysis Parameters](https://docs.sonarqube.org/latest/analysis/analysis-parameters/)
