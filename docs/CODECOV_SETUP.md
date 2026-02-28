# Codecov Integration Setup

This guide explains how to set up Codecov for code coverage tracking in this repository.

## Prerequisites

- GitHub repository with Actions enabled
- Codecov account (free tier available)

## Setup Steps

### 1. Create Codecov Account

1. Go to https://codecov.io
2. Sign up with GitHub
3. Authorize Codecov to access your repositories

### 2. Activate Repository

1. Log in to Codecov dashboard
2. Select the `documentale` repository
3. Enable code coverage tracking

### 3. Add Repository Token (Optional)

For private repositories, you may need a repository token:

1. In Codecov dashboard, go to repository settings
2. Copy the repository token
3. Add to GitHub repository secrets:
   - Go to Settings > Secrets and variables > Actions
   - Click "New repository secret"
   - Name: `CODECOV_TOKEN`
   - Value: [paste token from Codecov]

### 4. Update GitHub Workflows

The workflows are already configured with Codecov integration:

```yaml
- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v3
  with:
    files: ./backend/coverage.xml
    flags: backend
    fail_ci_if_error: false
```

### 5. Configure Coverage Requirements

Edit `.codecov.yml` to set coverage targets:

```yaml
coverage:
  status:
    project:
      default:
        target: 60%
        threshold: 5%
```

### 6. Add Branch Protection Rules

In GitHub repository settings:

1. Go to Settings > Branches
2. Add rule for `main` branch
3. Require status checks:
   - `Codecov/project/backend`
   - `Codecov/project/frontend`

### 7. View Coverage Reports

- **Dashboard**: https://codecov.io/gh/chrisquire80/documentale
- **Pull Requests**: Coverage comments auto-posted on PRs
- **Badges**: Add to README.md:

```markdown
[![codecov](https://codecov.io/gh/chrisquire80/documentale/branch/main/graph/badge.svg?token=YOUR_TOKEN)](https://codecov.io/gh/chrisquire80/documentale)
```

## Coverage Thresholds

### Current Targets

| Component | Target | Threshold |
|-----------|--------|-----------|
| Backend Project | 60% | ±5% |
| Backend Patch | 70% | ±2% |
| Frontend Project | 65% | ±5% |
| Frontend Patch | 75% | ±3% |

### Adjusting Thresholds

Edit `.codecov.yml`:

```yaml
flags:
  backend:
    statuses:
      - type: project
        target: 65%  # Increase target
        threshold: 3%  # Stricter threshold
```

## Troubleshooting

### Coverage Not Showing in PRs

1. Verify token is set (if private repo)
2. Check that coverage files are generated in CI
3. Verify `codecov-action` step is not skipped

### Low Coverage Report

1. Check if all test files are included:
   ```bash
   python -m pytest tests/ --cov=app --cov-report=xml
   ```

2. Verify coverage paths in `.codecov.yml`:
   ```yaml
   flags:
     backend:
       paths:
         - backend/app/
   ```

### Build Failing Due to Coverage

Check if coverage threshold is too strict:

```yaml
threshold: 5%  # Allow 5% drop from base
```

## Best Practices

1. **Review Coverage Trends**: Check codecov.io dashboard regularly
2. **Set Realistic Targets**: Don't require 100% coverage
3. **Monitor Patch Coverage**: Ensure new code maintains coverage
4. **Use Flags**: Separate backend and frontend metrics
5. **Allow Specific Files**: Exclude migrations, generated code:
   ```yaml
   ignore:
     - "**/migrations/**"
     - "**/generated/**"
   ```

## Integration with CI/CD

The workflow automatically:
- Runs tests with coverage collection
- Uploads reports to Codecov
- Posts coverage comments on PRs
- Updates badges
- Enforces coverage requirements

## References

- [Codecov Docs](https://docs.codecov.io)
- [codecov-action GitHub](https://github.com/codecov/codecov-action)
- [Coverage Configuration](https://docs.codecov.io/docs/codecovyml-reference)
