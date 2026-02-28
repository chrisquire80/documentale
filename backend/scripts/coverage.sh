#!/bin/bash
# Generate test coverage report

echo "🔍 Generating test coverage report..."
python -m pytest tests/ \
  --cov=app \
  --cov-report=term-missing \
  --cov-report=html \
  --cov-report=xml \
  -q

echo ""
echo "✅ Coverage report generated!"
echo "📊 HTML report: htmlcov/index.html"
echo "📄 XML report: coverage.xml (for CI/CD)"
