const { contextBridge, ipcRenderer } = require('electron');

// Simple UUID v4 generator (compatible with CommonJS)
function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

try {
    // Expose protected methods that allow the renderer process to use
    // the ipcRenderer without exposing the entire object
    contextBridge.exposeInMainWorld('electronAPI', {
        // Server status and health
        getServerStatus: () => ipcRenderer.invoke('get-server-status'),
        
        // Application version
        getAppVersion: () => ipcRenderer.invoke('get-app-version'),
        
        // Backend management
        restartBackend: () => ipcRenderer.invoke('restart-backend'),

        // API Key management
        checkAPIKeyStatus: () => ipcRenderer.invoke('check-api-key-status'),

        // Listen for error notifications from main process
        onErrorNotification: (callback) => {
            ipcRenderer.on('show-error-notification', (event, data) => callback(data));
        },

        // Platform information
        platform: process.platform,
        
        // Environment info (always ensure boolean)  
        isDevelopment: process.env.NODE_ENV === 'development' || process.defaultApp || /[\\/]electron-prebuilt[\\/]/.test(process.execPath) || /[\\/]electron[\\/]/.test(process.execPath)
    });
} catch (error) {
    console.error('Failed to expose electronAPI:', error);
}

try {
    // Expose a secure HTTP client for communicating with the Python backend
    contextBridge.exposeInMainWorld('httpClient', {
        // Make HTTP requests to the backend
        async request(url, options = {}) {
            try {
                let bodyString = undefined;
                if (options.body) {
                    bodyString = JSON.stringify(options.body);
                }
                
                // Extract body and other options separately to avoid override
                const { body: _, ...otherOptions } = options;
                
                const requestOptions = {
                    method: options.method || 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                        ...options.headers
                    },
                    body: bodyString,
                    ...otherOptions
                };
                
                
                const response = await fetch(url, requestOptions);

                if (!response.ok) {
                    const errorText = await response.text();
                    throw new Error(`HTTP ${response.status}: ${response.statusText} - ${errorText}`);
                }

                const contentType = response.headers.get('content-type');
                if (contentType && contentType.includes('application/json')) {
                    return await response.json();
                } else {
                    return await response.text();
                }
            } catch (error) {
                console.error('HTTP request failed:', error);
                throw error;
            }
        },

        // Convenience methods for common HTTP operations
        async get(url, options = {}) {
            return this.request(url, { ...options, method: 'GET' });
        },

        async post(url, data, options = {}) {
            return this.request(url, { 
                ...options, 
                method: 'POST', 
                body: data 
            });
        },

        async delete(url, options = {}) {
            return this.request(url, { ...options, method: 'DELETE' });
        },

        async put(url, data, options = {}) {
            return this.request(url, {
                ...options,
                method: 'PUT',
                body: data
            });
        },

        async checkApiKeyMissing(error) {
            // Check if error indicates missing API key
            if (error.message && (
                error.message.includes('API key') ||
                error.message.includes('unauthorized') ||
                error.message.includes('401')
            )) {
                return true;
            }
            return false;
        },

        async handleAPIKeyError(error, retryCallback) {
            // Handle API key related errors with user-friendly prompts
            const isAPIKeyError = await this.checkApiKeyMissing(error);

            if (isAPIKeyError) {
                // Notify the renderer about API key requirement
                if (window.onAPIKeyRequired) {
                    return window.onAPIKeyRequired(error, retryCallback);
                }
            }

            throw error;
        }
    });
} catch (error) {
    console.error('Failed to expose httpClient:', error);
}

try {
    // Expose utility functions
    contextBridge.exposeInMainWorld('utils', {
    // Generate UUID for session IDs (client-side backup)
    generateUUID() {
        return generateUUID();
    },

    // Format timestamp for display
    formatTimestamp(date = new Date()) {
        return date.toLocaleString();
    },

    // Copy text to clipboard
    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            return true;
        } catch (error) {
            console.error('Failed to copy to clipboard:', error);
            // Fallback method
            try {
                const textArea = document.createElement('textarea');
                textArea.value = text;
                textArea.style.position = 'fixed';
                textArea.style.left = '-999999px';
                textArea.style.top = '-999999px';
                document.body.appendChild(textArea);
                textArea.focus();
                textArea.select();
                const result = document.execCommand('copy');
                document.body.removeChild(textArea);
                return result;
            } catch (fallbackError) {
                console.error('Clipboard fallback failed:', fallbackError);
                return false;
            }
        }
    },

    // Debounce function for input handling
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    // Escape HTML to prevent XSS
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    // Parse markdown-like syntax for basic formatting
    parseMarkdown(text) {
        return text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
    }
    });
} catch (error) {
    console.error('Failed to expose utils:', error);
}

// Expose logging utilities (development only)
if (process.env.NODE_ENV === 'development') {
    contextBridge.exposeInMainWorld('devTools', {
        log: (...args) => console.log('[Renderer]', ...args),
        warn: (...args) => console.warn('[Renderer]', ...args),
        error: (...args) => console.error('[Renderer]', ...args),
        
        // Performance timing
        time: (label) => console.time(`[Renderer] ${label}`),
        timeEnd: (label) => console.timeEnd(`[Renderer] ${label}`)
    });
}

// Security: Prevent eval and Function constructor
window.eval = function() {
    throw new Error('eval() is disabled for security reasons');
};

window.Function = function() {
    throw new Error('Function constructor is disabled for security reasons');
};

