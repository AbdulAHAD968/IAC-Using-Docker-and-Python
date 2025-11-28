// ==================== DOM ELEMENTS ====================

const elements = {
    systemStatus: document.getElementById('system-status'),
    containerCount: document.getElementById('container-count'),
    deploymentStatus: document.getElementById('deployment-status'),
    containersList: document.getElementById('containers-list'),
    logsContainer: document.getElementById('logs-container'),
    autoScrollCheckbox: document.getElementById('auto-scroll'),
    clearLogsBtn: document.getElementById('clear-logs-btn'),
    deployBtn: document.getElementById('deploy-btn'),
    createClientBtn: document.getElementById('create-client-btn'),
    cleanupBtn: document.getElementById('cleanup-btn'),
    connectivityBtn: document.getElementById('connectivity-btn'),
    hardenBtn: document.getElementById('harden-btn'),
    auditBtn: document.getElementById('audit-btn'),
    createClientModal: document.getElementById('create-client-modal'),
    confirmModal: document.getElementById('confirm-modal'),
};

// ==================== STATE MANAGEMENT ====================

const state = {
    containers: [],
    deploymentLogs: [],
    isDeploying: false,
    lastLogCount: 0,
};

// ==================== INITIALIZATION ====================

document.addEventListener('DOMContentLoaded', () => {
    initializeEventListeners();
    startStatusPolling();
});

function initializeEventListeners() {
    // Deploy button
    elements.deployBtn.addEventListener('click', () => {
        showConfirmation(
            'Deploy Infrastructure',
            'This will deploy the complete infrastructure. Continue?',
            () => startDeployment()
        );
    });

    // Create client button
    elements.createClientBtn.addEventListener('click', () => {
        openModal('create-client-modal');
    });

    // Cleanup button
    elements.cleanupBtn.addEventListener('click', () => {
        showConfirmation(
            'Cleanup Infrastructure',
            'This will stop and remove all containers. This action cannot be undone. Continue?',
            () => performCleanup()
        );
    });

    // Connectivity test button
    elements.connectivityBtn.addEventListener('click', () => {
        showConfirmation(
            'Test Network Connectivity',
            'This will test connectivity between all containers. Continue?',
            () => performConnectivityTest()
        );
    });

    // Harden security button
    elements.hardenBtn.addEventListener('click', () => {
        showConfirmation(
            'Apply Security Hardening',
            'This will install security tools and harden all containers. Continue?',
            () => performSecurityHardening()
        );
    });

    // Audit button
    elements.auditBtn.addEventListener('click', () => {
        performSecurityAudit();
    });

    // Clear logs button
    elements.clearLogsBtn.addEventListener('click', () => {
        clearLogs();
    });

    // Modal close buttons
    document.querySelectorAll('.modal-close').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const modal = e.target.closest('.modal');
            if (modal) closeModal(modal.id);
        });
    });

    // Click outside modal to close
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeModal(modal.id);
        });
    });
}

// ==================== STATUS POLLING ====================

function startStatusPolling() {
    statusPoller.start(async () => {
        try {
            // Get main status
            const status = await API.getStatus();
            updateSystemStatus(status);

            // Get deployment status
            const deployStatus = await API.getDeploymentStatus();
            updateDeploymentStatus(deployStatus);

        } catch (error) {
            console.error('Error polling status:', error);
            elements.systemStatus.textContent = '🔴 Error';
            elements.systemStatus.className = 'status-badge status-failed';
        }
    });
}

// ==================== STATUS UPDATES ====================

function updateSystemStatus(status) {
    if (!status || !status.containers) return;

    // Update container count
    elements.containerCount.textContent = status.container_count || 0;

    // Update containers list
    updateContainersList(status.containers);

    // Update system status
    elements.systemStatus.textContent = '🟢 Running';
    elements.systemStatus.className = 'status-badge status-running';
}

