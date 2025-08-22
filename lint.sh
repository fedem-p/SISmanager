#!/bin/bash
# Run all linting and type checking tools for SISmanager

set -e

# Format code with black
poetry run black src/ tests/

# Run pylint for code quality
poetry run pylint src/ tests/

# Run mypy for type checking
poetry run mypy src/ tests/
