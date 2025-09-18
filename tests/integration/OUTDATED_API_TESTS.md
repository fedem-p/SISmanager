# Note: Integration tests are outdated for simplified importer

The tests in `test_importer_api.py` were designed for the complex multi-endpoint API that has been simplified.

## Current Implementation
- Single workflow endpoint: `/importer/upload`
- Simplified form-based interface
- Direct service integration

## Test Coverage
The simplified functionality is covered by:
- `tests/test_importer_simplified.py` - Tests the new simplified workflow
- Manual validation of core services (XLSXImporter, FileManager, etc.)

## Legacy Tests
The old integration tests in `test_importer_api.py` test endpoints that no longer exist:
- `/api/upload` → now `/importer/upload`
- `/api/process` → integrated into upload workflow
- `/api/remove-duplicates` → part of XLSXImporter.process()
- `/api/export` → part of XLSXImporter.process()

These tests should be updated or replaced with tests for the simplified approach.
