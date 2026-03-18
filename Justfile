uv_run_dev := "uv run --dev"
uv_run_matrix := "uv run --isolated --with-editable . --group dev"
python_matrix := "3.10 3.11 3.12 3.13 3.14"

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

# Typecheck python using `ty` for a specific Python version.
typecheck-py py="3.14":
    @echo "Typechecking python using ty on Python {{ py }}..."
    @{{ uv_run_matrix }} --python {{ py }} -- ty check src/ tests/

# Typecheck python using `ty` across the supported Python matrix.
typecheck-matrix:
    @for py in {{ python_matrix }}; do \
        just typecheck-py "$py" || exit $?; \
    done

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

# Run tests using `pytest` for a specific Python version.
test-py py="3.14":
    @echo "Running pytest on Python {{ py }}..."
    @{{ uv_run_matrix }} --python {{ py }} -- python -m pytest tests/

# Run tests across the supported Python matrix.
test-matrix:
    @for py in {{ python_matrix }}; do \
        just test-py "$py" || exit $?; \
    done

# Run local quality checks quickly.
check: fmt-py lint-py typecheck test

# Run local quality checks for a specific Python version.
check-py py="3.14":
    @echo "Running checks on Python {{ py }}..."
    @{{ uv_run_matrix }} --python {{ py }} -- ruff format --check src/ tests/
    @{{ uv_run_matrix }} --python {{ py }} -- ruff check src/ tests/
    @{{ uv_run_matrix }} --python {{ py }} -- ty check src/ tests/
    @{{ uv_run_matrix }} --python {{ py }} -- python -m pytest tests/

# Run local quality checks across the supported Python matrix.
check-matrix:
    @for py in {{ python_matrix }}; do \
        just check-py "$py" || exit $?; \
    done

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
