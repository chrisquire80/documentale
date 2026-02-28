# SonarQube Quick Start Guide

Choose between **SonarCloud** (recommended for open source) or **Self-Hosted**.

## Option A: SonarCloud (5 minutes) ⭐ RECOMMENDED

### Step 1: Create SonarCloud Account
```bash
# Go to https://sonarcloud.io
# Click "Sign up with GitHub"
# Authorize access
# Select "documentale" repository
```

### Step 2: Generate Token
1. Log in to SonarCloud
2. Click **Profile** → **Security**
3. Generate token (e.g., "CI Token")
4. Copy token

### Step 3: Add GitHub Secrets
```bash
# Settings → Secrets and variables → Actions
# New secret: SONAR_TOKEN_CLOUD
# Value: [paste token from step 2]
```

### Step 4: Test Integration
```bash
# Push code or create PR
# GitHub Actions runs sonarqube.yml workflow
# Check PR comments for quality analysis
```

### View Results
- **Dashboard**: https://sonarcloud.io/projects
- **PR Comments**: Auto-posted by SonarCloud
- **Metrics**: Real-time analysis

## Option B: Self-Hosted (10 minutes)

### Step 1: Start SonarQube Server
```bash
# Option 1: Docker (easiest)
chmod +x scripts/setup-sonarqube.sh
./scripts/setup-sonarqube.sh

# Option 2: Docker Compose manual
docker-compose -f docker-compose.sonarqube.yml up -d

# Option 3: Traditional installation
# Download from https://www.sonarsource.com/products/sonarqube/downloads/
# Follow installation guide
```

### Step 2: Access SonarQube
- **URL**: http://localhost:9000
- **Username**: admin
- **Password**: admin_password

### Step 3: Generate Token
1. Login to http://localhost:9000
2. Click **My Account** → **Security**
3. Generate token
4. Copy token

### Step 4: Add GitHub Secrets
```bash
# Settings → Secrets and variables → Actions
# New secret: SONAR_TOKEN
# Value: [paste token]

# New secret: SONAR_HOST_URL
# Value: http://localhost:9000 (or your server)
```

### Step 5: Test Analysis
```bash
# Local test
cd backend
python -m pytest tests/ --cov=app --cov-report=xml
sonar-scanner -Dsonar.projectKey=documentale

# Or push code to trigger GitHub Actions
```

## Configuration Already Done ✅

```
✅ sonar-project.properties - Project configuration
✅ .github/workflows/sonarqube.yml - Analysis workflow
✅ Coverage collection - Running in CI/CD
✅ Metrics defined - Quality gates ready
```

## What Happens Next

### With SonarCloud
1. Analysis runs on each push
2. Results appear in PR comments
3. Dashboard updated in real-time
4. Historical trends tracked

### With Self-Hosted
1. Start SonarQube server
2. Run analysis (local or CI/CD)
3. Results appear in web UI
4. Quality gates enforced

## Coverage Targets

```
Backend:
  - Project: 60% (±5%)
  - Patch: 70% (±2%)

Frontend:
  - Project: 65% (±5%)
  - Patch: 75% (±3%)
```

## Quality Gates

```
Code Smells: 0 (blocker)
Security Issues: 0
Duplicates: < 3%
Maintainability: A
```

## Common Commands

### SonarQube Server
```bash
# Start
docker-compose -f docker-compose.sonarqube.yml up -d

# Stop
docker-compose -f docker-compose.sonarqube.yml down

# Logs
docker-compose -f docker-compose.sonarqube.yml logs -f sonarqube

# Remove data
docker-compose -f docker-compose.sonarqube.yml down -v
```

### SonarQube Analysis
```bash
# Install scanner
brew install sonar-scanner

# Run analysis
sonar-scanner \
  -Dsonar.projectKey=documentale \
  -Dsonar.sources=backend/app,frontend/src \
  -Dsonar.login=$SONAR_TOKEN
```

## Troubleshooting

### "SonarQube not starting"
```bash
# Check logs
docker-compose -f docker-compose.sonarqube.yml logs sonarqube

# Check ports
netstat -an | grep 9000

# Wait 1-2 minutes, try again
```

### "Analysis not showing up"
1. Verify sonar-project.properties exists
2. Check SONAR_TOKEN is set
3. Verify project key matches
4. Check sonarqube.yml workflow runs

### "Low quality score"
1. Review issues in SonarQube UI
2. Fix code or increase thresholds
3. Re-run analysis
4. Update quality gates

## Next Steps

- [ ] Choose platform (SonarCloud or Self-Hosted)
- [ ] Complete setup
- [ ] Generate token
- [ ] Add GitHub secrets
- [ ] Test with first analysis
- [ ] Configure notifications
- [ ] Review quality gates

## Reference

| Platform | URL | Setup Time |
|----------|-----|-----------|
| SonarCloud | https://sonarcloud.io | 5 min ⭐ |
| Self-Hosted | http://localhost:9000 | 10 min |

## Documentation

- **Full Setup**: [SONARQUBE_SETUP.md](SONARQUBE_SETUP.md)
- **SonarCloud Docs**: https://docs.sonarcloud.io
- **SonarQube Docs**: https://docs.sonarqube.org

---

⏱️ **Setup Time**: 5-10 minutes
🔧 **Already Configured**: Yes
✅ **Ready to Deploy**: Yes
