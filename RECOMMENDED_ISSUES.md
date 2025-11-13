# Recommended Issues for SISmanager

This document contains actionable issues derived from the comprehensive audit report. Each issue is ready to be created as a GitHub issue with clear acceptance criteria and implementation guidance.

---

## P0 (Critical) - Security Fundamentals

### Issue 1: Add Flask Secret Key Configuration

**Labels:** `security`, `P0-critical`, `configuration`  
**Effort:** XS (1-2 hours)

#### Description
Flask application currently lacks a secret key configuration, which is critical for session security and CSRF protection. Without this, sessions are not secure and the application is vulnerable to session hijacking.

#### Current State
```python
def create_app():
    app = Flask(__name__)
    # No secret key set!
```

#### Proposed Solution
Add secret key configuration with environment variable support:
```python
def create_app():
    app = Flask(__name__)
    
    # Set secret key
    app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY') or \
        os.urandom(24).hex()
    
    # Security configurations
    app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
```

#### Acceptance Criteria
- [ ] Secret key loaded from FLASK_SECRET_KEY environment variable
- [ ] Fallback to secure random key in development
- [ ] Cookie security settings configured
- [ ] .env.example file created with FLASK_SECRET_KEY
- [ ] README updated with environment variable documentation
- [ ] All existing tests pass

#### Implementation Steps
1. Update `sismanager/__init__.py` with secret key configuration
2. Create `.env.example` with required variables
3. Update README.md environment variables section
4. Test session functionality
5. Verify security settings

---

### Issue 2: Enhance File Upload Security Validation

**Labels:** `security`, `P0-critical`, `file-upload`  
**Effort:** S (3-8 hours)

#### Description
Current file upload validation only checks file extensions, which can be easily spoofed. This leaves the application vulnerable to malicious file uploads. Need comprehensive validation including content-based type checking, file size limits, and secure filename handling.

#### Current State
- Extension-only validation: `ALLOWED_EXTENSIONS = {"xlsx", "xls"}`
- No file size limits
- No content type validation
- Predictable file storage locations

#### Proposed Solution
Implement comprehensive file validation:
```python
import magic
from werkzeug.utils import secure_filename

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_MIME_TYPES = [
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-excel'
]

def validate_upload_file(file):
    """Comprehensive file upload validation."""
    if not file or file.filename == '':
        raise InvalidFileFormatError("No file provided")
    
    filename = secure_filename(file.filename)
    
    # Check extension
    if not allowed_file(filename):
        raise InvalidFileFormatError("Invalid file extension")
    
    # Check file size
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    if size > MAX_FILE_SIZE:
        raise InvalidFileFormatError(f"File too large")
    
    # Check MIME type
    mime = magic.from_buffer(file.read(2048), mime=True)
    file.seek(0)
    if mime not in ALLOWED_MIME_TYPES:
        raise InvalidFileFormatError(f"Invalid file type")
    
    return filename
```

#### Acceptance Criteria
- [ ] python-magic added to dependencies
- [ ] Content-based file type validation implemented
- [ ] File size limits enforced (configurable)
- [ ] Secure filename handling with werkzeug
- [ ] Custom exception for validation errors
- [ ] Tests for malicious file uploads
- [ ] Tests for oversized files
- [ ] Flash messages for validation errors
- [ ] Documentation updated

---

## P1 (High) - Quality & Essential Security

### Issue 3: Add CSRF Protection with Flask-WTF

**Labels:** `security`, `P1-high`, `forms`  
**Effort:** M (1-3 days)

#### Description
Application forms lack CSRF protection, making them vulnerable to Cross-Site Request Forgery attacks. Implement Flask-WTF for comprehensive form security.

#### Dependencies
- Issue #1 (Secret Key) must be completed first

#### Proposed Solution
```python
# Add dependency
[tool.poetry.dependencies]
flask-wtf = "^1.2.0"

# Enable in app factory
from flask_wtf.csrf import CSRFProtect

def create_app():
    app = Flask(__name__)
    csrf = CSRPProtect(app)
    return app

# Update all forms
<form method="POST">
    {{ csrf_token() }}
    <!-- fields -->
</form>
```

