/**
 * API Key Status Indicator Component
 *
 * Displays the current API key status, source, and provides management options.
 * Shows security indicators and allows users to update/delete keys.
 */

class APIKeyStatus {
    constructor() {
        this.statusData = null;
        this.refreshInterval = null;
        this.errorTimeout = null;
        this.elements = {};

        this.init();
    }

    init() {
        this.createStatusElement();
        this.bindEvents();
        this.startPeriodicRefresh();
    }

    createStatusElement() {
        // Find where to insert the status indicator (in the header controls)
        const headerControls = document.querySelector('.header-controls');
        if (!headerControls) {
            console.error('Header controls not found for API key status');
            return;
        }

        const statusHTML = `
            <div class="api-key-status" id="api-key-status" title="API Key Status">
                <div class="status-indicator" id="api-key-status-indicator">
                    <span class="status-icon" id="api-key-status-icon">🟡</span>
                </div>
                <div class="status-dropdown" id="api-key-status-dropdown" style="display: none;">
                    <div class="dropdown-content">
                        <div class="status-info">
                            <div class="info-section">
                                <div class="info-label">Status:</div>
                                <div class="info-value" id="key-status-value">Unknown</div>
                            </div>
                            <div class="info-section">
                                <div class="info-label">Source:</div>
                                <div class="info-value" id="key-source-value">Unknown</div>
                            </div>
                            <div class="info-section" id="masked-key-section" style="display: none;">
                                <div class="info-label">Key:</div>
                                <div class="info-value masked-key" id="masked-key-value">-</div>
                            </div>
                            <div class="info-section" id="storage-methods-section">
                                <div class="info-label">Storage:</div>
                                <div class="storage-methods" id="storage-methods-info">
                                    <div class="storage-method" id="keychain-status">
                                        <span class="method-icon">🔐</span>
                                        <span class="method-name">Keychain</span>
                                        <span class="method-status" data-method="keychain">Unknown</span>
                                    </div>
                                    <div class="storage-method" id="file-status">
                                        <span class="method-icon">📁</span>
                                        <span class="method-name">File</span>
                                        <span class="method-status" data-method="encrypted_file">Unknown</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="status-actions">
                            <button class="dropdown-action" id="update-key-action">
                                <span class="action-icon">✏️</span>
                                Update Key
                            </button>
                            <button class="dropdown-action" id="test-key-action">
                                <span class="action-icon">🧪</span>
                                Test Key
                            </button>
                            <button class="dropdown-action danger" id="delete-key-action">
                                <span class="action-icon">🗑️</span>
                                Delete Key
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Don't insert the status indicator - we'll use the unified one
        // Just store the HTML for the dropdown functionality
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = statusHTML;
        const dropdown = tempDiv.querySelector('.status-dropdown');

        // Insert just the dropdown before the settings button
        const settingsButton = document.getElementById('settings-button');
        if (settingsButton && dropdown) {
            settingsButton.insertAdjacentElement('beforebegin', dropdown);
        }

        // Get element references
        this.elements = {
            container: document.getElementById('api-key-status'),
            indicator: document.getElementById('api-key-status-indicator'),
            icon: document.getElementById('api-key-status-icon'),
            dropdown: document.getElementById('api-key-status-dropdown'),
            statusValue: document.getElementById('key-status-value'),
            sourceValue: document.getElementById('key-source-value'),
            maskedKeySection: document.getElementById('masked-key-section'),
            maskedKeyValue: document.getElementById('masked-key-value'),
            storageMethodsInfo: document.getElementById('storage-methods-info'),
            updateAction: document.getElementById('update-key-action'),
            testAction: document.getElementById('test-key-action'),
            deleteAction: document.getElementById('delete-key-action')
        };
    }

    bindEvents() {
        if (!this.elements.container) return;

        // Toggle dropdown on click
        this.elements.indicator.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggleDropdown();
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!this.elements.container.contains(e.target)) {
                this.hideDropdown();
            }
        });

        // Action buttons
        this.elements.updateAction?.addEventListener('click', () => {
            this.hideDropdown();
            this.showUpdateKeyModal();
        });

        this.elements.testAction?.addEventListener('click', () => {
            this.hideDropdown();
            this.testAPIKey();
        });

        this.elements.deleteAction?.addEventListener('click', () => {
            this.hideDropdown();
            this.confirmDeleteKey();
        });

        // Copy masked key on click
        this.elements.maskedKeyValue?.addEventListener('click', () => {
            this.copyMaskedKey();
        });
    }

    async refresh() {
        try {
            const response = await window.httpClient.get(SERVER_CONFIG.ENDPOINTS.API_KEY_STATUS);
            this.statusData = response;

            // Clear any error timeout since we succeeded
            if (this.errorTimeout) {
                clearTimeout(this.errorTimeout);
                this.errorTimeout = null;
            }

            this.updateDisplay();
        } catch (error) {
            console.error('Failed to get API key status:', error);
            this.showError();
        }
    }

    updateDisplay() {
        if (!this.statusData || !this.elements.container) return;

        const { has_key, source, masked_key, storage_status } = this.statusData;

        // Update main indicator - simple traffic light
        if (has_key) {
            this.elements.icon.textContent = '🟢';
            this.elements.indicator.className = 'status-indicator status-active';
            this.elements.container.title = `API Key Active (${source})`;
        } else {
            this.elements.icon.textContent = '🔴';
            this.elements.indicator.className = 'status-indicator status-missing';
            this.elements.container.title = 'No API Key configured';
        }

        // Update dropdown info
        this.elements.statusValue.textContent = has_key ? 'Active' : 'Missing';
        this.elements.statusValue.className = has_key ? 'status-active' : 'status-missing';

        this.elements.sourceValue.textContent = this.formatSource(source);

        // Show/hide masked key
        if (has_key && masked_key) {
            this.elements.maskedKeySection.style.display = 'block';
            this.elements.maskedKeyValue.textContent = masked_key;
            this.elements.maskedKeyValue.title = 'Click to copy';
        } else {
            this.elements.maskedKeySection.style.display = 'none';
        }

        // Update storage status
        this.updateStorageStatus(storage_status);

        // Update action button states
        this.updateActionButtons(has_key);
    }

    updateStorageStatus(storageStatus) {
        if (!storageStatus) return;

        // Update keychain status
        const keychainMethod = this.elements.storageMethodsInfo?.querySelector('[data-method="keychain"]');
        if (keychainMethod) {
            keychainMethod.textContent = this.formatStorageStatus(storageStatus.keychain);
            keychainMethod.className = `method-status status-${storageStatus.keychain?.available ? 'available' : 'unavailable'}`;
        }

        // Update file storage status
        const fileMethod = this.elements.storageMethodsInfo?.querySelector('[data-method="encrypted_file"]');
        if (fileMethod) {
            fileMethod.textContent = this.formatStorageStatus(storageStatus.encrypted_file);
            fileMethod.className = `method-status status-${storageStatus.encrypted_file?.available ? 'available' : 'unavailable'}`;
        }
    }

    updateActionButtons(hasKey) {
        // Update button text and enable/disable states
        if (this.elements.updateAction) {
            this.elements.updateAction.innerHTML = hasKey
                ? '<span class="action-icon">✏️</span>Update Key'
                : '<span class="action-icon">➕</span>Add Key';
        }

        if (this.elements.testAction) {
            this.elements.testAction.style.display = hasKey ? 'block' : 'none';
        }

        if (this.elements.deleteAction) {
            this.elements.deleteAction.style.display = hasKey ? 'block' : 'none';
        }
    }

    formatSource(source) {
        const sourceMap = {
            environment: 'Environment Variable',
            keychain: 'System Keychain',
            encrypted_file: 'Encrypted File',
            none: 'Not Configured'
        };
        return sourceMap[source] || source;
    }

    formatStorageStatus(status) {
        if (!status) return 'Unknown';
        if (status.available) {
            return status.has_key ? 'Has Key' : 'Available';
        }
        return 'Unavailable';
    }

    showError() {
        if (!this.elements.container) return;

        this.elements.icon.textContent = '🟡';
        this.elements.indicator.className = 'status-indicator status-error';
        this.elements.container.title = 'Error checking API key status';

        // Clear any existing error timeout
        if (this.errorTimeout) {
            clearTimeout(this.errorTimeout);
        }

        // Auto-clear error after 5 seconds and retry
        this.errorTimeout = setTimeout(() => {
            this.elements.icon.textContent = '🟡';
            this.elements.indicator.className = 'status-indicator';
            this.elements.container.title = 'API Key Status';

            // Retry the refresh after clearing the error
            this.refresh();
        }, 5000);
    }

    toggleDropdown() {
        const isVisible = this.elements.dropdown.style.display !== 'none';
        if (isVisible) {
            this.hideDropdown();
        } else {
            this.showDropdown();
        }
    }

    showDropdown() {
        // Refresh status before showing
        this.refresh();
        this.elements.dropdown.style.display = 'block';
    }

    hideDropdown() {
        this.elements.dropdown.style.display = 'none';
    }

    showUpdateKeyModal() {
        // Create or get the modal instance
        if (!window.apiKeyModal) {
            window.apiKeyModal = new APIKeyModal();
        }

        window.apiKeyModal.show({
            onSuccess: (result) => {
                this.showSuccessMessage(`API key ${this.statusData?.has_key ? 'updated' : 'saved'} successfully using ${result.method}`);
                this.refresh();
            },
            onCancel: () => {
                // User cancelled
            }
        });
    }

    async testAPIKey() {
        if (!this.statusData?.has_key) {
            this.showErrorMessage('No API key configured to test');
            return;
        }

        try {
            this.showInfoMessage('Testing API key...');

            // Test by making a simple request to the backend
            // The backend will use the stored key to make a test request
            const response = await window.httpClient.get(SERVER_CONFIG.ENDPOINTS.HEALTH);

            if (response) {
                this.showSuccessMessage('API key test successful');
            } else {
                this.showErrorMessage('API key test failed');
            }
        } catch (error) {
            console.error('API key test error:', error);
            this.showErrorMessage('API key test failed: ' + error.message);
        }
    }

    confirmDeleteKey() {
        if (!this.statusData?.has_key) {
            this.showErrorMessage('No API key to delete');
            return;
        }

        const confirmed = confirm(
            'Are you sure you want to delete the stored API key?\n\n' +
            'This will remove the key from all storage locations and you will need to enter it again to use the application.'
        );

        if (confirmed) {
            this.deleteAPIKey();
        }
    }

    async deleteAPIKey() {
        try {
            this.showInfoMessage('Deleting API key...');

            const response = await window.httpClient.delete(SERVER_CONFIG.ENDPOINTS.API_KEY_MANAGE);

            if (response.success) {
                this.showSuccessMessage('API key deleted successfully');
                this.refresh();
            } else {
                this.showErrorMessage(response.message || 'Failed to delete API key');
            }
        } catch (error) {
            console.error('Delete API key error:', error);
            this.showErrorMessage('Failed to delete API key: ' + error.message);
        }
    }

    async copyMaskedKey() {
        if (!this.statusData?.masked_key) return;

        try {
            const success = await window.utils.copyToClipboard(this.statusData.masked_key);
            if (success) {
                this.showInfoMessage('Masked key copied to clipboard');
            } else {
                this.showErrorMessage('Failed to copy to clipboard');
            }
        } catch (error) {
            console.error('Copy error:', error);
            this.showErrorMessage('Failed to copy to clipboard');
        }
    }

    startPeriodicRefresh() {
        // Initial refresh
        this.refresh();

        // Refresh every 30 seconds
        this.refreshInterval = setInterval(() => {
            this.refresh();
        }, 30000);
    }

    stopPeriodicRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    // Toast message helpers
    showSuccessMessage(message) {
        if (window.showToast) {
            window.showToast(message, 'success');
        }
    }

    showErrorMessage(message) {
        if (window.showToast) {
            window.showToast(message, 'error');
        } else {
            console.error('Error:', message);
        }
    }

    showInfoMessage(message) {
        if (window.showToast) {
            window.showToast(message, 'info');
        }
    }

    // Public method to trigger refresh
    forceRefresh() {
        return this.refresh();
    }

    // Cleanup method
    destroy() {
        this.stopPeriodicRefresh();
        if (this.elements.container) {
            this.elements.container.remove();
        }
    }
}

// Export for use in other modules
window.APIKeyStatus = APIKeyStatus;

// Disable the API key status indicator - using unified status instead
// window.apiKeyStatus = new APIKeyStatus();