# Athena Client Library

This is a Python library for interacting with the Athena API (Resolver Unknown
CSAM Detection).

## TODO

### Async pipelines
Make pipeline style invocation of the async interators such that we can

async read file -> async transform -> async classify -> async results

### Generate correlation IDs based on <something>
Make do this with strategy pattern?


## Development
This package uses [uv](https://docs.astral.sh/uv/) to manage its packages.

To install dependencies, run:

```bash
uv sync --dev
```

To build the package, run:

```bash
uv build
```

To run the tests, run:

```bash
pytest
```

To lint and format the code, run:

```bash
ruff check
ruff format
```

There are pre-commit hooks that will lint, format, and type check the code.
Install them with:

```bash
pre-commit install
```

To re-compile the protobuf files, run from the repository's root directory:

```bash
bash scripts/compile_proto.sh
```
