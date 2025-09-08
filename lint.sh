#!/bin/bash
# Run all linting and type checking tools for SISmanager

set -e


MODE=${1:-fix}

if [ "$MODE" = "check" ]; then
	# Check code formatting with black (no changes)
	poetry run black --check sismanager/ tests/
else
	# Format code with black
	poetry run black sismanager/ tests/
fi

# Run pylint for code quality
poetry run pylint sismanager/

# Run mypy for type checking
poetry run mypy sismanager/
