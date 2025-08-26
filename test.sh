#!/bin/bash
# Run all tests for SISmanager

set -e

# Run all tests with pytest
poetry run pytest

# Optionally run with verbose output and coverage (uncomment if needed)
# poetry run pytest -v --cov=src --cov-report=term-missing