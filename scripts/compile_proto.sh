#!/bin/bash

# Define paths
PROTO_DIR="athena-protobufs"
OUT_DIR="src/resolver_athena_client/generated"

# Ensure output directory exists
mkdir -p "$OUT_DIR"

# Compile .proto files
if [ ! -f "$PROTO_DIR/athena/athena.proto" ]; then
  echo "Error: Protobuf file not found at $PROTO_DIR/athena/athena.proto. Ensure the submodule is initialized and updated."
  exit 1
fi

python -m grpc_tools.protoc \
  --proto_path="$PROTO_DIR" \
  --proto_path="$(python -c "import grpc_tools; print(grpc_tools.__path__[0])")" \
  --python_out="$OUT_DIR" \
  --grpc_python_out="$OUT_DIR" \
  --mypy_out="$OUT_DIR" \
  "$PROTO_DIR/athena/athena.proto"

# Fix imports in generated files
if [[ "$OSTYPE" == "darwin"* ]]; then
  sed -i '' -e 's/^from athena /from resolver_athena_client.generated.athena /' "$OUT_DIR/athena/athena_pb2_grpc.py"
  sed -i '' -e 's/^from athena /from resolver_athena_client.generated.athena /' "$OUT_DIR/athena/athena_pb2.py"
else
  sed -i -e 's/^from athena /from resolver_athena_client.generated.athena /' "$OUT_DIR/athena/athena_pb2_grpc.py"
  sed -i -e 's/^from athena /from resolver_athena_client.generated.athena /' "$OUT_DIR/athena/athena_pb2.py"
fi

if [ ! -f "$OUT_DIR/athena/athena_pb2.py" ] || [ ! -f "$OUT_DIR/athena/athena_pb2_grpc.py" ]; then
  echo "Error: Protobuf files were not generated successfully in $OUT_DIR."
  exit 1
fi

echo "Compilation complete. Files generated in $OUT_DIR"