#### Acceptance Criteria
- [ ] Flask-WTF added to dependencies
- [ ] CSRF protection enabled globally
- [ ] All POST forms include CSRF tokens
- [ ] CSRF error handling implemented
- [ ] Tests updated for CSRF tokens
- [ ] Documentation updated

---

### Issue 4: Increase Blueprint Route Test Coverage to 90%+

**Labels:** `testing`, `P1-high`, `quality`  
**Effort:** M (1-3 days)

#### Description
Blueprint routes have low test coverage (24-80%). Critical user-facing functionality is not adequately tested, which could hide bugs and regressions.

#### Current Coverage
- `importer/routes.py`: 29%
- `db_viewer/routes.py`: 24%
- `calendar/routes.py`: 80%
- Other routes: 80%

**Target:** 90%+ coverage for all routes

#### Proposed Solution
Create comprehensive route tests:
```python
# tests/unit/test_importer_routes.py
def test_upload_valid_file(client, sample_xlsx):
    """Test successful file upload and processing."""
    pass

def test_upload_invalid_extension(client):
    """Test rejection of invalid file types."""
    pass

def test_upload_no_file(client):
    """Test handling of missing file."""
    pass

def test_download_file(client):
    """Test file download endpoint."""
    pass
```

#### Acceptance Criteria
- [ ] Test file created for each blueprint
- [ ] Coverage for importer routes: 90%+
- [ ] Coverage for db_viewer routes: 90%+
- [ ] Edge cases covered (empty files, errors, invalid data)
- [ ] Mock external dependencies
- [ ] All tests passing
- [ ] CI reports coverage metrics

---

### Issue 5: Implement Standardized Error Handling

**Labels:** `error-handling`, `P1-high`, `quality`  
**Effort:** M (1-3 days)

#### Description
Error handling is inconsistent across the application. Need custom exceptions and standardized error responses for better debugging and user experience.

#### Proposed Solution
```python
# sismanager/exceptions.py
class SISManagerException(Exception):
    """Base exception."""
    status_code = 500

class FileNotFoundError(SISManagerException):
    status_code = 404

class InvalidFileFormatError(SISManagerException):
    status_code = 400

# Error handlers in app factory
@app.errorhandler(SISManagerException)
def handle_error(error):
    flash(str(error), 'error')
    return render_template('error.html', error=error), error.status_code
```

#### Acceptance Criteria
- [ ] Custom exception hierarchy created
- [ ] All services raise typed exceptions
- [ ] Flask error handlers implemented
- [ ] User-friendly error messages
- [ ] Error template created
- [ ] Tests for error scenarios
- [ ] Documentation updated

---

### Issue 6: Add Flask Security Headers

**Labels:** `security`, `P1-high`  
**Effort:** XS (1-2 hours)

#### Description
Application lacks security headers, leaving it vulnerable to common web attacks.

#### Proposed Solution
```python
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Content-Security-Policy'] = "default-src 'self'"
    return response
```

#### Acceptance Criteria
- [ ] Security headers middleware implemented
- [ ] Headers verified in response
- [ ] CSP policy defined
- [ ] Tests verify headers present
- [ ] Documentation updated

---

### Issue 7: Enhance Template Organization

**Labels:** `frontend`, `P1-high`, `templates`  
**Effort:** S (3-8 hours)

#### Description
Templates have inline CSS and limited reusability. Need better organization with components and proper flash message handling.

#### Proposed Solution
- Create `templates/components/` directory
- Extract navbar to `components/navbar.html`
- Create `components/flash_messages.html`
- Add template macros for common elements
- Proper CSS organization

#### Acceptance Criteria
- [ ] Component templates created
- [ ] Flash message handling standardized
- [ ] Template macros for common UI elements
- [ ] CSS moved to separate files
- [ ] Responsive design considerations
- [ ] All pages render correctly

---

### Issue 8: Plan Database Migration Strategy

**Labels:** `database`, `P1-high`, `architecture`, `epic`  
**Effort:** L (1-2 weeks)

#### Description
Current CSV-based storage limits scalability. Plan and implement migration to SQL database as mentioned in config.py.

