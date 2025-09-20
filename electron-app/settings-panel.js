/**
 * Simple Settings Panel Component
 *
 * Adds basic API key status and manage button to the settings modal.
 */

class SettingsPanel {
    constructor() {
        this.modal = null;
        this.isInitialized = false;
        this.init();
    }

    init() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.initialize());
        } else {
            this.initialize();
        }
    }

    async initialize() {
        this.modal = document.getElementById('settings-modal');
        if (!this.modal) {
            return;
        }

        this.addAPIKeySection();
        this.bindEvents();
        this.isInitialized = true;
    }

    addAPIKeySection() {
        const modalBody = this.modal.querySelector('.modal-body');
        if (!modalBody) {
            return;
        }

        const apiKeySectionHTML = `
            <div class="setting-group api-key-simple">
                <h3>🔑 API Key</h3>
                <div class="api-key-status-row">
                    <div class="status-info">
                        <span id="simple-status-indicator">⏳</span>
                        <span id="simple-status-text">Checking...</span>
                    </div>
                    <div class="api-key-actions">
                        <button id="manage-api-key-btn" class="btn btn-primary">Manage API Key</button>
                        <button id="delete-api-key-btn" class="btn btn-danger" style="display: none;">Delete</button>
                    </div>
                </div>
                <div id="simple-status-source" class="status-source" style="display: none;">
                    Source: <span id="simple-source-text">-</span>
                </div>
            </div>
        `;

        const firstSettingGroup = modalBody.querySelector('.setting-group');
        if (firstSettingGroup) {
            firstSettingGroup.insertAdjacentHTML('beforebegin', apiKeySectionHTML);
        } else {
            modalBody.insertAdjacentHTML('afterbegin', apiKeySectionHTML);
        }

        this.getElements();
    }

    getElements() {
        this.elements = {
            statusIndicator: document.getElementById('simple-status-indicator'),
            statusText: document.getElementById('simple-status-text'),
            sourceDiv: document.getElementById('simple-status-source'),
            sourceText: document.getElementById('simple-source-text'),
            manageBtn: document.getElementById('manage-api-key-btn'),
            deleteBtn: document.getElementById('delete-api-key-btn')
        };
    }

    bindEvents() {
        if (!this.elements) return;

        this.elements.manageBtn?.addEventListener('click', () => {
            this.showAPIKeyModal();
        });

        this.elements.deleteBtn?.addEventListener('click', () => {
            this.confirmDeleteKey();
        });

        const settingsButton = document.getElementById('settings-button');
        settingsButton?.addEventListener('click', () => {
            setTimeout(() => this.refreshStatus(), 100);
        });
    }

    async refreshStatus() {
        if (!this.elements) return;

        try {
            this.elements.statusIndicator.textContent = '⏳';
            this.elements.statusText.textContent = 'Checking...';
            this.elements.sourceDiv.style.display = 'none';

            const response = await window.httpClient.get(SERVER_CONFIG.ENDPOINTS.API_KEY_STATUS);
            this.updateStatus(response);
        } catch (error) {
            this.showError();
        }
    }

    updateStatus(statusData) {
        if (!this.elements || !statusData) return;

        const { has_key, source } = statusData;

        if (has_key) {
            this.elements.statusIndicator.textContent = '✅';
            this.elements.statusText.textContent = 'Active';
            this.elements.sourceText.textContent = this.formatSource(source);
            this.elements.sourceDiv.style.display = 'block';
            this.elements.deleteBtn.style.display = 'inline-block';
        } else {
            this.elements.statusIndicator.textContent = '⚠️';
            this.elements.statusText.textContent = 'Not configured';
            this.elements.sourceDiv.style.display = 'none';
            this.elements.deleteBtn.style.display = 'none';
        }
    }

    formatSource(source) {
        const sourceMap = {
            environment: 'environment variable',
            keychain: 'system keychain',
            encrypted_file: 'encrypted file',
            none: 'nowhere'
        };
        return sourceMap[source] || source;
    }

    showError() {
        if (!this.elements) return;
        this.elements.statusIndicator.textContent = '❌';
        this.elements.statusText.textContent = 'Error checking status';
        this.elements.sourceDiv.style.display = 'none';
        this.elements.deleteBtn.style.display = 'none';
    }

    showAPIKeyModal() {
        if (!window.apiKeyModal) {
            window.apiKeyModal = new APIKeyModal();
        }

        const hasKey = this.elements.statusText?.textContent === 'Active';

        window.apiKeyModal.show({
            isUpdating: hasKey,
            onSuccess: (result) => {
                const action = result.isUpdate ? 'updated' : 'saved';
                if (window.showToast) {
                    window.showToast(`API key ${action} successfully`, 'success');
                }

                // Refresh settings panel status
                this.refreshStatus();

                // Comprehensive refresh logic similar to startup-flow.js
                // Update main app UI components
                if (window.app) {
                    // Update UI for API key presence
                    window.app.updateUIForAPIKey(true);

                    // Create session if app exists and has createSession method
                    if (typeof window.app.createSession === 'function') {
                        window.app.createSession().then(() => {
                            window.app.updateConnectionStatus(true);
                            // Force refresh status to check API key
                            if (typeof window.app.forceRefreshStatus === 'function') {
                                window.app.forceRefreshStatus();
                            }
                        }).catch(error => {
                            console.error('Failed to create session after API key setup:', error);
                            // Even if session creation fails, try to update connection status
                            if (typeof window.app.updateConnectionStatus === 'function') {
                                window.app.updateConnectionStatus(true);
                            }
                            // Force refresh status to check API key
                            if (typeof window.app.forceRefreshStatus === 'function') {
                                window.app.forceRefreshStatus();
                            }
                        });
                    } else {
                        // If createSession is not available, just update connection
                        if (typeof window.app.updateConnectionStatus === 'function') {
                            window.app.updateConnectionStatus(true);
                        }
                        // Force refresh status to check API key
                        if (typeof window.app.forceRefreshStatus === 'function') {
                            window.app.forceRefreshStatus();
                        }
                    }
                }

                // Update startup flow components if they exist
                if (window.startupFlow && typeof window.startupFlow.updateUIForAPIKey === 'function') {
                    window.startupFlow.updateUIForAPIKey(true);
                    // Also trigger a check to refresh startup flow status
                    setTimeout(() => {
                        if (typeof window.startupFlow.checkStartupAPIKey === 'function') {
                            window.startupFlow.checkStartupAPIKey();
                        }
                    }, 1000);
                }

                // Update API key status components if they exist
                if (window.apiKeyStatus && typeof window.apiKeyStatus.forceRefresh === 'function') {
                    setTimeout(() => {
                        window.apiKeyStatus.forceRefresh();
                    }, 500);
                }

                // Additional immediate refresh
                if (window.app && typeof window.app.forceRefreshStatus === 'function') {
                    setTimeout(() => window.app.forceRefreshStatus(), 1000);
                }
            },
            onCancel: () => {
                // User cancelled
            }
        });
    }

    onSettingsOpened() {
        if (this.isInitialized) {
            this.refreshStatus();
        }
    }

    confirmDeleteKey() {
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
            if (window.showToast) {
                window.showToast('Deleting API key...', 'info');
            }

            const response = await window.httpClient.delete(SERVER_CONFIG.ENDPOINTS.API_KEY_MANAGE);

            if (response.success) {
                if (window.showToast) {
                    window.showToast('API key deleted successfully', 'success');
                }
                this.refreshStatus();
            } else {
                if (window.showToast) {
                    window.showToast(response.message || 'Failed to delete API key', 'error');
                }
            }
        } catch (error) {
            console.error('Delete API key error:', error);
            if (window.showToast) {
                window.showToast('Failed to delete API key: ' + error.message, 'error');
            }
        }
    }
}

// Export for use in other modules
window.SettingsPanel = SettingsPanel;

// Auto-initialize the settings panel
document.addEventListener('DOMContentLoaded', () => {
    window.settingsPanel = new SettingsPanel();
});