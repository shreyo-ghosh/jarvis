#!/usr/bin/env bash
# build_lambda.sh — builds a Lambda-compatible zip from the src tree.
# Lambda expects bot.py and its imports at the archive root.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BUILD_DIR="$ROOT/.lambda_build"
rm -rf "$BUILD_DIR" "$ROOT/lambda_package.zip" "$ROOT/lambda_deps"
mkdir -p "$BUILD_DIR"

if command -v docker >/dev/null 2>&1; then
  echo "🐳 Building Lambda package with Docker (linux/x86_64)..."
  docker run --rm --platform linux/x86_64 \
    -v "$ROOT:/workspace" \
    -w /workspace \
    --entrypoint /bin/bash \
    public.ecr.aws/lambda/python:3.12 \
    -c "
      set -euo pipefail
      python3 -m pip install -r /workspace/requirements.txt -t /workspace/lambda_deps --quiet
      mkdir -p /workspace/.lambda_build
      cp -R /workspace/src/. /workspace/.lambda_build/
      cp -R /workspace/lambda_deps/. /workspace/.lambda_build/
      echo '✅ Dependencies installed'
    "
else
  echo "⚠️ Docker not found; building package locally from source tree..."
  python3 -m pip install -r requirements.txt -t "$BUILD_DIR" --quiet || true
fi

if [[ -d "$ROOT/src" ]]; then
  cp -R "$ROOT/src/." "$BUILD_DIR/"
fi

if [[ -d "$ROOT/lambda_deps" ]]; then
  cp -R "$ROOT/lambda_deps/." "$BUILD_DIR/" 2>/dev/null || true
fi

find "$BUILD_DIR" -type d -name '__pycache__' -prune -exec rm -rf {} + || true

python3 - "$BUILD_DIR" "$ROOT/lambda_package.zip" <<'PY'
import os
import sys
import zipfile

src_dir = sys.argv[1]
zip_path = sys.argv[2]

with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
    for base, dirs, files in os.walk(src_dir):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for file in files:
            if file.endswith('.pyc'):
                continue
            full_path = os.path.join(base, file)
            arcname = os.path.relpath(full_path, src_dir)
            zf.write(full_path, arcname)

    names = set(zf.namelist())
    missing = []
    if 'bot.py' not in names and not any(n.endswith('/bot.py') for n in names):
        missing.append('bot.py')
    if not any('pydantic_core' in n and ('__init__.py' in n or '_pydantic_core' in n) for n in names):
        missing.append('pydantic_core dependency')
    if missing:
        raise SystemExit(f'Missing required Lambda package entries: {missing}')
PY

rm -rf "$BUILD_DIR" "$ROOT/lambda_deps"
SIZE=$(du -sh "$ROOT/lambda_package.zip" | cut -f1)
echo "✅ lambda_package.zip ready — $SIZE"