#### Proposed Phases
1. Add SQLAlchemy models (parallel to CSV)
2. Implement dual-write mode
3. Add Flask-Migrate
4. Create migration scripts
5. Switch to SQL-only
6. Remove CSV code

#### Acceptance Criteria
- [ ] SQLAlchemy models defined
- [ ] Migration plan documented
- [ ] Flask-Migrate integrated
- [ ] Data migration scripts created
- [ ] Performance benchmarks
- [ ] Rollback plan documented
- [ ] All tests pass with SQL backend

---

### Issue 9: Add Data Validation Layer

**Labels:** `validation`, `P1-high`, `data-quality`  
**Effort:** M (1-3 days)

#### Description
No explicit data validation before database writes. Need schema validation to ensure data integrity.

#### Proposed Solution
```python
from marshmallow import Schema, fields, validate

class StudentRecordSchema(Schema):
    order_code = fields.Str(required=True)
    quantity = fields.Integer(required=True, validate=validate.Range(min=0))
    # ... other fields

def validate_dataframe(df, schema):
    # Validate each row
    pass
```

#### Acceptance Criteria
- [ ] marshmallow added to dependencies
- [ ] Validation schema defined for all data models
- [ ] Validation applied before all writes
- [ ] Clear error messages for validation failures
- [ ] Tests for valid and invalid data
- [ ] Documentation updated

---

## P2 (Medium) - Architecture & Performance

### Issue 10: Implement Storage Backend Strategy Pattern

**Labels:** `architecture`, `P2-medium`, `refactoring`  
**Effort:** M (1-3 days)

#### Description
Prepare for future database migration by implementing storage backend abstraction using Strategy pattern.

#### Proposed Solution
```python
from abc import ABC, abstractmethod

class StorageBackend(ABC):
    @abstractmethod
    def read(self) -> pd.DataFrame:
        pass
    
    @abstractmethod
    def write(self, df: pd.DataFrame) -> None:
        pass

class CSVStorageBackend(StorageBackend):
    # Current implementation
    pass

class SQLStorageBackend(StorageBackend):
    # Future implementation
    pass
```

#### Acceptance Criteria
- [ ] Abstract base class created
- [ ] CSV backend implements interface
- [ ] Factory method for backend selection
- [ ] Configuration-based backend selection
- [ ] All tests pass
- [ ] No breaking changes

---

### Issue 11: Add Security Scanning with Bandit

**Labels:** `security`, `P2-medium`, `ci`  
**Effort:** XS (1-2 hours)

#### Description
Add automated security scanning to CI pipeline using Bandit.

#### Proposed Solution
```bash
# Add to dependencies
poetry add --group dev bandit

# Add to lint.sh
poetry run bandit -r sismanager/ -f screen

# Update CI
- name: Security scan
  run: poetry run bandit -r sismanager/
```

#### Acceptance Criteria
- [ ] Bandit added to dev dependencies
- [ ] Integrated into lint.sh
- [ ] CI runs security checks
- [ ] Zero high-severity findings
- [ ] Documentation updated

---

### Issue 12: Add Import Sorting with isort

**Labels:** `code-quality`, `P2-medium`, `ci`  
**Effort:** XS (1-2 hours)

#### Description
Standardize import organization across the codebase.

#### Acceptance Criteria
- [ ] isort configured in pyproject.toml
- [ ] Compatible with black
- [ ] All imports reformatted
- [ ] Integrated into lint.sh
- [ ] CI enforces import order

---

### Issue 13: Implement Rate Limiting

**Labels:** `security`, `P2-medium`, `performance`  
**Effort:** S (3-8 hours)

#### Description
Add rate limiting to protect against abuse, especially on file upload endpoints.

#### Proposed Solution
```python
from flask_limiter import Limiter

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@importer_bp.route("/upload", methods=["POST"])
@limiter.limit("10 per hour")
def upload():
    pass
```

#### Acceptance Criteria
- [ ] Flask-Limiter installed
- [ ] Rate limits configured
- [ ] Upload endpoints protected
- [ ] Error messages for rate exceeded
- [ ] Documentation updated
- [ ] Tests verify limits

---

### Issue 14: Environment-Based Configuration Classes

**Labels:** `configuration`, `P2-medium`, `refactoring`  
**Effort:** S (3-8 hours)

