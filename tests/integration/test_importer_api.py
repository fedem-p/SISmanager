"""Integration tests for importer API endpoints."""

import os
import tempfile
import pytest
from flask import Flask
from sismanager import create_app
from sismanager.config import DATA_DIR


@pytest.fixture
def app():
    """Create and configure a test Flask application."""
    app = create_app()
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    """Create a test client for the Flask application."""
    return app.test_client()


@pytest.fixture
def sample_xlsx_file():
    """Create a sample XLSX file for testing."""
    import pandas as pd
    
    # Create sample data
    data = {
        'idOrderPos': [1, 2, 3],
        'descrizioneMateriale': ['Material 1', 'Material 2', 'Material 3'],
        'codiceMateriale': ['CODE1', 'CODE2', 'CODE3'],
        'quantity': [10, 20, 30]
    }
    df = pd.DataFrame(data)
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        df.to_excel(tmp.name, index=False)
        yield tmp.name
    
    # Cleanup
    if os.path.exists(tmp.name):
        os.remove(tmp.name)


def test_upload_files_success(client, sample_xlsx_file):
    """Test successful file upload."""
    with open(sample_xlsx_file, 'rb') as f:
        response = client.post(
            '/api/upload',
            data={'files': (f, 'test.xlsx')},
            content_type='multipart/form-data'
        )
    
    assert response.status_code == 200
    data = response.get_json()
    assert 'files' in data
    assert len(data['files']) == 1
    assert data['files'][0]['original_name'] == 'test.xlsx'
    assert data['files'][0]['status'] == 'uploaded'


def test_upload_files_no_files(client):
    """Test upload with no files."""
    response = client.post('/api/upload')
    
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data


def test_upload_files_invalid_extension(client):
    """Test upload with invalid file extension."""
    # Create a temporary text file
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp:
        tmp.write(b'test content')
        tmp_path = tmp.name
    
    try:
        with open(tmp_path, 'rb') as f:
            response = client.post(
                '/api/upload',
                data={'files': (f, 'test.txt')},
                content_type='multipart/form-data'
            )
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'not allowed' in data['error'].lower()
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_get_all_files_status_empty(client):
    """Test getting status when no files are uploaded."""
    response = client.get('/api/status')
    
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)
    assert len(data) == 0


def test_get_file_status_not_found(client):
    """Test getting status for non-existent file."""
    response = client.get('/api/status/nonexistent')
    
    assert response.status_code == 404
    data = response.get_json()
    assert 'error' in data


def test_process_file_not_found(client):
    """Test processing non-existent file."""
    response = client.post('/api/process/nonexistent')
    
    assert response.status_code == 404
    data = response.get_json()
    assert 'error' in data


def test_remove_duplicates_not_found(client):
    """Test removing duplicates for non-existent file."""
    response = client.post('/api/remove-duplicates/nonexistent')
    
    assert response.status_code == 404
    data = response.get_json()
    assert 'error' in data


def test_export_file_not_found(client):
    """Test exporting non-existent file."""
    response = client.post('/api/export/nonexistent')
    
    assert response.status_code == 404
    data = response.get_json()
    assert 'error' in data


def test_download_file_not_found(client):
    """Test downloading non-existent file."""
    response = client.get('/api/download/nonexistent')
    
    assert response.status_code == 404
    data = response.get_json()
    assert 'error' in data


def test_cleanup_file_not_found(client):
    """Test cleaning up non-existent file."""
    response = client.delete('/api/cleanup/nonexistent')
    
    assert response.status_code == 404
    data = response.get_json()
    assert 'error' in data


# Integration test for the complete workflow
def test_complete_workflow(client, sample_xlsx_file):
    """Test the complete file processing workflow."""
    # 1. Upload file
    with open(sample_xlsx_file, 'rb') as f:
        upload_response = client.post(
            '/api/upload',
            data={'files': (f, 'test.xlsx')},
            content_type='multipart/form-data'
        )
    
    assert upload_response.status_code == 200
    upload_data = upload_response.get_json()
    file_id = upload_data['files'][0]['id']
    
    # 2. Check status after upload
    status_response = client.get(f'/api/status/{file_id}')
    assert status_response.status_code == 200
    status_data = status_response.get_json()
    assert not status_data['processed']
    assert not status_data['duplicates_removed']
    assert not status_data['exported']
    
    # 3. Process file
    process_response = client.post(f'/api/process/{file_id}')
    assert process_response.status_code == 200
    
    # 4. Check status after processing
    status_response = client.get(f'/api/status/{file_id}')
    assert status_response.status_code == 200
    status_data = status_response.get_json()
    assert status_data['processed']
    assert not status_data['duplicates_removed']
    assert not status_data['exported']
    
    # 5. Remove duplicates
    duplicates_response = client.post(f'/api/remove-duplicates/{file_id}')
    assert duplicates_response.status_code == 200
    
    # 6. Export file
    export_response = client.post(f'/api/export/{file_id}')
    assert export_response.status_code == 200
    export_data = export_response.get_json()
    assert 'download_url' in export_data
    
    # 7. Check final status
    status_response = client.get(f'/api/status/{file_id}')
    assert status_response.status_code == 200
    status_data = status_response.get_json()
    assert status_data['processed']
    assert status_data['duplicates_removed']
    assert status_data['exported']
    assert 'download_url' in status_data
    
    # 8. Download file
    download_response = client.get(f'/api/download/{file_id}')
    assert download_response.status_code == 200
    assert download_response.headers['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    
    # 9. Cleanup
    cleanup_response = client.delete(f'/api/cleanup/{file_id}')
    assert cleanup_response.status_code == 200
    
    # 10. Verify file is gone
    status_response = client.get(f'/api/status/{file_id}')
    assert status_response.status_code == 404
