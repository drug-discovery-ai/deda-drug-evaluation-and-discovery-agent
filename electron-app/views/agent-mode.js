/**
 * Agent Mode functionality for plan-approve-execute workflow
 */

class AgentModeManager {
    constructor(app) {
        this.app = app;
        this.agentModeEnabled = false;
        this.currentPlanId = null;
        this.eventSource = null;

        // Bind DOM elements
        this.elements = {
            modeRadios: document.querySelectorAll('input[name="mode"]'),

            // Modify modal
            modifyModal: document.getElementById('modify-modal'),
            modificationInput: document.getElementById('modification-input'),
            submitModifications: document.getElementById('submit-modifications'),
            cancelModifications: document.getElementById('cancel-modifications')
        };

        this.setupEventListeners();
    }

    setupEventListeners() {
        // Listen to mode radio changes
        this.elements.modeRadios.forEach(radio => {
            radio.addEventListener('change', (e) => this.onModeChange(e.target.value));
        });

        // Modify modal
        this.elements.submitModifications.addEventListener('click', () => this.submitModifications());
        this.elements.cancelModifications.addEventListener('click', () => this.hideModifyModal());

        // Use event delegation for dynamically created plan action buttons
        document.addEventListener('click', (e) => {
            if (e.target.closest('.plan-approve-btn')) {
                const planId = e.target.closest('.plan-approve-btn').dataset.planId;
                this.approvePlan(planId);
            } else if (e.target.closest('.plan-reject-btn')) {
                const planId = e.target.closest('.plan-reject-btn').dataset.planId;
                this.rejectPlan(planId);
            } else if (e.target.closest('.plan-modify-btn')) {
                const planId = e.target.closest('.plan-modify-btn').dataset.planId;
                this.showModifyModal(planId);
            }
        });
    }

    onModeChange(mode) {
        this.agentModeEnabled = (mode === 'agent');
    }

    async sendMessage(message) {
        if (!this.app.sessionId) {
            console.error('No session ID available');
            return;
        }

        try {
            const response = await window.httpClient.post(`${this.app.config.serverUrl}/chat/agent`, {
                session_id: this.app.sessionId,
                message: message,
                agent_mode: true
            });

            this.currentPlanId = response.plan_id;
            this.displayPlanAsMessage(response);

        } catch (error) {
            console.error('Failed to create plan:', error);
            if (window.toastManager) {
                window.toastManager.error('Failed to create execution plan');
            }
        }
    }

    displayPlanAsMessage(plan) {
        // Create plan message HTML
        const planHTML = `
            <div class="plan-message" data-plan-id="${plan.plan_id}">
                <div class="plan-header">
                    <span class="plan-title">📋 Execution Plan</span>
                    <span class="plan-steps-count">${plan.steps.length} steps</span>
                </div>

                <div class="plan-steps-list">
                    ${plan.steps.map((step, index) => `
                        <div class="plan-step" data-step-index="${index}" data-status="pending">
                            <span class="step-icon">${this.getStatusIcon('pending')}</span>
                            <div class="step-content">
                                <div class="step-header">
                                    <span class="step-number">Step ${index + 1}</span>
                                    <span class="step-duration" style="display: none;"></span>
                                </div>
                                <div class="step-text">${this.escapeHtml(step)}</div>
                                <div class="step-tool">Tool: ${this.escapeHtml(plan.tool_calls[index])}</div>
                            </div>
                        </div>
                    `).join('')}
                </div>

                <div class="plan-actions">
                    <button class="plan-approve-btn" data-plan-id="${plan.plan_id}">
                        ✓ Approve & Execute
                    </button>
                    <button class="plan-reject-btn" data-plan-id="${plan.plan_id}">
                        ✗ Reject
                    </button>
                    <button class="plan-modify-btn" data-plan-id="${plan.plan_id}">
                        ✏ Modify
                    </button>
                </div>

                <div class="plan-progress" style="display: none;">
                    <div class="progress-info">
                        <span class="progress-text">Step 0 of ${plan.steps.length}</span>
                        <span class="progress-percentage">0%</span>
                    </div>
                    <progress class="progress-bar" max="100" value="0"></progress>
                </div>
            </div>
        `;

        // Add as assistant message
        this.app.addMessage('assistant', planHTML);
    }

    getStatusIcon(status) {
        const icons = {
            pending: '⏳',
            'in-progress': '→',
            completed: '✓',
            failed: '✗'
        };
        return icons[status] || '⏳';
    }

    async approvePlan(planId) {
        if (!planId || !this.app.sessionId) return;

        try {
            // Hide action buttons and show progress
            const planMessage = document.querySelector(`[data-plan-id="${planId}"]`);
            if (!planMessage) {
                console.error('Plan message element not found!');
                return;
            }

            planMessage.querySelector('.plan-actions').style.display = 'none';
            planMessage.querySelector('.plan-progress').style.display = 'block';

            // Disable input during execution
            this.app.isProcessing = true;
            this.app.elements.sendButton.disabled = true;
            this.app.elements.messageInput.disabled = true;

            await window.httpClient.post(`${this.app.config.serverUrl}/chat/agent/approve`, {
                session_id: this.app.sessionId,
                plan_id: planId,
                approved: true
            });

            // Start polling for status
            this.pollExecutionStatus(planId);

        } catch (error) {
            console.error('Failed to approve plan:', error);
            if (window.toastManager) {
                window.toastManager.error('Failed to start execution');
            }
        }
    }

