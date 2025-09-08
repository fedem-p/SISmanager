"""
File management service for secure file storage and cleanup in SISmanager.
"""

import os
import shutil
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

from sismanager.config import logger, DATA_DIR


class FileManager:
    """Manages secure file storage, cleanup, and access control."""

    def __init__(self):
        """Initialize FileManager with secure directories."""
        self.upload_dir = Path(DATA_DIR) / "uploads"
        self.temp_dir = Path(DATA_DIR) / "temp"
        self.processed_dir = Path(DATA_DIR) / "processed"
        self.downloads_dir = Path(DATA_DIR) / "downloads"
        
        # Create directories with appropriate permissions
        self._ensure_directories()
        
        # File tracking
        self.active_files: Dict[str, Dict] = {}
        self._lock = threading.Lock()
        
        # Start cleanup scheduler
        self._start_cleanup_scheduler()

    def _ensure_directories(self):
        """Create necessary directories with secure permissions."""
        directories = [
            self.upload_dir,
            self.temp_dir,
            self.processed_dir,
            self.downloads_dir
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            # Set directory permissions to be readable/writable by owner only
            os.chmod(directory, 0o700)

    def store_uploaded_file(self, file, original_filename: str) -> Dict:
        """
        Securely store an uploaded file with UUID naming.
        
        Args:
            file: File object to store
            original_filename: Original name of the file
            
        Returns:
            Dict containing file metadata
        """
        # Generate unique filename
        file_id = str(uuid4())
        file_extension = Path(original_filename).suffix
        secure_filename = f"{file_id}{file_extension}"
        file_path = self.upload_dir / secure_filename
        
        try:
            # Save file securely
            file.save(str(file_path))
            
            # Set file permissions (owner read/write only)
            os.chmod(file_path, 0o600)
            
            # Track file metadata
            file_metadata = {
                'id': file_id,
                'original_name': original_filename,
                'filename': secure_filename,
                'file_path': str(file_path),
                'size': os.path.getsize(file_path),
                'upload_time': datetime.now().isoformat(),
                'status': 'uploaded',
                'last_accessed': datetime.now().isoformat()
            }
            
            with self._lock:
                self.active_files[file_id] = file_metadata
            
            logger.info(f"Stored file {original_filename} as {secure_filename}")
            return file_metadata
            
        except Exception as e:
            logger.error(f"Error storing file {original_filename}: {e}")
            # Clean up if file was partially created
            if file_path.exists():
                file_path.unlink()
            raise

    def get_file_info(self, file_id: str) -> Optional[Dict]:
        """Get file metadata by ID."""
        with self._lock:
            file_info = self.active_files.get(file_id)
            if file_info:
                # Update last accessed time
                file_info['last_accessed'] = datetime.now().isoformat()
            return file_info

    def get_file_path(self, file_id: str) -> Optional[Path]:
        """Get secure file path by ID."""
        file_info = self.get_file_info(file_id)
        if file_info and os.path.exists(file_info['file_path']):
            return Path(file_info['file_path'])
        return None

    def update_file_status(self, file_id: str, status: str, **kwargs):
        """Update file status and metadata."""
        with self._lock:
            if file_id in self.active_files:
                self.active_files[file_id]['status'] = status
                self.active_files[file_id]['last_accessed'] = datetime.now().isoformat()
                
                # Update additional metadata
                for key, value in kwargs.items():
                    self.active_files[file_id][key] = value

    def move_to_processed(self, file_id: str) -> Optional[Path]:
        """Move file from uploads to processed directory."""
        file_info = self.get_file_info(file_id)
        if not file_info:
            return None
            
        source_path = Path(file_info['file_path'])
        if not source_path.exists():
            return None
            
        # Create new path in processed directory
        processed_path = self.processed_dir / source_path.name
        
        try:
            shutil.move(str(source_path), str(processed_path))
            
            # Update file metadata
            with self._lock:
                self.active_files[file_id]['file_path'] = str(processed_path)
                self.active_files[file_id]['status'] = 'processed'
                self.active_files[file_id]['processed_time'] = datetime.now().isoformat()
            
            logger.info(f"Moved file {file_id} to processed directory")
            return processed_path
            
        except Exception as e:
            logger.error(f"Error moving file {file_id} to processed: {e}")
            return None

    def create_download_copy(self, file_id: str, download_filename: str) -> Optional[Path]:
        """Create a copy of processed file for download."""
        file_info = self.get_file_info(file_id)
        if not file_info or file_info['status'] != 'processed':
            return None
            
        source_path = Path(file_info['file_path'])
        if not source_path.exists():
            return None
        
        # Create download copy with clean filename
        download_id = str(uuid4())
        file_extension = Path(download_filename).suffix
        download_path = self.downloads_dir / f"{download_id}_{download_filename}"
        
        try:
            shutil.copy2(str(source_path), str(download_path))
            
            # Set appropriate permissions
            os.chmod(download_path, 0o600)
            
            # Track download file (with expiration)
            download_metadata = {
                'download_id': download_id,
                'original_file_id': file_id,
                'download_path': str(download_path),
                'filename': download_filename,
                'created_time': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(hours=1)).isoformat()
            }
            
            with self._lock:
                self.active_files[f"download_{download_id}"] = download_metadata
            
            logger.info(f"Created download copy for file {file_id}")
            return download_path
            
        except Exception as e:
            logger.error(f"Error creating download copy for {file_id}: {e}")
            return None

    def cleanup_file(self, file_id: str) -> bool:
        """Remove file and its metadata."""
        try:
            with self._lock:
                file_info = self.active_files.pop(file_id, None)
            
            if file_info:
                file_path = Path(file_info['file_path'])
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"Cleaned up file {file_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error cleaning up file {file_id}: {e}")
            return False

    def cleanup_expired_files(self):
        """Remove expired files and old uploads."""
        current_time = datetime.now()
        expired_files = []
        
        with self._lock:
            for file_id, file_info in self.active_files.items():
                # Remove files older than 24 hours if not processed
                last_accessed = datetime.fromisoformat(file_info['last_accessed'])
                age = current_time - last_accessed
                
                should_expire = False
                
                # Download files expire after 1 hour
                if file_id.startswith('download_'):
                    expires_at = datetime.fromisoformat(file_info.get('expires_at', current_time.isoformat()))
                    if current_time > expires_at:
                        should_expire = True
                
                # Uploaded files expire after 24 hours if not processed
                elif file_info['status'] == 'uploaded' and age > timedelta(hours=24):
                    should_expire = True
                
                # Processed files expire after 7 days
                elif file_info['status'] == 'processed' and age > timedelta(days=7):
                    should_expire = True
                
                if should_expire:
                    expired_files.append(file_id)
        
        # Clean up expired files
        for file_id in expired_files:
            self.cleanup_file(file_id)
            
        if expired_files:
            logger.info(f"Cleaned up {len(expired_files)} expired files")

    def get_file_stats(self) -> Dict:
        """Get statistics about managed files."""
        with self._lock:
            stats = {
                'total_files': len(self.active_files),
                'uploaded': 0,
                'processing': 0,
                'processed': 0,
                'downloads': 0,
                'total_size': 0
            }
            
            for file_info in self.active_files.values():
                status = file_info.get('status', 'unknown')
                if status in stats:
                    stats[status] += 1
                
                if 'download_' in file_info.get('id', ''):
                    stats['downloads'] += 1
                
                stats['total_size'] += file_info.get('size', 0)
            
            return stats

    def _start_cleanup_scheduler(self):
        """Start background cleanup scheduler."""
        def cleanup_worker():
            while True:
                try:
                    time.sleep(3600)  # Run every hour
                    self.cleanup_expired_files()
                except Exception as e:
                    logger.error(f"Error in cleanup scheduler: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
        logger.info("Started file cleanup scheduler")


# Global file manager instance
file_manager = FileManager()
