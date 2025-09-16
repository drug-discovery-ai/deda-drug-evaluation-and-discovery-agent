/**
 * API Key Input Modal Component
 *
 * Provides a modal dialog for users to input, validate, and store their API keys.
 * Includes validation, help text, and integration with backend storage.
 */

class APIKeyModal {
    constructor() {
        this.modal = null;
        this.isVisible = false;
        this.onSuccess = null;
        this.onCancel = null;
        this.currentRequestId = null;
        this.isUpdating = false;

        this.init();
    }

    init() {
        this.createModal();
        this.bindEvents();
    }

    createModal() {
        // Create modal HTML structure
        const modalHTML = `
            <div class="modal-overlay api-key-modal-overlay" id="api-key-modal">
                <div class="modal-content api-key-modal-content">
                            <div class="modal-header">
                                <h3 id="api-key-modal-title">🔐 Configure API Key</h3>
                                <button class="modal-close" id="api-key-modal-close" aria-label="Close">×</button>
                            </div>
                    <div class="modal-body">
                        <div class="api-key-form">
                            <!-- Help Section -->
                            <div class="help-section">
                                <div class="help-icon">💡</div>
                                        <div class="help-content">
                                            <h4 id="api-key-help-title">API Key Required</h4>
                                            <p id="api-key-help-text">This application requires an OpenAI API key to function. Your key will be stored securely on your system.</p>
                                    <div class="help-links">
                                        <a href="#" class="help-link" id="openai-help-link">📖 How to get an OpenAI API key</a>
                                        <a href="#" class="help-link" id="security-help-link">🔒 Security information</a>
                                    </div>
                                </div>
                            </div>

                            <!-- API Key Input -->
                            <div class="form-group">
                                <label for="api-key-input">API Key *</label>
                                <div class="input-wrapper">
                                    <input
                                        type="password"
                                        id="api-key-input"
                                        placeholder="sk-..."
                                        class="api-key-input"
                                        autocomplete="off"
                                        spellcheck="false"
                                        aria-describedby="api-key-help"
                                    >
                                    <button type="button" class="toggle-visibility" id="toggle-api-key-visibility" aria-label="Toggle visibility">
                                        👁️
                                    </button>
                                </div>
                                <div class="input-help" id="api-key-help">
                                    Enter your OpenAI API key (starts with 'sk-')
                                </div>
                                <div class="input-error" id="api-key-error" role="alert"></div>
                            </div>

                            <!-- Storage Method Selection -->
                            <div class="form-group">
                                <label for="storage-method">Storage Method</label>
                                <select id="storage-method" class="storage-method-select">
                                    <option value="auto">Automatic (Recommended)</option>
                                    <option value="keychain">System Keychain</option>
                                    <option value="encrypted_file">Encrypted File</option>
                                </select>
                                <div class="input-help">
                                    <span id="storage-method-help">Automatically selects the most secure available method</span>
                                </div>
                            </div>

                            <!-- Validation Status -->
                            <div class="validation-status" id="validation-status" style="display: none;">
                                <div class="validation-icon" id="validation-icon"></div>
                                <div class="validation-message" id="validation-message"></div>
                            </div>

                            <!-- Security Notice -->
                            <div class="security-notice">
                                <div class="notice-icon">🔒</div>
                                <div class="notice-content">
                                    <strong>Security:</strong> Your API key will be stored securely using your system's built-in security features.
                                    It will never be transmitted except to OpenAI's API.
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="button button-secondary" id="api-key-cancel">
                            Cancel
                        </button>
                        <button type="button" class="button button-primary" id="api-key-save" disabled>
                            <span class="button-icon">💾</span>
                            <span class="button-text">Save API Key</span>
                        </button>
                    </div>
                </div>
            </div>
        `;

        // Add modal to DOM
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        this.modal = document.getElementById('api-key-modal');

        // Get element references
        this.elements = {
            input: document.getElementById('api-key-input'),
            toggleVisibility: document.getElementById('toggle-api-key-visibility'),
            storageMethod: document.getElementById('storage-method'),
            storageMethodHelp: document.getElementById('storage-method-help'),
            validationStatus: document.getElementById('validation-status'),
            validationIcon: document.getElementById('validation-icon'),
            validationMessage: document.getElementById('validation-message'),
            error: document.getElementById('api-key-error'),
            saveButton: document.getElementById('api-key-save'),
            cancelButton: document.getElementById('api-key-cancel'),
            closeButton: document.getElementById('api-key-modal-close'),
            openaiHelpLink: document.getElementById('openai-help-link'),
            securityHelpLink: document.getElementById('security-help-link'),
            modalTitle: document.getElementById('api-key-modal-title'),
            helpTitle: document.getElementById('api-key-help-title'),
            helpText: document.getElementById('api-key-help-text')
        };
    }

