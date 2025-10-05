/**
 * Bioinformatics Chat Assistant - Frontend Logic
 * Handles UI interactions, session management, and backend communication
 */

class BioinformaticsChatApp {
    constructor() {
        // Configuration
        this.config = {
            serverUrl: SERVER_CONFIG.URL,
            maxRetries: 3,
            retryDelay: 1000,
            typingDelay: 100,
            autoScrollDelay: 100
        };

        // State
        this.sessionId = null;
        this.isConnected = false;
        this.isProcessing = false;
        this.messages = [];
        this.retryCount = 0;

        // DOM Elements
        this.elements = {};

        // Initialize when DOM is loaded
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.initialize());
        } else {
            this.initialize();
        }
    }

    /**
     * Initialize the application
     */
    async initialize() {
        try {
            this.bindElements();
            this.setupEventListeners();
            this.setupIPCListeners();
            this.showLoadingOverlay('Initializing application...');
            
            await this.initializeApp();
            
            this.hideLoadingOverlay();
        } catch (error) {
            this.error('Failed to initialize application:', error);
            this.hideLoadingOverlay();
            this.showError('Failed to initialize application. Please restart the app.');
        }
    }

    /**
     * Bind DOM elements
     */
    bindElements() {
        // Add platform-specific styling for macOS traffic light buttons
        const appHeader = document.querySelector('.app-header');
        if (window.electronAPI?.platform === 'darwin') {
            appHeader?.classList.add('macos');
        }

        this.elements = {
            // Main containers
            welcomeScreen: document.getElementById('welcome-screen'),
            chatMessages: document.getElementById('chat-messages'),
            loadingOverlay: document.getElementById('loading-overlay'),
            
            // Input elements
            messageInput: document.getElementById('message-input'),
            sendButton: document.getElementById('send-button'),
            charCounter: document.getElementById('char-counter'),
            
            // Status elements
            connectionStatus: document.getElementById('connection-status'),
            statusIndicator: document.getElementById('status-indicator'),
            
            // Typing indicator
            typingIndicator: document.getElementById('typing-indicator'),
            
            // Toast notifications (using toast manager now)
            errorToast: document.getElementById('error-toast'),
            errorMessage: document.getElementById('error-message'),
            errorClose: document.getElementById('error-close'),
            successToast: document.getElementById('success-toast'),
            successMessage: document.getElementById('success-message'),
            successClose: document.getElementById('success-close'),
            
            // Settings modal
            settingsButton: document.getElementById('settings-button'),
            settingsModal: document.getElementById('settings-modal'),
            settingsClose: document.getElementById('settings-close'),
            restartBackendButton: document.getElementById('restart-backend-button'),
            serverStatusDetail: document.getElementById('server-status-detail'),
            serverHost: document.getElementById('server-host'),
            serverPort: document.getElementById('server-port'),
            appVersion: document.getElementById('app-version'),
            appPlatform: document.getElementById('app-platform')
        };
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Input handling
        this.elements.messageInput.addEventListener('input', (e) => this.handleInputChange(e));
        this.elements.messageInput.addEventListener('keydown', (e) => this.handleKeyDown(e));
        this.elements.sendButton.addEventListener('click', () => this.sendMessage());

        // Toast close buttons
        if (this.elements.errorClose) {
            this.elements.errorClose.addEventListener('click', () => this.hideError());
        }
        if (this.elements.successClose) {
            this.elements.successClose.addEventListener('click', () => this.hideSuccess());
        }

        // Settings modal
        if (this.elements.settingsButton) {
            this.elements.settingsButton.addEventListener('click', () => this.showSettings());
        }

        if (this.elements.settingsClose) {
            this.elements.settingsClose.addEventListener('click', () => this.hideSettings());
        }

        if (this.elements.restartBackendButton) {
            this.elements.restartBackendButton.addEventListener('click', () => this.restartBackend());
        }

        // Modal overlay click to close
        if (this.elements.settingsModal) {
            this.elements.settingsModal.addEventListener('click', (e) => {
                if (e.target === this.elements.settingsModal) {
                    this.hideSettings();
                }
            });
        }

        // Note: Auto-hide timers are set when toasts are shown, not here
    }

    /**
     * Setup IPC listeners for main process communication
     */
    setupIPCListeners() {
        // Listen for error notifications from main process
        if (window.electronAPI?.onErrorNotification) {
            window.electronAPI.onErrorNotification((data) => {
                // Use toast manager for error notifications instead of native dialogs
                if (window.toastManager) {
                    window.toastManager.error(`${data.title}: ${data.message}`, {
                        duration: 8000,
                        persistent: false // Make sure it auto-dismisses
                    });
                } else {
                    // Fallback to basic error display
                    this.showError(`${data.title}: ${data.message}`);
                }
            });
        }
    }

    /**
     * Initialize application components
     */
    async initializeApp() {
        try {
            // Load app information
            await this.loadAppInfo();
            
            // Wait for backend to be ready
            await this.waitForBackend();

            // Update connection status - backend is ready
            this.updateConnectionStatus(true);

            // Try to create chat session (may fail if no API key)
            try {
                await this.createSession();
            } catch (error) {
                // Session creation failed (likely no API key), but backend is still connected
                this.log('Session creation failed:', error.message);
                // Don't throw - let the app continue with just backend connection
            }
            
            // Focus input
            this.elements.messageInput.focus();
        } catch (error) {
            this.error('Error in initializeApp:', error);
            throw error; // Re-throw to be caught by initialize()
        }
    }

    /**
     * Load application information
     */
    async loadAppInfo() {
        try {
            const version = await window.electronAPI.getAppVersion();
            const platform = window.electronAPI.platform;
            
            this.elements.appVersion.textContent = version;
            this.elements.appPlatform.textContent = platform;
            
            // Update server info
            const url = new URL(this.config.serverUrl);
            this.elements.serverHost.textContent = url.hostname;
            this.elements.serverPort.textContent = url.port || '80';
        } catch (error) {
            this.error('Failed to load app info:', error);
        }
    }

    /**
     * Wait for backend server to be ready
     */
    async waitForBackend(maxAttempts = 30) {
        this.setConnectingState();
        this.updateLoadingText('Waiting for backend server...');
        
        // Ensure httpClient is available
        if (!window.httpClient) {
            throw new Error('HTTP client not available - preload script may have failed');
        }
        
        for (let attempt = 1; attempt <= maxAttempts; attempt++) {
            try {
                const response = await window.httpClient.get(`${this.config.serverUrl}/health`);
                this.log('Health response:', response);
                
                // Check if response is healthy (response might be different than expected)
                if (response && (response.status === 'healthy' || response.healthy === true || response === 'OK')) {
                    this.log('Backend server is ready');
                    return;
                }
            } catch (error) {
                this.log(`Backend connection attempt ${attempt}/${maxAttempts} failed:`, error.message);
            }
            
            // Wait before next attempt
            await this.delay(2000);
            
            // Update loading text
            this.updateLoadingText(`Connecting to backend... (${attempt}/${maxAttempts})`);
        }
        
        throw new Error('Backend server is not responding');
    }

    /**
     * Create a new chat session
     */
    async createSession() {
        try {
            this.updateLoadingText('Creating chat session...');
            
            const payload = {
                verbose: window.electronAPI?.isDevelopment || false
            };
            
            
            const response = await window.httpClient.post(`${this.config.serverUrl}/sessions`, payload);
            
            this.sessionId = response.session_id;
        } catch (error) {
            this.error('Failed to create session:', error);
            throw error;
        }
    }

    /**
     * Handle input changes
     */
    handleInputChange(event) {
        const value = event.target.value;
        const length = value.length;
        const maxLength = parseInt(event.target.maxLength);
        
        // Update character counter
        this.elements.charCounter.textContent = `${length}/${maxLength}`;
        
        // Update send button state
        this.elements.sendButton.disabled = length === 0 || this.isProcessing;
        
        // Auto-resize textarea
        this.autoResizeTextarea(event.target);
    }

    /**
     * Handle key down events
     */
    handleKeyDown(event) {
        if (event.key === 'Enter') {
            if (event.shiftKey) {
                // Shift+Enter: new line (default behavior)
                return;
            } else {
                // Enter: send message
                event.preventDefault();
                this.sendMessage();
            }
        }
    }

    /**
     * Auto-resize textarea based on content
     */
    autoResizeTextarea(textarea) {
        textarea.style.height = 'auto';
        const newHeight = Math.min(textarea.scrollHeight, 120); // Max 120px
        textarea.style.height = newHeight + 'px';
    }

    /**
     * Send a message
     */
    async sendMessage() {
        const message = this.elements.messageInput.value.trim();
        
        if (!message || this.isProcessing || !this.sessionId) {
            return;
        }

        try {
            this.isProcessing = true;
            this.elements.sendButton.disabled = true;
            
            // Add user message to chat
            this.addMessage('user', message);
            
            // Clear input
            this.elements.messageInput.value = '';
            this.elements.charCounter.textContent = '0/2000';
            this.autoResizeTextarea(this.elements.messageInput);
            
            // Show typing indicator
            this.showTypingIndicator();
            
            // Send to backend
            const response = await this.sendMessageToBackend(message);
            
            // Hide typing indicator
            this.hideTypingIndicator();
            
            // Add assistant response
            this.addMessage('assistant', response.response);
            
            // Reset retry count on success
            this.retryCount = 0;
            
        } catch (error) {
            this.error('Failed to send message:', error);
            this.hideTypingIndicator();
            
            // Show error message
            this.showError('Failed to send message. Please try again.');
            
            // Restore message in input if it failed
            this.elements.messageInput.value = message;
            this.handleInputChange({ target: this.elements.messageInput });
            
        } finally {
            this.isProcessing = false;
            this.elements.sendButton.disabled = false;
            this.elements.messageInput.focus();
        }
    }

    /**
     * Send message to backend with retry logic
     */
    async sendMessageToBackend(message) {
        for (let attempt = 1; attempt <= this.config.maxRetries; attempt++) {
            try {
                return await window.httpClient.post(`${this.config.serverUrl}/chat`, {
                    session_id: this.sessionId,
                    message: message
                });
            } catch (error) {
                if (attempt === this.config.maxRetries) {
                    throw error;
                }
                
                this.log(`Send attempt ${attempt} failed, retrying...`);
                await this.delay(this.config.retryDelay * attempt);
            }
        }
    }

    /**
     * Add message to chat
     */
    addMessage(type, content, timestamp = new Date()) {
        const message = {
            type,
            content,
            timestamp
        };
        
        this.messages.push(message);
        
        // Hide welcome screen if this is the first message
        if (this.messages.length === 1) {
            this.elements.welcomeScreen.style.display = 'none';
            this.elements.chatMessages.classList.add('active');
        }
        
        // Create message element
        const messageElement = this.createMessageElement(message);
        this.elements.chatMessages.appendChild(messageElement);
        
        // Auto-scroll to bottom
        setTimeout(() => {
            this.scrollToBottom();
        }, this.config.autoScrollDelay);
    }

    /**
     * Create message DOM element
     */
    createMessageElement(message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${message.type}`;
        
        const avatar = message.type === 'user' ? '👤' : '🤖';
        
        messageDiv.innerHTML = `
            <div class="message-content">
                ${message.type === 'assistant' ? `<div class="avatar">${avatar}</div>` : ''}
                <div class="message-bubble">
                    ${this.formatMessageContent(message.content)}
                    <div class="message-actions">
                        <button class="action-button" onclick="app.copyMessage(this)" title="Copy message">
                            📋
                        </button>
                    </div>
                </div>
                ${message.type === 'user' ? `<div class="avatar">${avatar}</div>` : ''}
                <div class="message-timestamp">
                    ${window.utils.formatTimestamp(message.timestamp)}
                </div>
            </div>
        `;
        
        return messageDiv;
    }

    /**
     * Format message content with basic markdown support
     */
    formatMessageContent(content) {
        // Check if content contains HTML (plan messages)
        if (content.includes('<div') || content.includes('<span')) {
            // Return HTML as-is for plan messages
            return content;
        }
        // Otherwise escape and parse markdown for regular messages
        return window.utils.parseMarkdown(window.utils.escapeHtml(content));
    }

    /**
     * Copy message to clipboard
     */
    async copyMessage(button) {
        const messageBubble = button.closest('.message-bubble');
        const content = messageBubble.textContent.trim();
        
        try {
            const success = await window.utils.copyToClipboard(content);
            if (success) {
                this.showSuccess('Message copied to clipboard!');
                button.textContent = '✅';
                setTimeout(() => {
                    button.textContent = '📋';
                }, 2000);
            } else {
                throw new Error('Copy failed');
            }
        } catch (error) {
            this.error('Failed to copy message:', error);
            this.showError('Failed to copy message');
        }
    }

    /**
     * Show/hide typing indicator
     */
    showTypingIndicator() {
        this.elements.typingIndicator.classList.add('active');
        this.scrollToBottom();
    }

    hideTypingIndicator() {
        this.elements.typingIndicator.classList.remove('active');
    }

    /**
     * Scroll to bottom of chat
     */
    scrollToBottom() {
        this.elements.chatMessages.scrollTop = this.elements.chatMessages.scrollHeight;
    }

    /**
     * Update connection status
     */
    updateConnectionStatus(connected) {
        this.isConnected = connected;

        // Check overall system status (connection + API key)
        this.updateOverallStatus();
    }

    /**
     * Update overall system status based on connection and API key
     */
    async updateOverallStatus() {
        if (!this.isConnected) {
            // If not connected, show red
            this.elements.statusIndicator.className = 'status-indicator red';
            this.elements.statusIndicator.textContent = '';
            this.elements.connectionStatus.title = 'Disconnected';
            if (this.elements.serverStatusDetail) this.elements.serverStatusDetail.textContent = 'Disconnected';
            return;
        }

        // If connected, check API key status
        try {
            const apiKeyStatus = await window.httpClient.get(`${this.config.serverUrl}/api/key/status`);

            if (apiKeyStatus.has_key) {
                // Connected + API key = Green (fully ready)
                this.elements.statusIndicator.className = 'status-indicator green';
                this.elements.statusIndicator.textContent = '';
                this.elements.connectionStatus.title = 'Ready';
                if (this.elements.serverStatusDetail) this.elements.serverStatusDetail.textContent = 'Healthy';

                // Clear any existing error toasts when system is fully ready
                if (window.toastManager) {
                    window.toastManager.clearByType('error');
                }
            } else {
                // Connected but no API key = Yellow (partial)
                this.elements.statusIndicator.className = 'status-indicator yellow';
                this.elements.statusIndicator.textContent = '';
                this.elements.connectionStatus.title = 'Connected - API Key Required';
                if (this.elements.serverStatusDetail) this.elements.serverStatusDetail.textContent = 'API Key Missing';
            }
        } catch (error) {
            // Connected but can't check API key = Yellow (partial)
            this.elements.statusIndicator.className = 'status-indicator yellow';
            this.elements.statusIndicator.textContent = '';
            this.elements.connectionStatus.title = 'Connected - Status Unknown';
            if (this.elements.serverStatusDetail) this.elements.serverStatusDetail.textContent = 'Status Check Failed';
        }
    }

    /**
     * Set connecting state
     */
    setConnectingState() {
        this.elements.statusIndicator.className = 'status-indicator yellow';
        this.elements.statusIndicator.textContent = '';
        this.elements.connectionStatus.title = 'Connecting...';
    }

    /**
     * Force refresh overall status (called when API key is updated)
     */
    async forceRefreshStatus() {
        if (this.isConnected) {
            await this.updateOverallStatus();
        }
    }

    /**
     * Update UI elements based on API key status (for settings panel integration)
     */
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

    /**
     * Update welcome screen based on API key status
     */
    updateWelcomeScreen(hasKey = false, statusData = null) {
        const welcomeScreen = document.getElementById('welcome-screen');
        if (!welcomeScreen) return;

        if (!hasKey) {
            // Add API key setup prompt to welcome screen if not present
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

                // Bind click event to show API key modal
                const setupBtn = apiKeyPrompt.querySelector('.setup-api-key-btn');
                setupBtn?.addEventListener('click', () => this.showAPIKeyModal());
            }
        } else {
            // Remove API key prompt if it exists (API key is now available)
            const apiKeyPrompt = welcomeScreen.querySelector('.api-key-prompt');
            if (apiKeyPrompt) {
                apiKeyPrompt.remove();
            }
        }
    }

    /**
     * Show/hide loading overlay
     */
    showLoadingOverlay(text = 'Loading...') {
        this.elements.loadingOverlay.style.display = 'flex';
        this.updateLoadingText(text);
    }

    hideLoadingOverlay() {
        this.elements.loadingOverlay.style.display = 'none';
    }

    updateLoadingText(text) {
        const loadingText = this.elements.loadingOverlay.querySelector('.loading-text');
        if (loadingText) {
            loadingText.textContent = text;
        }
    }

    /**
     * Show/hide error toast
     */
    showError(message) {
        // Use toast manager for consistent error notifications
        if (window.toastManager) {
            window.toastManager.error(message, {
                duration: 8000,
                persistent: false // Make sure it auto-dismisses
            });
        } else {
            // Fallback to console if toast manager isn't available
            console.error('Error:', message);
        }
    }


    /**
     * Show/hide success toast
     */
    showSuccess(message) {
        this.elements.successMessage.textContent = message;
        this.elements.successToast.classList.add('show');
        
        // Auto-hide after 3 seconds
        setTimeout(() => this.hideSuccess(), 3000);
    }

    hideSuccess() {
        this.elements.successToast.classList.remove('show');
    }

    /**
     * Show/hide settings modal
     */
    async showSettings() {
        // Update server status
        try {
            const status = await window.electronAPI.getServerStatus();
            this.elements.serverStatusDetail.textContent = status.healthy ? 'Healthy' : 'Unhealthy';
        } catch (error) {
            this.elements.serverStatusDetail.textContent = 'Error';
        }

        // Notify settings panel that modal is opening (to refresh API key status)
        if (window.settingsPanel && typeof window.settingsPanel.onSettingsOpened === 'function') {
            window.settingsPanel.onSettingsOpened();
        }

        this.elements.settingsModal.classList.add('active');
    }

    hideSettings() {
        this.elements.settingsModal.classList.remove('active');
    }

    /**
     * Show API key modal
     */
    showAPIKeyModal() {
        // Create or get the modal instance
        if (!window.apiKeyModal) {
            window.apiKeyModal = new APIKeyModal();
        }

        window.apiKeyModal.show({
            onSuccess: (result) => {
                this.showSuccess(`API key saved successfully using ${result.method}`);

                // Force refresh the status after API key is saved
                setTimeout(() => {
                    if (typeof this.forceRefreshStatus === 'function') {
                        this.forceRefreshStatus();
                    }
                }, 500);
            },
            onCancel: () => {
                // User cancelled - no additional action needed
            }
        });
    }

    /**
     * Restart backend server
     */
    async restartBackend() {
        try {
            this.showLoadingOverlay('Restarting backend server...');
            
            const result = await window.electronAPI.restartBackend();
            
            if (result.success) {
                // Wait for backend to be ready
                await this.waitForBackend();
                
                // Create new session
                await this.createSession();
                
                this.updateConnectionStatus(true);
                this.showSuccess('Backend server restarted successfully');
            } else {
                throw new Error(result.error || 'Unknown error');
            }
        } catch (error) {
            this.error('Failed to restart backend:', error);
            this.showError('Failed to restart backend server');
            this.updateConnectionStatus(false);
        } finally {
            this.hideLoadingOverlay();
            this.hideSettings();
        }
    }

    /**
     * Cleanup on app close
     */
    async cleanup() {
        if (this.sessionId) {
            try {
                await window.httpClient.delete(`${this.config.serverUrl}/sessions/${this.sessionId}`);
                this.log('Session cleaned up successfully');
            } catch (error) {
                this.error('Failed to cleanup session:', error);
            }
        }
    }

    /**
     * Utility functions
     */
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    log(...args) {
        if (window.devTools) {
            window.devTools.log(...args);
        } else {
            console.log('[BioChatApp]', ...args);
        }
    }

    error(...args) {
        if (window.devTools) {
            window.devTools.error(...args);
        } else {
            console.error('[BioChatApp]', ...args);
        }
    }

}

// Initialize the application
const app = new BioinformaticsChatApp();

// Expose app globally for debugging and emergency cleanup
window.app = app;

// Global function to clear error banners (accessible via console)
window.clearErrorBanners = () => {
    if (window.toastManager) {
        window.toastManager.clearAll();
    }
    console.log('🧹 Cleared all error banners');
};

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    app.cleanup();
});

// Handle application focus/blur for connection monitoring
window.addEventListener('focus', async () => {
    if (app.sessionId) {
        try {
            const status = await window.electronAPI.getServerStatus();
            app.updateConnectionStatus(status.healthy);
        } catch (error) {
            app.updateConnectionStatus(false);
        }
    }
});

// Export app instance globally for access by other components
window.app = app;

// Global error handler (only log, don't show toasts unless critical)
window.addEventListener('error', (event) => {
    app.error('Global error:', event.error);
});

window.addEventListener('unhandledrejection', (event) => {
    app.error('Unhandled promise rejection:', event.reason);
});