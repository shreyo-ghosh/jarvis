#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
echo "Building Lambda deployment package..."
rm -rf build
mkdir -p build/package
docker run --rm \
  -v "$(pwd)":/var/task \
  -w /var/task \
  public.ecr.aws/sam/build-python3.12 \
  pip install -r requirements.txt -t build/package
cp -r src/* build/package/
if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN=python
else
  echo "Python is required to build the Lambda zip package."
  exit 127
fi
"$PYTHON_BIN" - <<'PY'
import os
import zipfile

base_dir = os.path.join(os.getcwd(), 'build', 'package')
zip_path = os.path.join(os.getcwd(), 'build', 'lambda.zip')

with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for file in files:
            if file.endswith('.pyc'):
                continue
            full_path = os.path.join(root, file)
            arcname = os.path.relpath(full_path, base_dir)
            zf.write(full_path, arcname)
PY

echo "Lambda package built at build/lambda.zip"
