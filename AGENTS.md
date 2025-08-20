# AGENTS.md

## Setup commands
- Install deps: `uv sync --dev`
- Build package: `uv build`
- Run tests: `pytest`
- Type check code: `pyright`
- Format code: `ruff format`
- Lint code: `ruff check`
- Install git hooks: `pre-commit install`
- Compile protobufs: `bash scripts/compile_proto.sh` (run from root)

## Code style
- Use Python type hints throughout
- Follow Black formatting (via ruff)
- Async/await for I/O operations
- Document public APIs with docstrings
- Use functional patterns where possible
- Implement proper error handling

## Testing instructions
- Tests live in the `tests/` directory
- Run `pytest` for full test suite
- Run `pytest path/to/test.py` for specific tests
- Run `pytest -k "test_name"` to run by pattern
- Run `pytest --cov=src/athena_client` for coverage
- Add tests for all new code
- Mock external services in tests
- Test both success and error cases

## PR instructions
- Title format: [component] Description
- Run `ruff check`, `pyright`, and `pytest` before committing
- Keep PRs focused on a single change
- Add tests for new functionality
- Update documentation for API changes
- Add proper type hints

## Dev tips
- Use `uv` package manager instead of pip
- Don't use `uv pip` commands, just the base `uv` commands
- Run formatters before committing
- Check generated code in `src/athena_client/generated/`
- Add error handling at each pipeline stage
- Use correlation IDs for request tracing

## Documentation
- Docs are in `docs/`
- Build docs by `cd docs && make clean && make html`
