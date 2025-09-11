#!/bin/bash

# Define paths
PROTO_DIR="athena-protobufs"
OUT_DIR="src/resolver_athena_client/generated"

# Ensure output directory exists
mkdir -p "$OUT_DIR"

# Create __init__.py files for Python packages
touch "$OUT_DIR/__init__.py"
mkdir -p "$OUT_DIR/athena"
touch "$OUT_DIR/athena/__init__.py"

# Compile .proto files
if [ ! -d "$PROTO_DIR/athena" ]; then
  echo "Error: Athena protobuf directory not found at $PROTO_DIR/athena. Ensure the submodule is initialized and updated."
  exit 1
fi

# Find all .proto files in the athena directory
PROTO_FILES=$(find "$PROTO_DIR/athena" -name "*.proto")
if [ -z "$PROTO_FILES" ]; then
  echo "Error: No .proto files found in $PROTO_DIR/athena."
  exit 1
fi

echo "Found proto files: $PROTO_FILES"

uv run python -m grpc_tools.protoc \
  --proto_path="$PROTO_DIR" \
  --python_out="$OUT_DIR" \
  --grpc_python_out="$OUT_DIR" \
  --mypy_out="$OUT_DIR" \
  $PROTO_FILES

# Fix imports in generated files
GENERATED_FILES=$(find "$OUT_DIR/athena" -name "*_pb2*.py" 2>/dev/null)
if [ -n "$GENERATED_FILES" ]; then
  for file in $GENERATED_FILES; do
    echo "Fixing imports in $file"
    if [[ "$OSTYPE" == "darwin"* ]]; then
      sed -i '' -e 's/^from athena /from resolver_athena_client.generated.athena /' "$file"
    else
      sed -i -e 's/^from athena /from resolver_athena_client.generated.athena /' "$file"
    fi
  done
else
  echo "Warning: No generated Python files found to fix imports."
fi

# Verify at least some files were generated
if [ ! -d "$OUT_DIR/athena" ] || [ -z "$(find "$OUT_DIR/athena" -name "*_pb2*.py" 2>/dev/null)" ]; then
  echo "Error: Protobuf files were not generated successfully in $OUT_DIR."
  exit 1
fi

echo "Compilation complete. Files generated in $OUT_DIR"