#### Description
Replace global config variables with class-based configuration for different environments.

#### Proposed Solution
```python
class Config:
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY')
    
class DevelopmentConfig(Config):
    DEBUG = True
    
class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
```

#### Acceptance Criteria
- [ ] Config classes created
- [ ] Environment selection working
- [ ] Tests use testing config
- [ ] No hardcoded values
- [ ] Documentation updated

---

### Issue 15: Multi-Stage Docker Build

**Labels:** `docker`, `P2-medium`, `devops`  
**Effort:** S (3-8 hours)

#### Description
Optimize Dockerfile with multi-stage build for smaller images and better security.

#### Proposed Solution
```dockerfile
# Builder stage
FROM python:3.10-slim as builder
# ... install dependencies

# Runtime stage
FROM python:3.10-slim
# ... copy artifacts
USER appuser
```

#### Acceptance Criteria
- [ ] Multi-stage build implemented
- [ ] Image size reduced by 30%+
- [ ] Non-root user configured
- [ ] Gunicorn for production
- [ ] Documentation updated

---

### Issue 16: Add Docker Security Scanning

**Labels:** `security`, `P2-medium`, `docker`, `ci`  
**Effort:** XS (1-2 hours)

#### Description
Add container vulnerability scanning to CI pipeline.

#### Acceptance Criteria
- [ ] Trivy integrated into CI
- [ ] Scans run on Docker build
- [ ] Fails on high/critical vulnerabilities
- [ ] Results visible in PR

---

### Issue 17: Implement Chunked File Processing

**Labels:** `performance`, `P2-medium`, `optimization`  
**Effort:** M (1-3 days)

#### Description
Add support for processing large XLSX files in chunks to reduce memory usage.

#### Proposed Solution
```python
def read_xlsx_chunked(self, chunk_size=10000):
    chunks = []
    for chunk in pd.read_excel(self.xlsx_path, chunksize=chunk_size):
        chunks.append(chunk)
    return pd.concat(chunks)
```

#### Acceptance Criteria
- [ ] Chunked processing implemented
- [ ] Configuration for chunk size
- [ ] Memory usage testing
- [ ] Performance benchmarks
- [ ] Documentation updated

---

### Issue 18: Add Application Context Management

**Labels:** `flask`, `P2-medium`, `architecture`  
**Effort:** S (3-8 hours)

#### Description
Properly use Flask application context for resource management.

#### Acceptance Criteria
- [ ] Request context properly used
- [ ] Resources cleaned up in teardown
- [ ] Tests verify context handling
- [ ] No resource leaks

---

### Issue 19: Improve .gitignore

**Labels:** `git`, `P2-medium`, `quick-win`  
**Effort:** XS (15 minutes)

#### Description
Add missing entries to .gitignore for better repository hygiene.

#### Additions Needed
```
.env
sismanager.log
data/uploads/*
data/processed/*
*.tmp
```

#### Acceptance Criteria
- [ ] .gitignore updated
- [ ] No sensitive files in repo
- [ ] Build artifacts excluded

---

### Issue 20: Add Performance Testing

**Labels:** `testing`, `P2-medium`, `performance`  
**Effort:** S (3-8 hours)

#### Description
Create performance test suite for large file processing.

#### Proposed Tests
- Import 10k row files
- Memory usage monitoring
- Processing time benchmarks

#### Acceptance Criteria
- [ ] Performance test suite created
- [ ] Baseline metrics established
- [ ] Memory profiling
- [ ] Optional CI integration

---

## P3 (Low) - Documentation & Nice-to-Have

### Issue 21: Add API Documentation

**Labels:** `documentation`, `P3-low`  
**Effort:** S (3-8 hours)

#### Description
Auto-generate API documentation with Swagger/OpenAPI.

#### Acceptance Criteria
- [ ] Flask-RESTX or similar integrated
- [ ] API docs auto-generated
- [ ] Swagger UI available
- [ ] Examples in documentation

---

### Issue 22: Create Architecture Documentation

**Labels:** `documentation`, `P3-low`  
**Effort:** S (3-8 hours)

#### Description
Document system architecture with diagrams.

