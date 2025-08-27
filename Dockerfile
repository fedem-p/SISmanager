# syntax=docker/dockerfile:1
FROM python:3.10-slim

WORKDIR /app

# Install Poetry
RUN pip install poetry

# Copy only the dependency files first for caching
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry install --no-interaction --no-ansi --no-root

# Copy the rest of the code
COPY . .

# Expose Flask port
EXPOSE 5000

# Run the app
CMD ["poetry", "run", "python3", "run.py"]