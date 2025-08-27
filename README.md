# SISmanager

SISmanager is a Python-based project for managing Student Information Systems, focused on data import/export, deduplication, and backup of student records. It is designed for use in Dockerized environments and uses Poetry for dependency management.

## Features

- **Data Import/Export**: Import data from XLSX files and export to various formats
- **Data Deduplication**: Intelligent duplicate detection and removal with user confirmation options
- **Backup Management**: Automated backup creation, verification, and cleanup
- **Repository Pattern**: Clean separation of data access logic for maintainability
- **Comprehensive Testing**: Full unit and integration test coverage
- **Dockerized Development**: Consistent development environment using Docker and Docker Compose
- **Configuration Management**: Environment-based configuration with sensible defaults

## Architecture

SISmanager follows a modular architecture with clear separation of concerns:

### Core Modules

- **`CentralDBRepository`**: Handles all file I/O operations for the central CSV database
- **`XLSXImporter`**: Manages XLSX file import, processing, and data transformation
- **`BackupManager`**: Provides backup creation, verification, and cleanup functionality
- **`config`**: Centralized configuration and logging management

### Data Flow

1. **Import**: XLSX files are read and processed with automatic orderCode generation
2. **Backup**: Automatic backup creation before any data modifications
3. **Append**: New data is appended to the central database
4. **Deduplicate**: Intelligent duplicate detection with optional user confirmation
5. **Export**: Data can be exported to XLSX with optional column filtering

## Getting Started

### Prerequisites

- Docker and Docker Compose (recommended)
- OR Python 3.10+ and Poetry for local development

### Docker Development (Recommended)

1. Clone the repository:
   ```bash
   git clone <repo-url>
   cd SISmanager
   ```

2. Build and start the containers:
   ```bash
   docker-compose up --build
   ```

### Local Development

1. Install Poetry if not already installed:
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. Install dependencies:
   ```bash
   poetry install
   ```

3. Activate the virtual environment:
   ```bash
   poetry shell
   ```

## Configuration

SISmanager uses environment variables for configuration. All configuration options have sensible defaults.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SISMANAGER_DATA_DIR` | `./data` | Directory for data files |
| `SISMANAGER_BACKUP_DIR` | `./data/backups` | Directory for backup files |
| `SISMANAGER_CENTRAL_DB_PATH` | `./data/central_db.csv` | Path to central database file |
| `SISMANAGER_LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `SISMANAGER_DB_TYPE` | `csv` | Database type (future: sqlite, postgresql) |
| `SISMANAGER_DB_URL` | `""` | Database connection URL (for future use) |

### Example Configuration

Create a `.env` file in the project root:

```bash
SISMANAGER_DATA_DIR=/custom/data/path
SISMANAGER_LOG_LEVEL=DEBUG
SISMANAGER_BACKUP_DIR=/custom/backup/path
```

## Usage Examples

### Basic XLSX Import

```python
from src.xlsx_importer import XLSXImporter

# Import an XLSX file
importer = XLSXImporter("data/orders.xlsx")
importer.process()

# Remove duplicates (with confirmation)
importer.remove_duplicates(mode="soft")

# Export to XLSX
importer.export_to_xlsx("output/exported_data.xlsx")
```

### Advanced Import with Column Filtering

```python
from src.xlsx_importer import XLSXImporter

# Import only specific columns
columns_to_keep = ['idOrderPos', 'descrizioneMateriale', 'quantity']
importer = XLSXImporter("data/orders.xlsx", columns_to_keep=columns_to_keep)
importer.process()
```

### Manual Database Operations

```python
from src.central_db_repository import CentralDBRepository
import pandas as pd

# Create repository instance
repo = CentralDBRepository()

# Read current data
data = repo.read()
print(f"Current records: {len(data)}")

# Add new data
new_data = pd.DataFrame({
    'orderCode': ['ORDER001'],
    'quantity': [10]
})
repo.append(new_data)

# Export with column filtering
repo.export_to_xlsx("filtered_export.xlsx", columns=['orderCode', 'quantity'])
```

### Backup Management

```python
from src.backup import BackupManager

# Create backup manager
backup_manager = BackupManager()

# Create backup
backup_manager.backup_central_db()

# Clean old backups (older than 30 days)
deleted_count, freed_space = backup_manager.delete_old_backups(days=30)
print(f"Deleted {deleted_count} old backups, freed {freed_space/1024/1024:.2f} MB")
```

## Testing

SISmanager includes comprehensive test coverage with both unit and integration tests.

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run only unit tests
poetry run pytest tests/unit/

