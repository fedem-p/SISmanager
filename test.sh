#!/bin/bash
# Run all tests for SISmanager

set -e

# Run all tests with pytest
poetry run pytest -v --cov=src --cov-report=term-missing