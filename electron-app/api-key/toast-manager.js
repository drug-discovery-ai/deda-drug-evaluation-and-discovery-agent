/**
 * Enhanced Toast Manager for API Key Operations
 *
 * Provides sophisticated toast notifications with support for different message types,
 * API key specific contexts, and actionable notifications.
 */

class ToastManager {
    constructor() {
        this.toasts = new Map();
        this.queue = [];
        this.maxVisible = 3;
        this.defaultDuration = {
            success: 4000,
            error: 6000,
            warning: 5000,
            info: 4000,
            apikey: 8000 // Longer for API key messages
        };

        this.init();
    }

    init() {
        this.createToastContainer();
        this.bindGlobalEvents();
    }

    createToastContainer() {
        // Check if container already exists
        let container = document.getElementById('enhanced-toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'enhanced-toast-container';
            container.className = 'enhanced-toast-container';
            document.body.appendChild(container);
        }
        this.container = container;
    }

    bindGlobalEvents() {
        // Close toasts on ESC key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.clearAll();
            }
        });
    }

    show(message, type = 'info', options = {}) {
        const toastId = this.generateId();
        const toast = this.createToast(toastId, message, type, options);

        // Add to queue if too many visible
        if (this.container.children.length >= this.maxVisible) {
            this.queue.push({ toastId, message, type, options });
            return toastId;
        }

        this.displayToast(toast);
        return toastId;
    }

    createToast(id, message, type, options) {
        const toast = document.createElement('div');
        toast.id = `toast-${id}`;
        toast.className = `enhanced-toast toast-${type}`;

        const iconMap = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️',
            apikey: '🔑'
        };

        const duration = options.duration || this.defaultDuration[type] || this.defaultDuration.info;
        const icon = options.icon || iconMap[type] || iconMap.info;
        const persistent = options.persistent || false;

        toast.innerHTML = `
            <div class="toast-content">
                <div class="toast-header">
                    <div class="toast-icon">${icon}</div>
                    <div class="toast-message">${this.sanitizeMessage(message)}</div>
                    <button class="toast-close" data-toast-id="${id}" aria-label="Close">×</button>
                </div>
                ${options.actions ? this.createActions(options.actions, id) : ''}
            </div>
            ${!persistent ? `<div class="toast-progress" style="animation-duration: ${duration}ms;"></div>` : ''}
        `;

        // Store toast info
        this.toasts.set(id, {
            element: toast,
            type,
            duration,
            persistent,
            timer: null
        });

        return toast;
    }

    createActions(actions, toastId) {
        const actionsHTML = actions.map(action => `
            <button class="toast-action" data-toast-id="${toastId}" data-action="${action.id}">
                ${action.icon ? `<span class="action-icon">${action.icon}</span>` : ''}
                <span class="action-text">${action.text}</span>
            </button>
        `).join('');

        return `<div class="toast-actions">${actionsHTML}</div>`;
    }

    displayToast(toast) {
        this.container.appendChild(toast);

        // Animate in
        requestAnimationFrame(() => {
            toast.classList.add('show');
        });

        // Bind events
        this.bindToastEvents(toast);

        // Auto-hide timer
        const toastInfo = this.toasts.get(this.getToastId(toast));
        if (toastInfo && !toastInfo.persistent) {
            toastInfo.timer = setTimeout(() => {
                this.hide(this.getToastId(toast));
            }, toastInfo.duration);
        } else if (toastInfo && toastInfo.persistent && toastInfo.type === 'error') {
            // Auto-clear persistent error toasts after 15 seconds
            toastInfo.timer = setTimeout(() => {
                this.hide(this.getToastId(toast));
            }, 15000);
        }

        // Process queue
        this.processQueue();
    }

    bindToastEvents(toast) {
        // Close button
        const closeBtn = toast.querySelector('.toast-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const toastId = e.currentTarget.dataset.toastId;
                if (toastId) {
                    this.hide(toastId);
                }
            });
        }

        // Action buttons
        const actionBtns = toast.querySelectorAll('.toast-action');
        actionBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const toastId = e.currentTarget.dataset.toastId;
                const actionId = e.currentTarget.dataset.action;
                this.handleAction(toastId, actionId);
            });
        });

        // Pause timer on hover
        toast.addEventListener('mouseenter', () => {
            const toastInfo = this.toasts.get(this.getToastId(toast));
            if (toastInfo?.timer) {
                clearTimeout(toastInfo.timer);
            }
        });

        // Resume timer on leave
        toast.addEventListener('mouseleave', () => {
            const toastInfo = this.toasts.get(this.getToastId(toast));
            if (toastInfo && !toastInfo.persistent) {
                toastInfo.timer = setTimeout(() => {
                    this.hide(this.getToastId(toast));
                }, 2000); // Shorter resume time
            }
        });
    }

    hide(toastId) {
        const toastInfo = this.toasts.get(toastId);
        if (!toastInfo) return;

        const toast = toastInfo.element;

        // Clear timer
        if (toastInfo.timer) {
            clearTimeout(toastInfo.timer);
        }

        // Animate out
        toast.classList.add('hide');

        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
            this.toasts.delete(toastId);
            this.processQueue();
        }, 300);
    }

    handleAction(toastId, actionId) {
        const toastInfo = this.toasts.get(toastId);
        if (!toastInfo) return;

        // Emit custom event for action handling
        const event = new CustomEvent('toastAction', {
            detail: { toastId, actionId }
        });
        document.dispatchEvent(event);

        // Hide toast after action (unless it's a non-dismissive action)
        if (!['retry', 'configure'].includes(actionId)) {
            this.hide(toastId);
        }
    }

    processQueue() {
        if (this.queue.length === 0) return;
        if (this.container.children.length >= this.maxVisible) return;

        const queued = this.queue.shift();
        const toast = this.createToast(queued.toastId, queued.message, queued.type, queued.options);
        this.displayToast(toast);
    }

    clearAll() {
        for (const [toastId] of this.toasts) {
            this.hide(toastId);
        }
        this.queue = [];
    }

    clearByType(type) {
        for (const [toastId, toastInfo] of this.toasts) {
            if (toastInfo.type === type) {
                this.hide(toastId);
            }
        }
    }

    getToastId(toastElement) {
        return toastElement.id.replace('toast-', '');
    }

    generateId() {
        return Date.now().toString(36) + Math.random().toString(36).substring(2);
    }

    sanitizeMessage(message) {
        const div = document.createElement('div');
        div.textContent = message;
        return div.innerHTML;
    }

    // API Key specific toast methods
    showAPIKeyRequired(context = 'general') {
        const messages = {
            general: 'API key required to continue. Please configure your OpenAI API key.',
            chat: 'API key required to send messages. Configure your OpenAI API key to start chatting.',
            startup: 'Welcome! Please configure your OpenAI API key to get started.'
        };

        return this.show(messages[context] || messages.general, 'apikey', {
            persistent: true,
            icon: '🔑',
            actions: [
                {
                    id: 'configure',
                    text: 'Configure Now',
                    icon: '⚙️'
                },
                {
                    id: 'learn-more',
                    text: 'Learn More',
                    icon: '📖'
                }
            ]
        });
    }

    showAPIKeySuccess(method) {
        const message = `API key saved successfully using ${method}. You're ready to go!`;
        return this.show(message, 'success', {
            icon: '🔑',
            duration: 5000
        });
    }

    showAPIKeyError(error, canRetry = false) {
        const actions = canRetry ? [
            {
                id: 'retry',
                text: 'Retry',
                icon: '🔄'
            },
            {
                id: 'configure',
                text: 'Reconfigure',
                icon: '⚙️'
            }
        ] : [
            {
                id: 'configure',
                text: 'Check Settings',
                icon: '⚙️'
            }
        ];

        return this.show(`API key error: ${error}`, 'error', {
            icon: '🔑',
            duration: 8000,
            actions
        });
    }

    showAPIKeyWarning(warning) {
        return this.show(`API key warning: ${warning}`, 'warning', {
            icon: '🔑',
            duration: 6000
        });
    }

    showAPIKeyValidation(isValid, message, recommendations = []) {
        if (isValid) {
            return this.show(`✓ ${message}`, 'success', {
                icon: '🔑',
                duration: 4000
            });
        } else {
            const actions = recommendations.length > 0 ? [
                {
                    id: 'view-recommendations',
                    text: 'View Tips',
                    icon: '💡'
                }
            ] : [];

            return this.show(`✗ ${message}`, 'error', {
                icon: '🔑',
                duration: 6000,
                actions
            });
        }
    }

    showConnectionError(retryCallback) {
        return this.show('Connection to backend failed. Check if the server is running.', 'error', {
            actions: [
                {
                    id: 'retry',
                    text: 'Retry',
                    icon: '🔄'
                },
                {
                    id: 'settings',
                    text: 'Settings',
                    icon: '⚙️'
                }
            ]
        });
    }

    // Update existing methods to use new toast system
    success(message, options = {}) {
        return this.show(message, 'success', options);
    }

    error(message, options = {}) {
        return this.show(message, 'error', options);
    }

    warning(message, options = {}) {
        return this.show(message, 'warning', options);
    }

    info(message, options = {}) {
        return this.show(message, 'info', options);
    }
}

// Global instance
window.toastManager = new ToastManager();

// Compatibility with existing toast system
window.showToast = (message, type = 'info', options = {}) => {
    return window.toastManager.show(message, type, options);
};

// Export for module use
window.ToastManager = ToastManager;