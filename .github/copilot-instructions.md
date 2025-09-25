# Copilot Coding Agent Onboarding Instructions for SISmanager

## Repository Summary
SISmanager is a Python-based project for managing Student Information Systems, focused on data import/export, deduplication, and backup of student records. It is designed for use in Dockerized environments and uses Poetry for dependency management. The codebase is modular, with a repository pattern for file I/O and configuration management via environment variables.

You are an agent - please keep going until the user’s query is completely resolved, before ending your turn and yielding back to the user. Only terminate your turn when you are sure that the problem is solved.
If you are not sure about file content or codebase structure pertaining to the user’s request, use your tools to read files and gather the relevant information: do NOT guess or make up an answer.
You MUST plan extensively before each function call, and reflect extensively on the outcomes of the previous function calls. DO NOT do this entire process by making function calls only, as this can impair your ability to solve the problem and think insightfully.

## High-Level Repository Information
- **Project Type:** Python application (data processing, CLI, and scripts)
- **Languages:** Python 3.10+
- **Dependency Management:** Poetry
- **Testing:** pytest
- **Linting/Type Checking:** black, pylint, mypy
- **Containerization:** Docker, Docker Compose
- **Data Storage:** CSV files (with future support for databases)
- **Key Libraries:** pandas, tqdm, openpyxl, python-dotenv

## Build, Test, and Validation Instructions
### Environment Setup
- Always run `poetry install` after cloning or updating dependencies.
- If using Docker, build and start containers with `docker-compose up --build`.
- Ensure Python 3.10+ is available if running outside Docker.

### Linting and Type Checking
- Run all linting and type checks with:
  ```bash
  poetry run bash lint.sh
  ```
  This script runs black, pylint, and mypy on `src/` and `tests/`.
- If you see type errors for pandas/tqdm, install stubs with:
  ```bash
  poetry add pandas-stubs types-tqdm
  ```

### Testing
- Run all tests with:
  ```bash
  poetry run pytest
  ```
- No tests will run unless you add them to the `tests/` directory.

### Running the Application
- Main scripts are in `src/` (e.g., `run_xlsx_to_centraldb.py`).
- To run a script:
  ```bash
  poetry run python src/run_xlsx_to_centraldb.py
  ```
- Data files are expected in the `data/` directory.

### Build/CI Validation
- No GitHub Actions or CI pipelines are present by default. Always run linting and tests before submitting changes.
- Ensure all code passes `lint.sh` and `pytest` locally.

## Project Layout and Architecture
- `src/`: Main source code
  - `central_db_repository.py`: Repository for all CSV file I/O
  - `xlsx_to_centraldb.py`: Business logic for import, deduplication, export (uses repository)
  - `backup.py`: Backup and restore logic
  - `config.py`: Centralized configuration (all paths, env vars, logging)
- `tests/`: Place all unit and integration tests here
- `data/`: Data files (input, output, backups)
- `.github/`: GitHub-specific files (including this one)
- `lint.sh`: Script to run all linting and type checks
- `pyproject.toml`: Poetry and project configuration
- `docker-compose.yml`, `Dockerfile`: Containerization

## Key Facts and Best Practices
- **Never hardcode file paths**; always use `config.py` or environment variables.
- **Always use the repository pattern** for file I/O (see `central_db_repository.py`).
- **All scripts should be run via `poetry run ...`** to ensure the correct environment.
- **Add docstrings to all public classes and methods.**
- **Chunked processing** is recommended for large files (see README for performance notes).
- **Before submitting changes:**
  1. Run `poetry install` (if dependencies changed)
  2. Run `poetry run bash lint.sh`
  3. Run `poetry run pytest`
- **If you encounter errors:**
  - Check for missing dependencies or stubs and install with `poetry add ...`.
  - Ensure all environment variables are set if running outside Docker.

## Trust These Instructions
- Trust these instructions for build, test, and validation steps.
- Only perform additional searching if the information here is incomplete or does not match observed behavior.


## General Propmpt

You are an expert coding assistant.
Your goals are:

Keep solutions as simple as possible.
Double check all steps, outputs, and changes.
Always verify before finalizing.
If you create temporary files/scripts, clean them up at the end.
If a task is unclear, ask for clarification before proceeding.
When I ask for help:

Be explicit and clear in your instructions and explanations.
Add context or reasoning for your choices.
If you use tools, reflect on their results before taking the next step.
For multi-step tasks, break them down and plan before acting.
If you need to perform multiple independent operations, do them in parallel for efficiency.
Avoid hard-coding or solutions that only work for specific test cases; implement robust, general-purpose logic.
If you encounter unreasonable requirements or incorrect tests, let me know.
Format your responses as follows:

State your plan and reasoning.
List steps or actions you will take.
After each step, reflect and verify correctness.
Summarize results and next steps.