function updateDeploymentStatus(deployStatus) {
    if (!deployStatus) return;

    state.isDeploying = deployStatus.in_progress;

    // Update deployment status badge
    updateDeploymentStatusBadge(deployStatus.status);

    // Update logs
    if (deployStatus.logs && deployStatus.logs.length > state.lastLogCount) {
        const newLogs = deployStatus.logs.slice(state.lastLogCount);
        newLogs.forEach(log => addLogEntry(log));
        state.lastLogCount = deployStatus.logs.length;
    }

    // Update button states
    elements.deployBtn.disabled = state.isDeploying;
    elements.createClientBtn.disabled = state.isDeploying;
    elements.cleanupBtn.disabled = state.isDeploying;
    elements.auditBtn.disabled = state.isDeploying;
}

function updateDeploymentStatusBadge(status) {
    let statusText = '⏳ Idle';
    let statusClass = 'status-badge';

    switch (status) {
        case 'deploying':
            statusText = '🚀 Deploying...';
            statusClass = 'status-badge status-deploying';
            break;
        case 'completed':
            statusText = '✅ Completed';
            statusClass = 'status-badge status-completed';
            break;
        case 'failed':
            statusText = '❌ Failed';
            statusClass = 'status-badge status-failed';
            break;
        default:
            statusText = '⏳ Idle';
            statusClass = 'status-badge';
    }

    elements.deploymentStatus.textContent = statusText;
    elements.deploymentStatus.className = statusClass;
}

function updateContainersList(containers) {
    if (!containers || containers.length === 0) {
        elements.containersList.innerHTML = `
            <div class="empty-state">
                <p>No containers running</p>
                <p class="text-muted">Deploy infrastructure to start</p>
            </div>
        `;
        return;
    }

    const html = containers.map(container => `
        <div class="container-item">
            <div class="container-header">
                <span class="container-name">${container.name}</span>
                <span class="container-status ${container.status === 'running' ? 'status-running-badge' : 'status-stopped-badge'}">
                    ${container.status === 'running' ? 'Running' : 'Stopped'}
                </span>
            </div>
            <div class="container-info">
                <span><strong>Type:</strong> ${getContainerType(container.name)}</span>
                <span><strong>Image:</strong> ${container.image}</span>
                <span><strong>ID:</strong> ${container.id}</span>
            </div>
            <div class="container-actions">
                ${container.status === 'running' 
                    ? `<button class="btn btn-warning btn-small" onclick="stopContainerAction('${container.name}')">Stop</button>` 
                    : `<button class="btn btn-success btn-small" onclick="startContainerAction('${container.name}')">Start</button>`
                }
                <button class="btn btn-danger btn-small" onclick="removeContainerAction('${container.name}')">Remove</button>
            </div>
        </div>
    `).join('');

    elements.containersList.innerHTML = html;
}

// ==================== LOGGING ====================

function addLogEntry(message) {
    if (!message) return;

    // Clear empty state message
    if (elements.logsContainer.textContent.includes('No logs yet')) {
        elements.logsContainer.innerHTML = '';
    }

    // Determine log type from message
    let logClass = 'info';
    if (message.includes('✅') || message.includes('completed')) logClass = 'success';
    else if (message.includes('❌') || message.includes('failed')) logClass = 'error';
    else if (message.includes('⚠️') || message.includes('Warning')) logClass = 'warning';
    else if (message.includes('🚀') || message.includes('🔍')) logClass = 'info';

    const logEntry = document.createElement('div');
    logEntry.className = `log-entry ${logClass}`;
    logEntry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;

    elements.logsContainer.appendChild(logEntry);

    // Auto-scroll if enabled
    if (elements.autoScrollCheckbox.checked) {
        elements.logsContainer.scrollTop = elements.logsContainer.scrollHeight;
    }
}

function clearLogs() {
    state.deploymentLogs = [];
    state.lastLogCount = 0;
    elements.logsContainer.innerHTML = '<p class="text-muted">No logs yet</p>';
}

// ==================== ACTIONS ====================

async function startDeployment() {
    try {
        elements.deployBtn.disabled = true;
        showAlert('Starting infrastructure deployment...', 'info');

        const response = await API.deploy();
        showAlert('Deployment started! Check logs for progress.', 'success');
    } catch (error) {
        console.error('Deployment error:', error);
        showAlert(`Deployment failed: ${error.message}`, 'error');
    } finally {
        elements.deployBtn.disabled = false;
    }
}

