uv_run_dev := "uv run --dev"

# Setup for devs
setup:
    uv sync --all-extras --all-groups --locked

# Upgrade project deps
uprade:
    uv sync --all-extras --all-groups --upgrade

# Format python using `ruff`
fmt-py:
    @echo "Formating python using ruff..."
    @{{ uv_run_dev }} ruff format src/ tests/

# Format markdown using `mdformat`
fmt-md:
    @echo "Formating markdown using mdformat..."
    @{{ uv_run_dev }} mdformat README.md AGENTS.md

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
