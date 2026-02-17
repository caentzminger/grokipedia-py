uv_run_dev := "uv run --dev"

# Setup for devs
setup:
    uv sync --all-extras --all-groups --upgrade

# Format python using `ruff`...
fmt-py:
    echo "Formating python using `ruff`..."
    @{{ uv_run_dev }} ruff format src/ tests/

# Format markdown using `mdformat`...
fmt-md:
    echo "Formating markdown using `mdformat`..."
    @{{ uv_run_dev }} mdformat README.md

fmt-all: fmt-py fmt-md

# Typecheck python using `ty`...
typecheck:
    @{{ uv_run_dev }} ty check src/ tests/

# Run tests using `pytest`...
test:
    @{{ uv_run_dev }} pytest tests/