# Run only integration tests
poetry run pytest tests/integration/

# Run tests with coverage report
poetry run pytest --cov=src --cov-report=html

# Run specific test file
poetry run pytest tests/unit/test_central_db_repository.py
```

### Test Structure

- **Unit Tests** (`tests/unit/`): Test individual components in isolation
  - `test_central_db_repository.py`: Database operations
  - `test_xlsx_importer.py`: XLSX import functionality
  - `test_backup_manager.py`: Backup operations
  - `test_config.py`: Configuration management

- **Integration Tests** (`tests/integration/`): Test complete workflows
  - `test_workflows.py`: End-to-end import, backup, and export flows

- **Test Fixtures** (`tests/fixtures/`): Sample data files for testing

### Test Coverage

Current test coverage includes:
- ✅ 62 unit tests covering all core modules
- ✅ 9 integration tests covering complete workflows
- ✅ Error handling and edge cases
- ✅ Backup and rollback scenarios
- ✅ Data validation and integrity checks

## Development

### Code Quality

The project maintains high code quality standards:

```bash
# Run all linting and formatting
poetry run bash lint.sh

# Individual tools
poetry run black src/ tests/          # Code formatting
poetry run pylint src/ tests/         # Code quality analysis
poetry run mypy src/ tests/           # Type checking
```

### Project Structure

```
SISmanager/
├── pyproject.toml
├── poetry.lock
├── run.py                          # Application entry point (create this if missing)
├── config.py                       # Configuration
├── sismanager/                     # Main package
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── student.py
│   │   ├── part.py
│   │   └── money.py
│   ├── blueprints/
│   │   ├── __init__.py
│   │   ├── main/
│   │   │   ├── __init__.py
│   │   │   ├── routes.py
│   │   │   └── templates/
│   │   ├── importer/
│   │   │   ├── __init__.py
│   │   │   ├── routes.py
│   │   │   ├── forms.py
│   │   │   └── templates/
│   │   ├── calendar/
│   │   ├── materials/
│   │   └── money/
│   ├── services/
│   │   ├── __init__.py
│   │   ├── csv_service.py
│   │   ├── backup_service.py
│   │   └── import_service.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── validators.py
│   │   └── helpers.py
│   ├── static/
│   │   ├── css/
│   │   ├── js/
│   │   └── img/
│   └── templates/
│       └── base.html
├── data/
│   ├── central_db.csv
│   ├── backups/
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── fixtures/
│   ├── integration/
│   └── unit/
├── deployment/
│   ├── windows/
│   └── docker/
└── scripts/                        # (optional, for CLI/test scripts)
    └── run_xlsx_to_centraldb.py
```

### Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Make your changes and add tests
4. Run the test suite: `poetry run pytest`
5. Run linting: `poetry run bash lint.sh`
6. Commit your changes: `git commit -am 'Add new feature'`
7. Push to the branch: `git push origin feature/new-feature`
8. Submit a pull request

### Performance Considerations

- **Chunked Processing**: For large files, consider processing data in chunks
- **Memory Usage**: The system loads entire XLSX files into memory
- **Backup Storage**: Regular cleanup of old backups is recommended
- **Progress Tracking**: Import operations show progress bars for large files

## Common Workflows

### 1. Daily Data Import

```bash
# Place XLSX files in data/ directory
poetry run python src/run_xlsx_to_centraldb.py
```

### 2. Data Cleanup

```python
from src.central_db_repository import CentralDBRepository

repo = CentralDBRepository()
# Remove duplicates with confirmation
duplicates_removed = repo.deduplicate(mode="soft")
print(f"Removed {duplicates_removed} duplicates")
```

### 3. Data Export for Reporting

```python
from src.central_db_repository import CentralDBRepository

repo = CentralDBRepository()
# Export specific columns for reporting
repo.export_to_xlsx(
    "reports/monthly_report.xlsx",
    columns=["orderCode", "descrizioneMateriale", "quantity"]
)
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Check that XLSX files are in the correct format and accessible
2. **Permission Errors**: Ensure the application has write access to data directories
3. **Memory Issues**: For very large files, consider breaking them into smaller chunks
4. **Backup Failures**: Check available disk space and file permissions

### Logging

Logs are written to both console and `sismanager.log` file. Increase log level for debugging:

```bash
export SISMANAGER_LOG_LEVEL=DEBUG
```

## License

[Add your license information here]

## Support

For questions or issues, please:
1. Check the troubleshooting section above
2. Review existing issues in the repository
3. Create a new issue with detailed information about your problem