async function stopContainerAction(containerName) {
    try {
        showAlert(`Stopping ${containerName}...`, 'info');
        await API.stopContainer(containerName);
        showAlert(`${containerName} stopped successfully`, 'success');
    } catch (error) {
        console.error('Error stopping container:', error);
        showAlert(`Failed to stop container: ${error.message}`, 'error');
    }
}

async function startContainerAction(containerName) {
    try {
        showAlert(`Starting ${containerName}...`, 'info');
        await API.startContainer(containerName);
        showAlert(`${containerName} started successfully`, 'success');
    } catch (error) {
        console.error('Error starting container:', error);
        showAlert(`Failed to start container: ${error.message}`, 'error');
    }
}

async function removeContainerAction(containerName) {
    showConfirmation(
        'Remove Container',
        `Are you sure you want to remove ${containerName}?`,
        async () => {
            try {
                showAlert(`Removing ${containerName}...`, 'info');
                await API.removeContainer(containerName);
                showAlert(`${containerName} removed successfully`, 'success');
            } catch (error) {
                console.error('Error removing container:', error);
                showAlert(`Failed to remove container: ${error.message}`, 'error');
            }
        }
    );
}

async function performCleanup() {
    try {
        showAlert('Cleaning up infrastructure...', 'warning');
        await API.cleanup();
        showAlert('Infrastructure cleaned up successfully', 'success');
    } catch (error) {
        console.error('Cleanup error:', error);
        showAlert(`Cleanup failed: ${error.message}`, 'error');
    }
}

async function performSecurityAudit() {
    try {
        elements.auditBtn.disabled = true;
        showAlert('Running security audit...', 'info');

        const response = await API.securityAudit();
        showAlert('Security audit completed! Check logs for details.', 'success');
    } catch (error) {
        console.error('Security audit error:', error);
        showAlert(`Security audit failed: ${error.message}`, 'error');
    } finally {
        elements.auditBtn.disabled = false;
    }
}

async function performConnectivityTest() {
    try {
        elements.connectivityBtn.disabled = true;
        showAlert('Testing network connectivity...', 'info');

        const response = await API.testConnectivity();
        showAlert('Connectivity testing started! Check logs for results.', 'success');
    } catch (error) {
        console.error('Connectivity test error:', error);
        showAlert(`Connectivity test failed: ${error.message}`, 'error');
    } finally {
        elements.connectivityBtn.disabled = false;
    }
}

async function performSecurityHardening() {
    try {
        elements.hardenBtn.disabled = true;
        showAlert('Applying security hardening...', 'info');

        const response = await API.hardenSecurity();
        showAlert('Security hardening started! Check logs for progress.', 'success');
    } catch (error) {
        console.error('Security hardening error:', error);
        showAlert(`Security hardening failed: ${error.message}`, 'error');
    } finally {
        elements.hardenBtn.disabled = false;
    }
}

async function submitCreateClient() {
    const clientNameInput = document.getElementById('client-name');
    const clientName = clientNameInput.value.trim() || '';

    if (!clientName) {
        showAlert('Please enter a client name or leave blank for auto-generation', 'warning');
        return;
    }

    try {
        showAlert('Creating client...', 'info');
        const response = await API.createClient(clientName);
        showAlert(`Client ${response.container.name} created successfully!`, 'success');
        closeModal('create-client-modal');
        clientNameInput.value = '';
    } catch (error) {
        console.error('Create client error:', error);
        showAlert(`Failed to create client: ${error.message}`, 'error');
    }
}

// ==================== MODALS ====================

function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('hidden');
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('hidden');
    }
}

let pendingConfirmCallback = null;

function showConfirmation(title, message, callback) {
    const confirmTitle = document.getElementById('confirm-title');
    const confirmMessage = document.getElementById('confirm-message');

    confirmTitle.textContent = title;
    confirmMessage.textContent = message;
    pendingConfirmCallback = callback;

    openModal('confirm-modal');
}

function confirmAction() {
    if (pendingConfirmCallback) {
        pendingConfirmCallback();
        pendingConfirmCallback = null;
    }
    closeModal('confirm-modal');
}

// ==================== KEYBOARD SHORTCUTS ====================

document.addEventListener('keydown', (e) => {
    // Escape to close modals
    if (e.key === 'Escape') {
        document.querySelectorAll('.modal:not(.hidden)').forEach(modal => {
            closeModal(modal.id);
        });
    }
});
