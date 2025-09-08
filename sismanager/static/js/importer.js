// Importer JavaScript functionality

class ImporterApp {
    constructor() {
        this.files = new Map(); // Store files with their status
        this.isProcessing = false;
        this.processedFiles = [];
        
        this.initializeElements();
        this.attachEventListeners();
    }

    initializeElements() {
        // Main elements
        this.dropZone = document.getElementById('dropZone');
        this.fileInput = document.getElementById('fileInput');
        this.browseBtn = document.getElementById('browseBtn');
        this.fileListSection = document.getElementById('fileListSection');
        this.fileList = document.getElementById('fileList');
        
        // Buttons
        this.processBtn = document.getElementById('processBtn');
        this.clearBtn = document.getElementById('clearBtn');
        this.removeDuplicatesBtn = document.getElementById('removeDuplicatesBtn');
        this.exportBtn = document.getElementById('exportBtn');
        
        // Status elements
        this.processingStatus = document.getElementById('processingStatus');
        this.postProcessActions = document.getElementById('postProcessActions');
        this.processedCount = document.getElementById('processedCount');
        this.totalCount = document.getElementById('totalCount');
        this.progressFill = document.getElementById('progressFill');
        
        // Messages
        this.messages = document.getElementById('messages');
    }

    attachEventListeners() {
        // File input events
        this.dropZone.addEventListener('click', () => this.fileInput.click());
        this.browseBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.fileInput.click();
        });
        this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));

        // Drag and drop events
        this.dropZone.addEventListener('dragover', (e) => this.handleDragOver(e));
        this.dropZone.addEventListener('dragleave', (e) => this.handleDragLeave(e));
        this.dropZone.addEventListener('drop', (e) => this.handleDrop(e));

        // Button events
        this.processBtn.addEventListener('click', () => this.processFiles());
        this.clearBtn.addEventListener('click', () => this.clearFiles());
        this.removeDuplicatesBtn.addEventListener('click', () => this.removeDuplicates());
        this.exportBtn.addEventListener('click', () => this.exportData());
    }

    // Drag and Drop Handlers
    handleDragOver(e) {
        e.preventDefault();
        this.dropZone.classList.add('dragover');
    }

    handleDragLeave(e) {
        e.preventDefault();
        this.dropZone.classList.remove('dragover');
    }

    handleDrop(e) {
        e.preventDefault();
        this.dropZone.classList.remove('dragover');
        
        const files = Array.from(e.dataTransfer.files);
        this.addFiles(files);
    }

    handleFileSelect(e) {
        const files = Array.from(e.target.files);
        this.addFiles(files);
    }

    // File Management
    addFiles(files) {
        let validFiles = files.filter(file => this.isValidFile(file));
        
        if (validFiles.length === 0) {
            this.showMessage('No valid XLSX files selected.', 'warning');
            return;
        }

        validFiles.forEach(file => {
            if (!this.files.has(file.name)) {
                this.files.set(file.name, {
                    file: file,
                    status: 'pending',
                    id: Date.now() + Math.random()
                });
            }
        });

        this.renderFileList();
        this.updateButtonStates();
    }

    isValidFile(file) {
        const validTypes = [
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-excel'
        ];
        const validExtensions = ['.xlsx', '.xls'];
        
        return validTypes.includes(file.type) || 
               validExtensions.some(ext => file.name.toLowerCase().endsWith(ext));
    }

    renderFileList() {
        if (this.files.size === 0) {
            this.fileListSection.style.display = 'none';
            return;
        }

        this.fileListSection.style.display = 'block';
        this.fileList.innerHTML = '';

        this.files.forEach((fileData, fileName) => {
            const fileItem = this.createFileItem(fileName, fileData);
            this.fileList.appendChild(fileItem);
        });
    }

    createFileItem(fileName, fileData) {
        const item = document.createElement('div');
        item.className = 'file-item';
        item.innerHTML = `
            <div class="file-info">
                <span class="file-icon">📊</span>
                <div class="file-details">
                    <h4>${fileName}</h4>
                    <p>${this.formatFileSize(fileData.file.size)}</p>
                </div>
            </div>
            <div class="file-status">
                <span class="status-badge status-${fileData.status}">${fileData.status}</span>
                <button class="file-remove" onclick="importer.removeFile('${fileName}')">✕</button>
            </div>
        `;
        return item;
    }

    removeFile(fileName) {
        this.files.delete(fileName);
        this.renderFileList();
        this.updateButtonStates();
    }

    clearFiles() {
        this.files.clear();
        this.renderFileList();
        this.updateButtonStates();
        this.hideProcessingStatus();
        this.hidePostProcessActions();
        this.fileInput.value = '';
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // Processing Functions
    async processFiles() {
        if (this.isProcessing || this.files.size === 0) return;

        this.isProcessing = true;
        this.setButtonLoading(this.processBtn, true);
        this.showProcessingStatus();
        
        const fileArray = Array.from(this.files.entries());
        this.totalCount.textContent = fileArray.length;
        this.processedCount.textContent = '0';
        this.progressFill.style.width = '0%';

        try {
            let processed = 0;
            
            for (const [fileName, fileData] of fileArray) {
                await this.processFile(fileName, fileData);
                processed++;
                this.processedCount.textContent = processed.toString();
                this.progressFill.style.width = `${(processed / fileArray.length) * 100}%`;
            }

            this.showMessage('All files processed successfully!', 'success');
            this.showPostProcessActions();
            
        } catch (error) {
            this.showMessage(`Processing failed: ${error.message}`, 'error');
        } finally {
            this.isProcessing = false;
            this.setButtonLoading(this.processBtn, false);
            this.updateButtonStates();
        }
    }

    async processFile(fileName, fileData) {
        // Update status
        fileData.status = 'processing';
        this.renderFileList();

        const formData = new FormData();
        formData.append('files', fileData.file);

        try {
            const response = await fetch('/importer/api/upload', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (response.ok && result.success) {
                fileData.status = 'success';
                this.processedFiles.push(fileName);
            } else {
                throw new Error(result.message || 'Upload failed');
            }
        } catch (error) {
            fileData.status = 'error';
            throw error;
        } finally {
            this.renderFileList();
        }
    }

    async removeDuplicates() {
        if (this.processedFiles.length === 0) {
            this.showMessage('No processed files to deduplicate.', 'warning');
            return;
        }

        this.setButtonLoading(this.removeDuplicatesBtn, true);

        try {
            const response = await fetch('/importer/api/remove-duplicates', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    mode: 'forceful' // or 'soft' for confirmation
                })
            });

            const result = await response.json();

            if (response.ok && result.success) {
                this.showMessage(`Removed ${result.removed_count} duplicate entries.`, 'success');
            } else {
                throw new Error(result.message || 'Deduplication failed');
            }
        } catch (error) {
            this.showMessage(`Deduplication failed: ${error.message}`, 'error');
        } finally {
            this.setButtonLoading(this.removeDuplicatesBtn, false);
        }
    }

    async exportData() {
        this.setButtonLoading(this.exportBtn, true);

        try {
            const response = await fetch('/importer/api/export', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    columns: ["orderCode", "idOrderPos", "descrizioneMateriale", "codiceMateriale"]
                })
            });

            if (response.ok) {
                // Handle file download
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = 'exported_data.xlsx';
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                
                this.showMessage('Data exported successfully!', 'success');
            } else {
                const result = await response.json();
                throw new Error(result.message || 'Export failed');
            }
        } catch (error) {
            this.showMessage(`Export failed: ${error.message}`, 'error');
        } finally {
            this.setButtonLoading(this.exportBtn, false);
        }
    }

    // UI Helper Functions
    updateButtonStates() {
        const hasFiles = this.files.size > 0;
        const hasProcessedFiles = this.processedFiles.length > 0;
        
        this.processBtn.disabled = !hasFiles || this.isProcessing;
        this.removeDuplicatesBtn.disabled = !hasProcessedFiles;
        this.exportBtn.disabled = !hasProcessedFiles;
    }

    setButtonLoading(button, loading) {
        const textSpan = button.querySelector('.btn-text');
        const spinner = button.querySelector('.btn-spinner');
        
        if (loading) {
            textSpan.style.display = 'none';
            spinner.style.display = 'inline';
            button.disabled = true;
        } else {
            textSpan.style.display = 'inline';
            spinner.style.display = 'none';
            button.disabled = false;
        }
    }

    showProcessingStatus() {
        this.processingStatus.style.display = 'block';
    }

    hideProcessingStatus() {
        this.processingStatus.style.display = 'none';
    }

    showPostProcessActions() {
        this.postProcessActions.style.display = 'block';
    }

    hidePostProcessActions() {
        this.postProcessActions.style.display = 'none';
    }

    showMessage(text, type = 'info', duration = 5000) {
        const message = document.createElement('div');
        message.className = `message message-${type}`;
        message.innerHTML = `
            <span>${text}</span>
            <button class="message-close" onclick="this.parentElement.remove()">✕</button>
        `;
        
        this.messages.appendChild(message);
        
        if (duration > 0) {
            setTimeout(() => {
                if (message.parentElement) {
                    message.remove();
                }
            }, duration);
        }
    }
}

// Initialize the application when the DOM is loaded
let importer;
document.addEventListener('DOMContentLoaded', () => {
    importer = new ImporterApp();
});
