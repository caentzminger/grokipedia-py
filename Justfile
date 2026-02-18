uv_run_dev := "uv run --dev"

# Setup for devs
setup:
    uv sync --all-extras --all-groups --locked

# Upgrade project deps
upgrade:
    uv sync --all-extras --all-groups --upgrade

# Format python using `ruff`
fmt-py:
    @echo "Formatting python using ruff..."
    @{{ uv_run_dev }} ruff format src/ tests/

# Format markdown using `mdformat`
fmt-md:
    @echo "Formatting markdown using mdformat..."
    @{{ uv_run_dev }} mdformat README.md AGENTS.md CHANGELOG.md

# Formats python and markdown files
fmt-all: fmt-py fmt-md

# Typecheck python using `ty`
typecheck:
    @echo "Typechecking python using ty..."
    @{{ uv_run_dev }} ty check src/ tests/

# Lint python using `ruff`
lint-py:
    @echo "Linting python using ruff..."
    @{{ uv_run_dev }} ruff check src/ tests/

# Lint-fix python using `ruff`
lint-fix-py:
    @echo "Lint-fixing python using ruff..."
    @{{ uv_run_dev }} ruff check src/ tests/ --fix

# Run tests using `pytest`
test:
    @{{ uv_run_dev }} pytest tests/

# Run local quality checks quickly.
check: fmt-py lint-py typecheck test

# Build distribution artifacts.
build:
    uv build

# Remove local build/test artifacts.
clean:
    rm -rf .pytest_cache .ruff_cache build dist *.egg-info

# Mirror CI checks exactly.
ci:
    uv sync --all-extras --all-groups --locked
    @{{ uv_run_dev }} ruff format --check src/ tests/
    @{{ uv_run_dev }} ruff check src/ tests/
    @{{ uv_run_dev }} ty check src/ tests/
    @{{ uv_run_dev }} pytest tests/
