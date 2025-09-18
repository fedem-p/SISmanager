"""Simple test for the simplified importer functionality."""

import tempfile
import pandas as pd
import pytest
from sismanager import create_app


@pytest.fixture
def app():
    """Create and configure a test Flask application."""
    app = create_app()
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key"  # Required for flash messages
    return app


@pytest.fixture
def client(app):
    """Create a test client for the Flask application."""
    return app.test_client()


@pytest.fixture
def sample_xlsx_file():
    """Create a sample XLSX file for testing."""
    # Create sample data
    data = {
        "idOrderPos": [1, 2, 3],
        "descrizioneMateriale": ["Material 1", "Material 2", "Material 3"],
        "codiceMateriale": ["CODE1", "CODE2", "CODE3"],
        "quantity": [10, 20, 30],
    }
    df = pd.DataFrame(data)

    # Create temporary file
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        df.to_excel(tmp.name, index=False)
        yield tmp.name

    # No cleanup needed as tempfile handles it


def test_importer_page_loads(client):
    """Test that the simplified importer page loads correctly."""
    response = client.get("/importer")
    
    assert response.status_code == 200
    assert b"Upload" in response.data or b"upload" in response.data


def test_file_upload_simplified(client, sample_xlsx_file):
    """Test the simplified file upload workflow."""
    with open(sample_xlsx_file, "rb") as f:
        response = client.post(
            "/importer/upload",
            data={"file": (f, "test.xlsx")},
            content_type="multipart/form-data",
            follow_redirects=True  # Follow any redirects
        )
    
    # Should redirect back to importer page with success message
    assert response.status_code == 200
    # Should have some indication of success (flash message or result)
    response_text = response.data.decode()
    success_indicators = ["success", "completed", "processed", "imported"]
    assert any(indicator in response_text.lower() for indicator in success_indicators)


def test_api_status_endpoint(client):
    """Test that the API status endpoint still works."""
    response = client.get("/api/status")
    
    assert response.status_code == 200
    data = response.get_json()
    assert "success" in data
    assert "files" in data


def test_no_file_upload(client):
    """Test upload without file."""
    response = client.post(
        "/importer/upload",
        data={},
        follow_redirects=True
    )
    
    assert response.status_code == 200
    # Should show error message
    response_text = response.data.decode()
    error_indicators = ["error", "no file", "required", "missing"]
    assert any(indicator in response_text.lower() for indicator in error_indicators)


if __name__ == "__main__":
    # Run basic tests if called directly
    import os
    os.system("poetry run pytest " + __file__ + " -v")