    bindEvents() {
        // Modal close events
        this.elements.closeButton.addEventListener('click', () => this.hide());
        this.elements.cancelButton.addEventListener('click', () => this.hide());

        // Click outside to close
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.hide();
            }
        });

        // ESC key to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isVisible) {
                this.hide();
            }
        });

        // API key input validation
        this.elements.input.addEventListener('input', window.utils.debounce(() => {
            this.validateInput();
        }, 300));

        this.elements.input.addEventListener('paste', () => {
            // Validate after paste
            setTimeout(() => this.validateInput(), 100);
        });

        // Toggle visibility
        this.elements.toggleVisibility.addEventListener('click', () => {
            this.togglePasswordVisibility();
        });

        // Storage method change
        this.elements.storageMethod.addEventListener('change', () => {
            this.updateStorageMethodHelp();
        });

        // Save button
        this.elements.saveButton.addEventListener('click', () => {
            this.saveAPIKey();
        });

        // Help links
        this.elements.openaiHelpLink.addEventListener('click', (e) => {
            e.preventDefault();
            this.showOpenAIHelp();
        });

        this.elements.securityHelpLink.addEventListener('click', (e) => {
            e.preventDefault();
            this.showSecurityHelp();
        });

        // Form submission on Enter
        this.elements.input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !this.elements.saveButton.disabled) {
                this.saveAPIKey();
            }
        });
    }

    show(options = {}) {
        this.onSuccess = options.onSuccess;
        this.onCancel = options.onCancel;
        this.isUpdating = options.isUpdating || false;

        // Update modal content based on mode
        if (this.isUpdating) {
            this.elements.modalTitle.textContent = '✏️ Update API Key';
            this.elements.helpTitle.textContent = 'Update API Key';
            this.elements.helpText.textContent = 'Enter your new OpenAI API key. This will replace the currently stored key.';
            this.elements.saveButton.innerHTML = '<span class="button-icon">✏️</span><span class="button-text">Update API Key</span>';
        } else {
            this.elements.modalTitle.textContent = '🔐 Configure API Key';
            this.elements.helpTitle.textContent = 'API Key Required';
            this.elements.helpText.textContent = 'This application requires an OpenAI API key to function. Your key will be stored securely on your system.';
            this.elements.saveButton.innerHTML = '<span class="button-icon">💾</span><span class="button-text">Save API Key</span>';
        }

        // Reset form
        this.resetForm();

        // Show modal
        this.modal.style.display = 'flex';
        this.isVisible = true;

        // Focus input
        setTimeout(() => {
            this.elements.input.focus();
        }, 100);

        // Update storage method help
        this.updateStorageMethodHelp();
    }

    hide() {
        this.modal.style.display = 'none';
        this.isVisible = false;

        if (this.onCancel) {
            this.onCancel();
        }

        // Cancel any pending validation
        if (this.currentRequestId) {
            this.currentRequestId = null;
        }
    }

    resetForm() {
        this.elements.input.value = '';
        this.elements.storageMethod.value = 'auto';
        this.elements.error.textContent = '';
        this.elements.error.style.display = 'none';
        this.elements.validationStatus.style.display = 'none';
        this.elements.saveButton.disabled = true;
        this.elements.input.type = 'password';
        this.elements.toggleVisibility.textContent = '👁️';
        this.elements.input.classList.remove('error', 'success');
    }

    async validateInput() {
        const apiKey = this.elements.input.value.trim();

        // Clear previous validation
        this.clearValidation();

        if (!apiKey) {
            this.elements.saveButton.disabled = true;
            return;
        }

        // Basic format check
        if (apiKey.length < 10) {
            this.showValidation(false, 'API key is too short');
            return;
        }

        if (!apiKey.startsWith('sk-')) {
            this.showValidation(false, 'API key should start with "sk-"');
            return;
        }

        // Advanced validation via backend
        try {
            this.showValidation('loading', 'Validating API key format...');

            const requestId = Date.now();
            this.currentRequestId = requestId;

            const response = await window.httpClient.post(SERVER_CONFIG.ENDPOINTS.API_KEY_VALIDATE, {
                api_key: apiKey
            });

            // Check if this is still the current request
            if (this.currentRequestId !== requestId) {
                return;
            }

            if (response.valid) {
                this.showValidation(true, `Valid ${response.format_type} API key`);
                this.elements.saveButton.disabled = false;

                // Show recommendations if any
                if (response.recommendations && response.recommendations.length > 0) {
                    this.showRecommendations(response.recommendations);
                }
            } else {
                this.showValidation(false, response.error_message || 'Invalid API key format');
            }

            // Show warnings if any
            if (response.warnings && response.warnings.length > 0) {
                this.showWarnings(response.warnings);
            }

        } catch (error) {
            console.error('API key validation error:', error);

            // Check if this is still the current request
            if (this.currentRequestId !== requestId) {
                return;
            }

            this.showValidation(false, 'Unable to validate API key. Please check your connection.');
        }
    }

    clearValidation() {
        this.elements.error.style.display = 'none';
        this.elements.validationStatus.style.display = 'none';
        this.elements.input.classList.remove('error', 'success');
    }

    showValidation(isValid, message) {
        this.elements.validationStatus.style.display = 'flex';

        if (isValid === 'loading') {
            this.elements.validationIcon.textContent = '⏳';
            this.elements.validationMessage.textContent = message;
            this.elements.input.classList.remove('error', 'success');
        } else if (isValid) {
            this.elements.validationIcon.textContent = '✅';
            this.elements.validationMessage.textContent = message;
            this.elements.input.classList.remove('error');
            this.elements.input.classList.add('success');
        } else {
            this.elements.validationIcon.textContent = '❌';
            this.elements.validationMessage.textContent = message;
            this.elements.input.classList.remove('success');
            this.elements.input.classList.add('error');
            this.elements.saveButton.disabled = true;
        }
    }

    showWarnings(warnings) {
        // Show warnings in a non-intrusive way
        warnings.forEach(warning => {
            console.warn('API Key Warning:', warning);
        });
    }

    showRecommendations(recommendations) {
        // TODO: show the recommendations in the UI
    }

    togglePasswordVisibility() {
        const isPassword = this.elements.input.type === 'password';
        this.elements.input.type = isPassword ? 'text' : 'password';
        this.elements.toggleVisibility.textContent = isPassword ? '🙈' : '👁️';
    }

    updateStorageMethodHelp() {
        const method = this.elements.storageMethod.value;
        const helpTexts = {
            auto: 'Automatically selects the most secure available method',
            keychain: 'Store in system keychain (most secure)',
            encrypted_file: 'Store in encrypted file (fallback option)'
        };

        this.elements.storageMethodHelp.textContent = helpTexts[method] || helpTexts.auto;
    }

    async saveAPIKey() {
        const apiKey = this.elements.input.value.trim();
        const storageMethod = this.elements.storageMethod.value;

        if (!apiKey) {
            this.showError('Please enter an API key');
            return;
        }

        try {
            // Disable save button and show loading
            this.elements.saveButton.disabled = true;
            const loadingText = this.isUpdating ? 'Updating...' : 'Saving...';
            const loadingIcon = this.isUpdating ? '✏️' : '⏳';
            this.elements.saveButton.innerHTML = `<span class="button-icon">${loadingIcon}</span><span class="button-text">${loadingText}</span>`;

            // Save to backend
            const requestData = {
                api_key: apiKey,
                preferred_method: storageMethod === 'auto' ? null : storageMethod
            };

            // Use PUT for updates, POST for new keys
            const method = this.isUpdating ? 'put' : 'post';
            const response = await window.httpClient[method](SERVER_CONFIG.ENDPOINTS.API_KEY_MANAGE, requestData);

            if (response.success) {
                // Success - hide modal and call success callback
                this.hide();

                if (this.onSuccess) {
                    this.onSuccess({
                        method: response.method_used,
                        message: response.message,
                        warnings: response.warnings,
                        isUpdate: this.isUpdating
                    });
                }
            } else {
                this.showError(response.message || 'Failed to save API key');
            }

        } catch (error) {
            console.error('Save API key error:', error);
            const errorText = this.isUpdating ? 'Failed to update API key. Please try again.' : 'Failed to save API key. Please try again.';
            this.showError(errorText);
        } finally {
            // Restore save button
            const buttonText = this.isUpdating ? 'Update API Key' : 'Save API Key';
            const buttonIcon = this.isUpdating ? '✏️' : '💾';
            this.elements.saveButton.innerHTML = `<span class="button-icon">${buttonIcon}</span><span class="button-text">${buttonText}</span>`;
            this.elements.saveButton.disabled = false;
        }
    }

    showError(message) {
        this.elements.error.textContent = message;
        this.elements.error.style.display = 'block';

        // Scroll error into view if needed
        this.elements.error.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    showOpenAIHelp() {
        // Open OpenAI API keys page in external browser
        if (window.electronAPI) {
            // This would be handled by the main process
        } else {
            window.open('https://platform.openai.com/api-keys', '_blank');
        }
    }

    showSecurityHelp() {
        // Show security information modal or tooltip
        const securityInfo = `
            Security Information:

            • Your API key is stored securely using your operating system's built-in security features
            • On macOS: Stored in Keychain
            • On Windows: Stored in Credential Manager
            • On Linux: Stored using Secret Service

            • Your API key is never transmitted except directly to OpenAI's servers
            • The key is encrypted if file storage is used as a fallback
            • You can update or delete your stored key at any time
        `;

        alert(securityInfo); // Could be replaced with a nicer modal
    }

    // Public method to pre-fill the modal (for editing existing keys)
    setAPIKey(maskedKey, storageMethod) {
        // Don't actually set the masked key, just update the storage method
        if (storageMethod) {
            this.elements.storageMethod.value = storageMethod;
            this.updateStorageMethodHelp();
        }
    }
}

// Export for use in other modules
window.APIKeyModal = APIKeyModal;