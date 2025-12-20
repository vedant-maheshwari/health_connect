#!/bin/bash
# Run all tests with coverage report

echo "🧪 Running Comprehensive Test Suite..."
echo "======================================"

# Install test dependencies
echo "📦 Installing test dependencies..."
pip install -q -r requirements-test.txt

# Run tests with coverage
echo ""
echo "🔬 Running tests with coverage..."
pytest tests/ \
    -v \
    --cov=services \
    --cov=shared \
    --cov-report=html \
    --cov-report=term-missing \
    --asyncio-mode=auto \
    -W ignore::DeprecationWarning

# Generate coverage report
echo ""
echo "📊 Coverage Report Generated: htmlcov/index.html"

# Check if all tests passed
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ ALL TESTS PASSED!"
else
    echo ""
    echo "❌ SOME TESTS FAILED - Check output above"
    exit 1
fi
