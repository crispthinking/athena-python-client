#!/bin/bash

# Define paths
PROTO_DIR="proto"
OUT_DIR="src/athena_client/generated"

# Ensure output directory exists
mkdir -p "$OUT_DIR"

# Compile .proto files
python -m grpc_tools.protoc \
  --proto_path="$PROTO_DIR" \
  --python_out="$OUT_DIR" \
  --grpc_python_out="$OUT_DIR" \
  --mypy_out="$OUT_DIR" \
  "$PROTO_DIR/athena/athena.proto"

echo "Compilation complete. Files generated in $OUT_DIR"
