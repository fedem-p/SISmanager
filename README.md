# SISmanager

SISmanager is a project for managing Student Information Systems. This repository is set up for development and testing using Docker and Poetry as the dependency manager.

## Features
- Dockerized development and testing
- Poetry for dependency management

## Getting Started

### Prerequisites
- Docker
- Docker Compose

### Development

1. Clone the repository:
   ```bash
   git clone <repo-url>
   cd SISmanager
   ```
2. Build and start the containers:
   ```bash
   docker-compose up --build
   ```

### Poetry Usage

To add dependencies (inside the container):
```bash
poetry add <package>
```

To run tests (inside the container):
```bash
poetry run pytest
```

## License
Add your license information here.
