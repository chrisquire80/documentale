# Codecov Quick Start Guide

This is a quick setup guide for Codecov integration. For detailed information, see [CODECOV_SETUP.md](CODECOV_SETUP.md).

## 5-Minute Setup

### Step 1: Create Codecov Account (2 min)

1. Go to **https://codecov.io**
2. Click **"Sign up with GitHub"**
3. Authorize Codecov to access your repositories
4. Select **documentale** repository

### Step 2: Configure GitHub Secrets (1 min)

**Only needed for private repositories:**

1. In Codecov dashboard, go to repository settings
2. Copy the repository token
3. In GitHub:
   - Settings → Secrets and variables → Actions
   - Click **"New repository secret"**
   - Name: `CODECOV_TOKEN`
   - Value: [paste token]

### Step 3: Set Up Branch Protection (1 min)

1. GitHub → Settings → Branches
2. Click **"Add branch protection rule"**
3. Branch name pattern: `main`
4. Check: **"Require status checks"**
5. Add required checks:
   - `Codecov/project/backend`
   - `Codecov/project/frontend`

### Step 4: Verify Setup (1 min)

1. Push a test commit or create a PR
2. Check that Codecov comments appear
3. View dashboard at **https://codecov.io/gh/chrisquire80/documentale**

## Configuration Already Done ✅

```
✅ .codecov.yml - Coverage targets configured
✅ GitHub Actions - Workflows ready
✅ Coverage collection - Running in CI/CD
✅ Integration - Ready for Codecov connection
```

## What Happens Next

1. **Coverage Reports**: Auto-uploaded with each test run
2. **PR Comments**: Codecov posts coverage changes
3. **Dashboard**: View trends at codecov.io
4. **Alerts**: Get notified of coverage drops
5. **Badges**: Use in README for visibility

## Coverage Targets

| Component | Target | Patch |
|-----------|--------|-------|
| Backend | 60% | 70% |
| Frontend | 65% | 75% |

## Current Status

```
Backend Coverage: 61% ✅ (Above target)
Frontend Coverage: Pending first measurements
```

## Common Issues

### "Codecov doesn't show up in PR"

1. Check token is set (if private repo)
2. Verify GitHub Actions runs successfully
3. Check coverage.xml is generated
4. Wait 5 minutes for processing

### "Coverage threshold failing"

1. Run tests locally: `pytest tests/ --cov=app`
2. Check coverage percentage
3. Update code or increase target
4. Review `.codecov.yml` configuration

### "Can't find token in Codecov"

1. Log in to codecov.io
2. Select repository
3. Go to Settings (gear icon)
4. Copy token from "Upload token"

## Next Steps

- [ ] Create Codecov account
- [ ] Add repository token (if needed)
- [ ] Set up branch protection
- [ ] Test with a sample PR
- [ ] Configure Slack/email notifications
- [ ] Add badge to README

## Reference

- **Codecov Dashboard**: https://codecov.io/gh/chrisquire80/documentale
- **Codecov Docs**: https://docs.codecov.io
- **Full Setup Guide**: [CODECOV_SETUP.md](CODECOV_SETUP.md)

---

⏱️ **Total Setup Time**: ~5 minutes
🔧 **No Code Changes Required**
✅ **Fully Automated After Setup**