    async pollExecutionStatus(planId) {
        const pollInterval = 1000; // Poll every second

        const poll = async () => {
            try {
                const status = await window.httpClient.get(
                    `${this.app.config.serverUrl}/chat/agent/status/${planId}?session_id=${this.app.sessionId}`
                );

                // Update UI based on status
                this.updateExecutionStatus(planId, status);

                // Continue polling if still executing
                if (status.status === 'executing' || status.status === 'awaiting_approval') {
                    setTimeout(poll, pollInterval);
                } else if (status.status === 'completed') {
                    // Add final response message
                    if (status.final_response) {
                        this.app.addMessage('assistant', status.final_response);
                    }
                    // Re-enable input
                    this.app.isProcessing = false;
                    this.app.elements.sendButton.disabled = false;
                    this.app.elements.messageInput.disabled = false;
                } else if (status.status === 'failed') {
                    this.app.addMessage('assistant', `❌ Execution failed: ${status.error || 'Unknown error'}`);
                    // Re-enable input
                    this.app.isProcessing = false;
                    this.app.elements.sendButton.disabled = false;
                    this.app.elements.messageInput.disabled = false;
                }
            } catch (error) {
                console.error('Failed to poll status:', error);
            }
        };

        poll();
    }

    updateExecutionStatus(planId, status) {
        const planMessage = document.querySelector(`[data-plan-id="${planId}"]`);
        if (!planMessage) {
            return;
        }

        // Update progress bar
        const progressBar = planMessage.querySelector('.progress-bar');
        const progressText = planMessage.querySelector('.progress-text');
        const progressPercentage = planMessage.querySelector('.progress-percentage');

        if (progressBar && progressText && progressPercentage) {
            const percentage = status.total_steps > 0 ? (status.current_step / status.total_steps) * 100 : 0;
            progressBar.value = percentage;
            progressText.textContent = `Step ${status.current_step} of ${status.total_steps}`;
            progressPercentage.textContent = `${Math.round(percentage)}%`;
        }

        // Update completed steps
        status.completed.forEach((stepResult, index) => {
            const stepEl = planMessage.querySelector(`[data-step-index="${index}"]`);
            if (stepEl) {
                const newStatus = stepResult.success ? 'completed' : 'failed';
                stepEl.dataset.status = newStatus;
                const iconEl = stepEl.querySelector('.step-icon');
                if (iconEl) {
                    iconEl.textContent = this.getStatusIcon(newStatus);
                }

                const durationEl = stepEl.querySelector('.step-duration');
                if (durationEl) {
                    durationEl.textContent = `${stepResult.duration.toFixed(1)}s`;
                    durationEl.style.display = 'inline';
                }
            }
        });

        // Update current step
        if (status.current_step < status.total_steps) {
            const currentStepEl = planMessage.querySelector(`[data-step-index="${status.current_step}"]`);
            if (currentStepEl) {
                currentStepEl.dataset.status = 'in-progress';
                const iconEl = currentStepEl.querySelector('.step-icon');
                if (iconEl) {
                    iconEl.textContent = this.getStatusIcon('in-progress');
                }
            }
        }
    }

    rejectPlan(planId) {
        const planMessage = document.querySelector(`[data-plan-id="${planId}"]`);
        if (planMessage) {
            planMessage.querySelector('.plan-actions').innerHTML = '<div class="plan-rejected">❌ Plan rejected</div>';
        }
    }

    showModifyModal(planId) {
        this.currentPlanId = planId;
        this.elements.modifyModal.style.display = 'flex';
    }

    hideModifyModal() {
        this.elements.modifyModal.style.display = 'none';
        this.elements.modificationInput.value = '';
        this.currentPlanId = null;
    }

    async submitModifications() {
        const modifications = this.elements.modificationInput.value.trim();
        if (!modifications || !this.currentPlanId) return;

        try {
            const response = await window.httpClient.post(`${this.app.config.serverUrl}/chat/agent/approve`, {
                session_id: this.app.sessionId,
                plan_id: this.currentPlanId,
                approved: false,
                modifications: modifications
            });

            // Display new modified plan
            this.displayPlanAsMessage(response);
            this.hideModifyModal();

        } catch (error) {
            console.error('Failed to modify plan:', error);
            if (window.toastManager) {
                window.toastManager.error('Failed to modify plan');
            }
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize agent mode when app is ready
document.addEventListener('DOMContentLoaded', () => {
    // Wait for the main app to be initialized
    const initAgentMode = () => {
        if (window.app) {
            window.agentMode = new AgentModeManager(window.app);

            // Override sendMessage to check agent mode
            const originalSendMessage = window.app.sendMessage.bind(window.app);
            window.app.sendMessage = async function() {
                const message = this.elements.messageInput.value.trim();

                if (!message || this.isProcessing || !this.sessionId) {
                    return;
                }

                if (window.agentMode && window.agentMode.agentModeEnabled) {
                    // Use agent mode
                    this.isProcessing = true;
                    this.elements.sendButton.disabled = true;

                    // Add user message to chat
                    this.addMessage('user', message);

                    // Clear input
                    this.elements.messageInput.value = '';
                    this.elements.charCounter.textContent = '0/2000';
                    this.autoResizeTextarea(this.elements.messageInput);

                    // Show typing indicator briefly
                    this.showTypingIndicator();

                    await window.agentMode.sendMessage(message);

                    this.hideTypingIndicator();
                    this.isProcessing = false;
                    this.elements.sendButton.disabled = false;
                    this.elements.messageInput.focus();
                } else {
                    // Use normal mode
                    return originalSendMessage();
                }
            };
        } else {
            // App not ready yet, wait a bit
            setTimeout(initAgentMode, 100);
        }
    };

    initAgentMode();
});