#### Contents
- System architecture diagram
- Data flow diagrams
- Component interactions
- Database schema

#### Acceptance Criteria
- [ ] `docs/ARCHITECTURE.md` created
- [ ] Diagrams included
- [ ] Decision records
- [ ] Up-to-date with code

---

### Issue 23: Create Deployment Guide

**Labels:** `documentation`, `P3-low`, `devops`  
**Effort:** S (3-8 hours)

#### Description
Comprehensive production deployment documentation.

#### Contents
- Production deployment steps
- Environment variables reference
- Backup procedures
- Monitoring setup
- Troubleshooting guide

#### Acceptance Criteria
- [ ] `docs/DEPLOYMENT.md` created
- [ ] Step-by-step instructions
- [ ] Configuration examples
- [ ] Troubleshooting section

---

### Issue 24: Add User Authentication (Future)

**Labels:** `feature`, `P3-low`, `authentication`, `epic`  
**Effort:** L (1-2 weeks)

#### Description
Implement user authentication and role-based access control for future multi-user scenarios.

#### Proposed Stack
- Flask-Login
- User model and database
- Role-based access control
- Login/logout pages

#### Acceptance Criteria
- [ ] Flask-Login integrated
- [ ] User model created
- [ ] Registration/login pages
- [ ] Password hashing
- [ ] Session management
- [ ] Role-based permissions
- [ ] Tests for auth flows

---

### Issue 25: Add Monitoring and Structured Logging

**Labels:** `monitoring`, `P3-low`, `logging`  
**Effort:** M (1-3 days)

#### Description
Enhanced logging with structured format and application metrics.

#### Features
- JSON-formatted logs
- Request/response logging
- Application metrics
- Error tracking (Sentry)

#### Acceptance Criteria
- [ ] Structured logging implemented
- [ ] Metrics collection
- [ ] Optional Sentry integration
- [ ] Documentation updated

---

## Summary Statistics

**Total Issues:** 25

**By Priority:**
- P0 (Critical): 2 issues
- P1 (High): 7 issues  
- P2 (Medium): 12 issues
- P3 (Low): 4 issues

**By Effort:**
- XS (1-2h): 6 issues
- S (3-8h): 9 issues
- M (1-3d): 7 issues
- L (1-2w): 3 issues

**Quick Wins (XS + S effort):** 15 issues

---

## Recommended Implementation Order

### Sprint 1 (Week 1): Critical Security
1. Issue #1: Flask Secret Key
2. Issue #2: File Upload Security
3. Issue #6: Security Headers
4. Issue #3: CSRF Protection

### Sprint 2 (Week 2): Quality & Testing
5. Issue #4: Blueprint Test Coverage
6. Issue #5: Standardized Error Handling
7. Issue #11: Bandit Security Scanning
8. Issue #12: isort Integration

### Sprint 3 (Week 3): Architecture
9. Issue #10: Storage Backend Pattern
10. Issue #14: Environment Config
11. Issue #7: Template Organization
12. Issue #19: Improve .gitignore

### Sprint 4 (Week 4-5): Database & Performance
13. Issue #8: Database Migration (Epic)
14. Issue #9: Data Validation
15. Issue #17: Chunked Processing

### Sprint 5 (Week 6): DevOps
16. Issue #15: Multi-Stage Docker
17. Issue #16: Docker Security Scan
18. Issue #13: Rate Limiting

### Sprint 6 (Week 7-8): Documentation & Polish
19. Issue #20: Performance Testing
20. Issue #21: API Documentation
21. Issue #22: Architecture Docs
22. Issue #23: Deployment Guide

### Future Backlog
23. Issue #18: Context Management
24. Issue #24: User Authentication (Epic)
25. Issue #25: Monitoring & Logging

---

## Notes for Implementation

1. **Dependencies:** Some issues depend on others (e.g., CSRF needs Secret Key)
2. **Testing:** All changes should include tests
3. **Documentation:** Update docs with each change
4. **Code Review:** Maintain current 10/10 code quality
5. **Simplicity:** Keep implementations simple per project values

This roadmap takes the project from its current excellent foundation to production-ready enterprise-grade application in approximately 8-14 weeks of focused development.
