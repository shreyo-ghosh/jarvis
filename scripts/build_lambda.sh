#!/usr/bin/env bash
# build_lambda.sh — builds a Lambda-compatible zip using Docker
# Ensures native binaries (aiohttp, cryptography etc) compile for Linux x86_64
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "🐳 Building Lambda package with Docker (linux/x86_64)..."

# Use AWS Lambda Python 3.12 base image for correct ABI
docker run --rm --platform linux/x86_64 \
  -v "$ROOT:/workspace" \
  -w /workspace \
  public.ecr.aws/lambda/python:3.12 \
  bash -c "
    pip install -r requirements.txt -t /workspace/lambda_deps/ --quiet
    echo '✅ Dependencies installed'
  "

echo "📁 Assembling zip..."
rm -f lambda_package.zip

# Add src/ files (our code)
cd src
zip -r ../lambda_package.zip . -x "__pycache__/*" "*.pyc" "tests/*" 2>/dev/null
cd ..

# Add dependencies
cd lambda_deps
zip -r ../lambda_package.zip . -x "__pycache__/*" "*.pyc" "*.dist-info/*" 2>/dev/null
cd ..

# Cleanup
rm -rf lambda_deps/

SIZE=$(du -sh lambda_package.zip | cut -f1)
echo "✅ lambda_package.zip ready — $SIZE"
