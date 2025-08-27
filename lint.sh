#!/bin/bash
# Run all linting and type checking tools for SISmanager

set -e

# Format code with black
poetry run black sismanager/ tests/

# Run pylint for code quality
poetry run pylint sismanager/

# Run mypy for type checking
poetry run mypy sismanager/
