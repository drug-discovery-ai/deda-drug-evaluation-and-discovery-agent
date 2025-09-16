/**
 * Startup API Key Flow Manager
 *
 * Handles the application startup flow for API key checking, prompting,
 * and initial configuration. Ensures users have a valid API key before
 * they can use the application features.
 */

class StartupFlow {
    constructor() {
        this.hasCheckedOnStartup = false;
        this.isFirstRun = false;
        this.startupPromise = null;
        this.retryCount = 0;
        this.maxRetries = 3;

        this.init();
    }

    init() {
        // Listen for DOM ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.start());
        } else {
            this.start();
        }

        // Listen for backend connection status
        this.setupConnectionListeners();
    }

    async start() {
        if (this.hasCheckedOnStartup) return;

        try {
            // Wait for essential components to be ready
            await this.waitForBackend();

            // Check API key status
            await this.checkStartupAPIKey();

            this.hasCheckedOnStartup = true;
        } catch (error) {
            console.error('Startup flow error:', error);
            this.handleStartupError(error);
        }
    }

    async waitForBackend(timeout = 30000) {
        const startTime = Date.now();

        while (Date.now() - startTime < timeout) {
            try {
                const status = await window.electronAPI?.getServerStatus();
                if (status?.healthy) {
                    return true;
                }
            } catch (error) {
                // Backend not ready yet
            }

            await this.sleep(1000);
        }

        throw new Error('Backend failed to start within timeout');
    }

    async checkStartupAPIKey() {
        try {
        // Use dynamic URL construction based on server configuration
            const response = await window.httpClient.get(SERVER_CONFIG.ENDPOINTS.API_KEY_STATUS);

            if (response.has_key) {
                this.handleAPIKeyFound(response);
            } else {
                this.handleAPIKeyMissing();
            }
        } catch (error) {
            console.error('Failed to check API key status:', error);
            this.handleAPIKeyCheckError(error);
        }
    }

    handleAPIKeyFound(statusData) {
        const { source, masked_key } = statusData;

        // Show success notification
        if (window.toastManager) {
            window.toastManager.show(
                `API key loaded from ${this.formatSource(source)}. Ready to start!`,
                'success',
                { 
                    duration: 3000,
                    icon: '🔑'
                }
            );
        }

        // Update UI elements
        this.updateUIForAPIKey(true, statusData);

        // Hide loading overlay if it exists
        this.hideLoadingOverlay();
    }

    handleAPIKeyMissing() {
        this.isFirstRun = true;

        // Show welcome message with API key prompt
        this.showWelcomePrompt();

        // Update UI elements
        this.updateUIForAPIKey(false);

        // Hide loading overlay
        this.hideLoadingOverlay();
    }

    handleAPIKeyCheckError(error) {
        console.error('API key check error:', error);

        if (window.toastManager) {
            window.toastManager.showConnectionError(() => {
                this.retryStartupCheck();
            });
        }

        // Still hide loading overlay but show error state
        this.hideLoadingOverlay();
        this.showErrorState();
    }

    showWelcomePrompt() {
        // Show a friendly welcome message for first-time users
        if (window.toastManager) {
            const toastId = window.toastManager.showAPIKeyRequired('startup');

            // Listen for toast actions
            document.addEventListener('toastAction', (e) => {
                if (e.detail.toastId === toastId) {
                    this.handleWelcomeAction(e.detail.actionId);
                }
            }, { once: true });
        }

        // Also update the welcome screen if it's visible
        this.updateWelcomeScreen();
    }

    handleWelcomeAction(actionId) {
        switch (actionId) {
            case 'configure':
                this.showAPIKeyModal();
                break;
            case 'learn-more':
                this.showAPIKeyHelp();
                break;
        }
    }

    showAPIKeyModal() {
        // Ensure modal component is loaded
        if (!window.apiKeyModal) {
            window.apiKeyModal = new APIKeyModal();
        }

        window.apiKeyModal.show({
            onSuccess: (result) => {
                // API key saved successfully
                if (window.toastManager) {
                    window.toastManager.showAPIKeySuccess(result.method);
                }

                // Update UI
                this.updateUIForAPIKey(true);

                // Re-check status to update all components and initialize main app
                setTimeout(() => {
                    this.checkStartupAPIKey();

                    // Update API key status components
                    if (window.apiKeyStatus && typeof window.apiKeyStatus.forceRefresh === 'function') {
                        window.apiKeyStatus.forceRefresh();
                    }

                    // Trigger main app session creation if app exists
                    if (window.app && typeof window.app.createSession === 'function') {
                        window.app.createSession().then(() => {
                            window.app.updateConnectionStatus(true);
                            // Force refresh status to check API key
                            if (typeof window.app.forceRefreshStatus === 'function') {
                                window.app.forceRefreshStatus();
                            }
                        }).catch(error => {
                            console.error('Failed to create session after API key setup:', error);
                            // Even if session creation fails, try to update connection status
                            if (window.app && typeof window.app.updateConnectionStatus === 'function') {
                                window.app.updateConnectionStatus(true);
                            }
                            // Force refresh status to check API key
                            if (window.app && typeof window.app.forceRefreshStatus === 'function') {
                                window.app.forceRefreshStatus();
                            }
                        });
                    } else if (window.app) {
                        // If app doesn't exist or createSession is not available, just update connection
                        if (typeof window.app.updateConnectionStatus === 'function') {
                            window.app.updateConnectionStatus(true);
                        }
                        // Force refresh status to check API key
                        if (typeof window.app.forceRefreshStatus === 'function') {
                            window.app.forceRefreshStatus();
                        }
                    }
                }, 2000); // Increase delay to ensure backend has processed the save

                // Also try immediate refresh
                if (window.app && typeof window.app.forceRefreshStatus === 'function') {
                    setTimeout(() => window.app.forceRefreshStatus(), 500);
                }
            },
            onCancel: () => {
                // User cancelled - show helpful message
                if (window.toastManager) {
                    window.toastManager.show(
                        'You can configure your API key anytime from the settings panel.',
                        'info',
                        { duration: 5000 }
                    );
                }
            }
        });
    }

    showAPIKeyHelp() {
        // Show help information about API keys
        const helpMessage = `
            OpenAI API Key Setup:

            1. Visit https://platform.openai.com/api-keys
            2. Sign in to your OpenAI account
            3. Click "Create new secret key"
            4. Copy the key (starts with 'sk-')
            5. Paste it in the configuration dialog

            Your API key is stored securely on your system and only used to communicate with OpenAI's servers.
        `;

        alert(helpMessage); // Could be replaced with a nicer modal

        // Show the configuration modal after help
        setTimeout(() => this.showAPIKeyModal(), 500);
    }

    updateUIForAPIKey(hasKey, statusData = null) {
        // Update various UI elements based on API key status

        // Update message input placeholder
        const messageInput = document.getElementById('message-input');
        if (messageInput) {
            if (hasKey) {
                messageInput.placeholder = 'Ask about proteins, sequences, molecular structures, or any bioinformatics question...';
                messageInput.disabled = false;
            } else {
                messageInput.placeholder = 'Configure your API key to start asking questions...';
                messageInput.disabled = true;
            }
        }

        // Update send button
        const sendButton = document.getElementById('send-button');
        if (sendButton) {
            sendButton.disabled = !hasKey || !messageInput?.value?.trim();
        }

        // Update welcome screen if visible
        this.updateWelcomeScreen(hasKey, statusData);
    }

    updateWelcomeScreen(hasKey = false, statusData = null) {
        const welcomeScreen = document.getElementById('welcome-screen');
        if (!welcomeScreen) return;

        if (!hasKey) {
            // Add API key setup prompt to welcome screen
            let apiKeyPrompt = welcomeScreen.querySelector('.api-key-prompt');
            if (!apiKeyPrompt) {
                apiKeyPrompt = document.createElement('div');
                apiKeyPrompt.className = 'api-key-prompt';
                apiKeyPrompt.innerHTML = `
                    <div class="prompt-content">
                        <div class="prompt-icon">🔑</div>
                        <h3>Get Started</h3>
                        <p>Configure your OpenAI API key to unlock the full power of this bioinformatics assistant.</p>
                        <button class="button button-primary setup-api-key-btn">
                            <span class="button-icon">⚙️</span>
                            <span class="button-text">Setup API Key</span>
                        </button>
                    </div>
                `;

                const welcomeContent = welcomeScreen.querySelector('.welcome-content');
                if (welcomeContent) {
                    welcomeContent.appendChild(apiKeyPrompt);
                }

                // Bind click event
                const setupBtn = apiKeyPrompt.querySelector('.setup-api-key-btn');
                setupBtn?.addEventListener('click', () => this.showAPIKeyModal());
            }
        } else {
            // Remove API key prompt if it exists
            const apiKeyPrompt = welcomeScreen.querySelector('.api-key-prompt');
            if (apiKeyPrompt) {
                apiKeyPrompt.remove();
            }
        }
    }

    hideLoadingOverlay() {
        const loadingOverlay = document.getElementById('loading-overlay');
        if (loadingOverlay) {
            loadingOverlay.style.display = 'none';
        }
    }

    showErrorState() {
        // Show error state in UI
        const connectionStatus = document.getElementById('connection-status');
        if (connectionStatus) {
            const statusIndicator = connectionStatus.querySelector('.status-indicator');
            const statusText = connectionStatus.querySelector('.status-text');

            if (statusIndicator) statusIndicator.style.backgroundColor = '#f44336';
            if (statusText) statusText.textContent = 'Connection Error';
        }
    }

    async retryStartupCheck() {
        if (this.retryCount >= this.maxRetries) {
            if (window.toastManager) {
                window.toastManager.show(
                    'Failed to connect to backend after multiple attempts. Please restart the application.',
                    'error',
                    { persistent: true }
                );
            }
            return;
        }

        this.retryCount++;

        try {
            await this.sleep(2000); // Wait before retry
            await this.checkStartupAPIKey();
        } catch (error) {
            console.error(`Startup retry ${this.retryCount} failed:`, error);
            this.handleStartupError(error);
        }
    }

    setupConnectionListeners() {
        // Listen for connection status changes
        setInterval(async () => {
            if (!this.hasCheckedOnStartup) return;

            try {
                const status = await window.electronAPI?.getServerStatus();
                if (!status?.healthy) {
                    this.handleConnectionLoss();
                }
            } catch (error) {
                this.handleConnectionLoss();
            }
        }, 10000); // Check every 10 seconds
    }

    handleConnectionLoss() {
        if (window.toastManager) {
            window.toastManager.show(
                'Connection to backend lost. Some features may not work properly.',
                'warning',
                { duration: 8000 }
            );
        }
    }

    formatSource(source) {
        const sourceMap = {
            environment: 'environment variable',
            keychain: 'system keychain',
            encrypted_file: 'encrypted file',
            none: 'configuration'
        };
        return sourceMap[source] || source;
    }

    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // Public method to manually trigger API key check
    async recheckAPIKey() {
        this.hasCheckedOnStartup = false;
        this.retryCount = 0;
        await this.start();
    }

    // Public method to handle API key requirement during operation
    handleAPIKeyRequired(context = 'general') {
        if (window.toastManager) {
            const toastId = window.toastManager.showAPIKeyRequired(context);

            document.addEventListener('toastAction', (e) => {
                if (e.detail.toastId === toastId) {
                    this.handleWelcomeAction(e.detail.actionId);
                }
            }, { once: true });
        }
    }
}

// Global API key requirement handler
window.onAPIKeyRequired = (error, retryCallback) => {
    if (window.startupFlow) {
        window.startupFlow.handleAPIKeyRequired('operation');
        return true; // Handled
    }
    return false; // Not handled
};

// Initialize startup flow
window.startupFlow = new StartupFlow();

// Export for module use
window.StartupFlow = StartupFlow;