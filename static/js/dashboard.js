function switchTab(tabName) {

    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });

    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    document.getElementById(tabName).classList.add('active');

    event.target.classList.add('active');

    if (tabName === 'health') {
        setTimeout(runHealthCheck, 500);
    } else if (tabName === 'versioning') {
        setTimeout(loadDeploymentHistory, 500);
    } else if (tabName === 'configuration') {
        setTimeout(loadConfiguration, 500);
    } else if (tabName === 'security') {
        setTimeout(loadFirewallRules, 500);
    } else if (tabName === 'ids') {
        setTimeout(refreshIDSStatus, 500);
    }
}

async function startDeployment() {
    showConfirmation(
        'Deploy Infrastructure',
        'This will deploy complete infrastructure. Continue?',
        async () => {
            try {
                updateStatus('deploying', '⏳ Deploying...');
                disableButtons();

                const response = await fetch('/api/deploy', { method: 'POST' });
                const data = await response.json();

                addLog(' Deployment started');

                let isDeploying = true;
                while (isDeploying) {
                    await new Promise(resolve => setTimeout(resolve, 2000));

                    const statusRes = await fetch('/api/deployment/status');
                    const statusData = await statusRes.json();

                    const newLogs = statusData.logs.slice(state.lastLogCount);
                    newLogs.forEach(log => addLog(log));
                    state.lastLogCount = statusData.logs.length;

                    if (statusData.status === 'completed' || statusData.status === 'failed') {
                        isDeploying = false;
                        updateStatus('completed', statusData.status === 'completed' ? ' Completed' : ' Failed');
                        await refreshStatus();
                    }
                }

                enableButtons();
            } catch (error) {
                addLog(` Error: ${error.message}`);
                updateStatus('error', ' Error');
                enableButtons();
            }
        }
    );
}

async function performCleanup() {
    showConfirmation(
        'Cleanup Infrastructure',
        'This will stop and remove ALL containers. Cannot be undone. Continue?',
        async () => {
            try {
                updateStatus('cleaning', '⏳ Cleaning...');
                const response = await fetch('/api/cleanup', { method: 'POST' });
                const data = await response.json();

                addLog(' ' + data.message);
                await new Promise(resolve => setTimeout(resolve, 2000));
                await refreshStatus();
                updateStatus('idle', ' Cleanup Complete');
            } catch (error) {
                addLog(` Error: ${error.message}`);
                updateStatus('error', ' Error');
            }
        }
    );
}

async function runHealthCheck() {
    try {
        addLog(' Running health checks...');

        const response = await fetch('/api/health/check', { method: 'POST' });
        const health = await response.json();

        const healthSummary = `
            <div class="health-card">
                <h4>Health Check Summary</h4>
                <p><strong>Timestamp:</strong> ${health.timestamp}</p>
                <p><strong>Total Containers:</strong> ${health.total_containers}</p>
                <p><strong>Healthy:</strong> ${health.summary.healthy}</p>
                <p><strong>Unhealthy:</strong> ${health.summary.unhealthy}</p>
                <p><strong>Stopped:</strong> ${health.summary.stopped}</p>
            </div>
        `;

        document.getElementById('health-report').innerHTML = healthSummary;

        let containerHealthHTML = '';
        health.checked_containers.forEach(container => {
            const isHealthy = container.healthy && container.status === 'running';
            const cardClass = isHealthy ? '' : (container.status !== 'running' ? 'warning' : 'error');

            containerHealthHTML += `
                <div class="health-card ${cardClass}">
                    <strong>${container.name}</strong>
                    <p>Status: ${container.status}</p>
                    <p>Memory: ${container.memory_usage_mb || 'N/A'} MB / ${container.memory_limit_mb || 'N/A'} MB (${container.memory_percent || 0}%)</p>
                    <p>CPU: ${container.cpu_percent || 0}%</p>
                    ${container.issues && container.issues.length > 0 ? 
                        `<p style="color: red;"><strong>Issues:</strong> ${container.issues.join(', ')}</p>` : 
                        '<p style="color: green;"> No issues</p>'}
                </div>
            `;
        });

        document.getElementById('container-health-list').innerHTML = containerHealthHTML;

        if (health.summary.unhealthy === 0) {
            document.getElementById('health-status').className = 'status-badge status-running';
            document.getElementById('health-status').textContent = ' Healthy';
        } else {
            document.getElementById('health-status').className = 'status-badge';
            document.getElementById('health-status').textContent = ' Warning';
        }

        addLog(' Health check completed');
    } catch (error) {
        addLog(` Health check error: ${error.message}`);
    }
}

async function performSecurityHardening() {
    showConfirmation(
        'Apply Security Hardening',
        'This will install security tools and harden all containers. Continue?',
        async () => {
            try {
                updateStatus('hardening', '⏳ Hardening...');
                const response = await fetch('/api/security/harden', { method: 'POST' });
                const data = await response.json();

                addLog(' ' + data.message);

                let isHardening = true;
                while (isHardening) {
                    await new Promise(resolve => setTimeout(resolve, 2000));

                    const statusRes = await fetch('/api/deployment/status');
                    const statusData = await statusRes.json();

                    const newLogs = statusData.logs.slice(state.lastLogCount);
                    newLogs.forEach(log => addLog(log));
                    state.lastLogCount = statusData.logs.length;

                    if (!statusData.in_progress) {
                        isHardening = false;
                        addLog(' Security hardening completed');
                        updateStatus('completed', ' Hardened');
                    }
                }
            } catch (error) {
                addLog(` Error: ${error.message}`);
                updateStatus('error', ' Error');
            }
        }
    );
}

async function performSecurityAudit() {
    try {
        addLog(' Running security audit...');

        const response = await fetch('/api/security/audit', { method: 'POST' });
        const audit = await response.json();

        let auditHTML = '<h4>Security Audit Results</h4>';

        if (audit.audit_results && audit.audit_results.length > 0) {
            auditHTML += '<div style="max-height: 400px; overflow-y: auto;">';
            audit.audit_results.forEach(result => {
                const hasIssues = result.security_issues && result.security_issues.length > 0;
                const bgColor = hasIssues ? '#fff3cd' : '#d4edda';

                auditHTML += `
                    <div style="background: ${bgColor}; padding: 10px; margin: 5px 0; border-radius: 5px;">
                        <strong>${result.container}</strong>
                        <p>Running as root: ${result.running_as_root ? ' Yes' : ' No'}</p>
                        ${hasIssues ? `<p style="color: red;">Issues: ${result.security_issues.join(', ')}</p>` : ''}
                    </div>
                `;
            });
            auditHTML += '</div>';
        }

        document.getElementById('security-report').innerHTML = auditHTML;
        addLog(' Security audit completed');
    } catch (error) {
        addLog(` Audit error: ${error.message}`);
    }
}

async function performConnectivityTest() {
    try {
        addLog(' Testing network connectivity...');

        const response = await fetch('/api/test-connectivity', { method: 'POST' });
        const data = await response.json();

        addLog(' Connectivity test started, checking results...');

        let isRunning = true;
        while (isRunning) {
            await new Promise(resolve => setTimeout(resolve, 2000));

            const resultsRes = await fetch('/api/connectivity-results');
            const results = await resultsRes.json();

            if (results.completed) {
                isRunning = false;

                let connectivityHTML = `
                    <h4>Connectivity Test Results</h4>
                    <p><strong>Passed:</strong> ${results.stats.passed}/${results.stats.total}</p>
                `;

                connectivityHTML += '<div style="max-height: 300px; overflow-y: auto; background: #f8f9fa; padding: 10px; border-radius: 5px;">';
                results.results.forEach(result => {
                    connectivityHTML += `<p>${result}</p>`;
                });
                connectivityHTML += '</div>';

                document.getElementById('security-report').innerHTML = connectivityHTML;
            }
        }

        addLog(' Connectivity test completed');
    } catch (error) {
        addLog(` Connectivity test error: ${error.message}`);
    }
}

async function loadFirewallRules() {
    try {
        const response = await fetch('/api/configuration');
        const config = await response.json();

        let rulesHTML = '';

        if (config.infrastructure) {
            ['web_servers', 'db_servers', 'email_servers', 'client_pcs'].forEach(service => {
                if (config.infrastructure[service] && config.infrastructure[service].security) {
                    const rules = config.infrastructure[service].security.firewall_rules || [];
                    if (rules.length > 0) {
                        rulesHTML += `<h4>${service}</h4><ul>`;
                        rules.forEach(rule => {
                            rulesHTML += `<li>${rule}</li>`;
                        });
                        rulesHTML += '</ul>';
                    }
                }
            });
        }

        if (!rulesHTML) {
            rulesHTML = '<p class="text-muted">No firewall rules configured</p>';
        }

        document.getElementById('firewall-rules').innerHTML = rulesHTML;
    } catch (error) {
        document.getElementById('firewall-rules').innerHTML = `<p class="text-muted">Error loading rules: ${error.message}</p>`;
    }
}

async function loadDeploymentHistory() {
    try {
        addLog(' Loading deployment history...');

        const response = await fetch('/api/deployments?limit=20');
        const data = await response.json();

        let historyHTML = '';

        if (data.deployments && data.deployments.length > 0) {
            data.deployments.forEach((dep, index) => {
                historyHTML += `
                    <div class="deployment-history" onclick="loadDeploymentDetails('${dep.deployment_id}')">
                        <div style="cursor: pointer;">
                            <strong>${dep.deployment_id}</strong>
                            <br>
                            <small>${dep.timestamp}</small>
                            <br>
                            <span class="version-badge">${dep.container_count} containers</span>
                            <span class="version-badge">${dep.description}</span>
                            <button class="btn btn-sm btn-warning" onclick="event.stopPropagation(); showRollbackConfirm('${dep.deployment_id}')">
                                 Rollback
                            </button>
                        </div>
                    </div>
                `;
            });
        } else {
            historyHTML = '<p class="text-muted">No deployment history available</p>';
        }

        document.getElementById('deployment-history-list').innerHTML = historyHTML;
        addLog(' Deployment history loaded');
    } catch (error) {
        addLog(` Error loading history: ${error.message}`);
    }
}

async function loadDeploymentDetails(deploymentId) {
    try {
        const response = await fetch(`/api/deployment/${deploymentId}`);
        const deployment = await response.json();

        let detailsHTML = `
            <h3>${deployment.deployment_id}</h3>
            <p><strong>Timestamp:</strong> ${deployment.timestamp}</p>
            <p><strong>Status:</strong> ${deployment.status}</p>
            <p><strong>Description:</strong> ${deployment.description}</p>
            <h4>Containers:</h4>
            <ul>
        `;

        Object.entries(deployment.containers).forEach(([name, info]) => {
            detailsHTML += `
                <li>
                    <strong>${name}</strong>
                    <br>
                    Image: ${info.image}
                    <br>
                    Status: ${info.status}
                </li>
            `;
        });

        detailsHTML += '</ul>';

        document.getElementById('deployment-details-content').innerHTML = detailsHTML;
        document.getElementById('details-rollback-btn').style.display = 'block';
        document.getElementById('details-rollback-btn').onclick = () => showRollbackConfirm(deploymentId);

        openModal('deployment-details-modal');
    } catch (error) {
        addLog(` Error loading details: ${error.message}`);
    }
}

function showRollbackConfirm(deploymentId) {
    showConfirmation(
        'Rollback Deployment',
        `Rollback to ${deploymentId}? This will recreate containers to match this deployment.`,
        () => performRollback(deploymentId)
    );
}

async function performRollback(deploymentId) {
    try {
        updateStatus('rollback', '⏳ Rolling back...');
        addLog(` Starting rollback to ${deploymentId}...`);

        const response = await fetch(`/api/deployment/${deploymentId}/rollback`, { method: 'POST' });
        const data = await response.json();

        addLog(' Rollback completed');
        closeModal('deployment-details-modal');

        await new Promise(resolve => setTimeout(resolve, 2000));
        await refreshStatus();
        updateStatus('completed', ' Rollback Complete');
    } catch (error) {
        addLog(` Rollback error: ${error.message}`);
        updateStatus('error', ' Error');
    }
}

function rollbackFromModal() {
    const deploymentId = document.getElementById('details-title').textContent.split(': ')[1];
    showRollbackConfirm(deploymentId);
}

async function loadConfiguration() {
    try {
        addLog(' Loading configuration...');

        const response = await fetch('/api/configuration');
        const config = await response.json();

        const configHTML = `
            <pre style="background: #f8f9fa; padding: 15px; border-radius: 5px; overflow-x: auto; max-height: 400px; overflow-y: auto;">
${JSON.stringify(config, null, 2)}
            </pre>
        `;

        document.getElementById('config-display').innerHTML = configHTML;
        addLog(' Configuration loaded');
    } catch (error) {
        addLog(` Error: ${error.message}`);
    }
}

async function validateConfiguration() {
    try {
        const response = await fetch('/api/configuration');
        const config = await response.json();

        const validateRes = await fetch('/api/configuration/validate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        const validation = await validateRes.json();

        const message = validation.valid ? 
            ' Configuration is VALID' : 
            ' Configuration has ERRORS';

        addLog(` Validation Result: ${message}`);

        const message_html = validation.valid ? 
            '<p style="color: green; font-weight: bold;"> Configuration is valid</p>' :
            '<p style="color: red; font-weight: bold;"> Configuration has errors</p>';

        document.getElementById('config-display').innerHTML = message_html;
    } catch (error) {
        addLog(` Validation error: ${error.message}`);
    }
}

async function loadConfigVersions() {
    try {
        addLog(' Loading configuration versions...');

        const response = await fetch('/api/configuration/versions');
        const data = await response.json();

        let versionsHTML = '';

        if (data.versions && data.versions.length > 0) {
            data.versions.forEach(version => {
                versionsHTML += `
                    <div class="deployment-history">
                        <strong>${version.version_id}</strong>
                        <p>${version.timestamp}</p>
                        <p>${version.description || 'No description'}</p>
                        <small>Hash: ${version.config_hash.substring(0, 8)}...</small>
                    </div>
                `;
            });
        } else {
            versionsHTML = '<p class="text-muted">No configuration versions</p>';
        }

        document.getElementById('versions-list').innerHTML = versionsHTML;
        addLog(' Configuration versions loaded');
    } catch (error) {
        addLog(` Error: ${error.message}`);
    }
}

async function checkConfigChanges() {
    try {
        addLog(' Checking for configuration changes...');

        const response = await fetch('/api/configuration/check-changes');
        const data = await response.json();

        const message = data.has_changes ?
            ' Configuration HAS CHANGED' :
            ' No changes detected';

        addLog(message);

        let infoHTML = data.has_changes ?
            '<p style="color: orange; font-weight: bold;"> Configuration has changed! You may want to redeploy.</p>' :
            '<p style="color: green; font-weight: bold;"> Configuration is up-to-date</p>';

        document.getElementById('config-changes-info').innerHTML = infoHTML;
    } catch (error) {
        addLog(` Error: ${error.message}`);
    }
}

async function redeployOnConfigChange() {
    try {
        const response = await fetch('/api/configuration/check-changes');
        const data = await response.json();

        if (!data.has_changes) {
            addLog(' No configuration changes detected - no redeploy needed');
            return;
        }

        showConfirmation(
            'Redeploy on Config Change',
            'Configuration has changed. Redeploy infrastructure with new settings?',
            startDeployment
        );
    } catch (error) {
        addLog(` Error: ${error.message}`);
    }
}

function updateStatus(status, text) {
    document.getElementById('deployment-status').textContent = text;
}

function addLog(message) {
    const logsContainer = document.getElementById('logs-container');

    if (logsContainer.querySelector('.text-muted')) {
        logsContainer.innerHTML = '';
    }

    const logEntry = document.createElement('div');
    logEntry.style.cssText = 'padding: 8px; border-bottom: 1px solid #e0e0e0; font-family: monospace; font-size: 12px;';
    logEntry.textContent = message;

    logsContainer.appendChild(logEntry);

    if (document.getElementById('auto-scroll').checked) {
        logsContainer.scrollTop = logsContainer.scrollHeight;
    }
}

async function refreshLogs() {
    try {
        const searchTerm = document.getElementById('log-search').value;
        const limit = 100;

        const url = new URL('/api/logs', window.location.origin);
        url.searchParams.append('limit', limit);
        if (searchTerm) {
            url.searchParams.append('search', searchTerm);
        }

        const response = await fetch(url.toString());
        const data = await response.json();

        window.allLogs = data.logs;
        window.logsData = data;

        displayLogs(data.logs);

        document.getElementById('log-count').textContent = `${data.count} of ${data.total} logs`;
    } catch (error) {
        console.error('Error refreshing logs:', error);
        addLog(` Error loading logs: ${error.message}`);
    }
}

function displayLogs(logs) {
    const logsContainer = document.getElementById('logs-container');

    if (!logs || logs.length === 0) {
        logsContainer.innerHTML = '<p class="text-muted">No logs available</p>';
        return;
    }

    logsContainer.innerHTML = '';

    logs.forEach(log => {
        const logEntry = document.createElement('div');
        logEntry.className = 'log-entry';
        logEntry.style.cssText = `
            padding: 8px 12px;
            border-bottom: 1px solid #e0e0e0;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 12px;
            line-height: 1.4;
            white-space: pre-wrap;
            word-wrap: break-word;
        `;

        if (log.includes('') || log.includes('')) {
            logEntry.style.color = '#28a745';
        } else if (log.includes('') || log.includes('')) {
            logEntry.style.color = '#dc3545';
        } else if (log.includes('') || log.includes('')) {
            logEntry.style.color = '#ffc107';
        } else if (log.includes('') || log.includes('ℹ')) {
            logEntry.style.color = '#17a2b8';
        }

        logEntry.textContent = log;
        logsContainer.appendChild(logEntry);
    });

    if (document.getElementById('auto-scroll').checked) {
        logsContainer.scrollTop = logsContainer.scrollHeight;
    }
}

function filterLogs() {
    const searchTerm = document.getElementById('log-search').value.toLowerCase();

    if (!window.allLogs) {
        refreshLogs();
        return;
    }

    const filtered = window.allLogs.filter(log => 
        log.toLowerCase().includes(searchTerm)
    );

    displayLogs(filtered);
    document.getElementById('log-count').textContent = `${filtered.length} of ${window.allLogs.length} logs`;
}

async function clearLogs() {
    if (!confirm('Are you sure you want to clear all logs?')) {
        return;
    }

    try {
        const response = await fetch('/api/logs/clear', { method: 'POST' });
        const data = await response.json();

        window.allLogs = [];
        window.logsData = data;
        document.getElementById('logs-container').innerHTML = '<p class="text-muted">Logs cleared</p>';
        document.getElementById('log-count').textContent = '0 logs';
        document.getElementById('log-search').value = '';

        addLog(' Logs cleared');
    } catch (error) {
        addLog(` Error clearing logs: ${error.message}`);
    }
}

async function refreshStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();

        document.getElementById('container-count').textContent = data.container_count;

        let containerHTML = '';
        if (data.containers && data.containers.length > 0) {
            data.containers.forEach(container => {
                const statusEmoji = container.status === 'running' ? '' : '';
                containerHTML += `
                    <div style="padding: 10px; background: #f8f9fa; margin: 5px 0; border-radius: 5px;">
                        <strong>${statusEmoji} ${container.name}</strong>
                        <br>
                        <small>${container.image}</small>
                        <div>
                            <button class="btn btn-sm" onclick="stopContainer('${container.name}')" ${container.status !== 'running' ? 'disabled' : ''}>Stop</button>
                            <button class="btn btn-sm" onclick="startContainer('${container.name}')" ${container.status === 'running' ? 'disabled' : ''}>Start</button>
                            <button class="btn btn-sm" onclick="removeContainer('${container.name}')">Remove</button>
                        </div>
                    </div>
                `;
            });
        } else {
            containerHTML = '<div class="empty-state"><p>No containers running</p></div>';
        }

        document.getElementById('containers-list').innerHTML = containerHTML;
    } catch (error) {
        console.error('Error refreshing status:', error);
    }
}

async function stopContainer(containerName) {
    try {
        const response = await fetch(`/api/container/${containerName}/stop`, { method: 'POST' });
        const data = await response.json();
        addLog(` ${data.message}`);
        await refreshStatus();
    } catch (error) {
        addLog(` Error: ${error.message}`);
    }
}

async function startContainer(containerName) {
    try {
        const response = await fetch(`/api/container/${containerName}/start`, { method: 'POST' });
        const data = await response.json();
        addLog(` ${data.message}`);
        await refreshStatus();
    } catch (error) {
        addLog(` Error: ${error.message}`);
    }
}

async function removeContainer(containerName) {
    showConfirmation(
        'Remove Container',
        `Remove ${containerName}?`,
        async () => {
            try {
                const response = await fetch(`/api/container/${containerName}/remove`, { method: 'DELETE' });
                const data = await response.json();
                addLog(` ${data.message}`);
                await refreshStatus();
            } catch (error) {
                addLog(` Error: ${error.message}`);
            }
        }
    );
}

async function submitCreateClient() {
    try {
        const name = document.getElementById('client-name').value;
        const response = await fetch('/api/create-client', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name || undefined })
        });

        const data = await response.json();
        addLog(` ${data.message}`);

        closeModal('create-client-modal');
        document.getElementById('create-client-form').reset();

        await refreshStatus();
    } catch (error) {
        addLog(` Error: ${error.message}`);
    }
}

function showConfirmation(title, message, callback) {
    document.getElementById('confirm-title').textContent = title;
    document.getElementById('confirm-message').textContent = message;
    window.confirmCallback = callback;
    openModal('confirm-modal');
}

function executeConfirmation() {
    if (window.confirmCallback) {
        window.confirmCallback();
    }
    closeModal('confirm-modal');
}

function openModal(modalId) {
    document.getElementById(modalId).classList.remove('hidden');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.add('hidden');
}

function disableButtons() {
    document.querySelectorAll('button').forEach(btn => btn.disabled = true);
}

function enableButtons() {
    document.querySelectorAll('button').forEach(btn => btn.disabled = false);
}

async function testNetworkConnectivity() {
    try {
        openModal('network-test-modal');

        const response = await fetch('/api/network/test', { method: 'POST' });
        const data = await response.json();

        addLog(' Network connectivity test started');

        let isTesting = true;
        while (isTesting) {
            await new Promise(resolve => setTimeout(resolve, 1000));

            const statusRes = await fetch('/api/deployment/status');
            const statusData = await statusRes.json();

            const logsDisplay = document.getElementById('network-test-logs');
            if (statusData.logs && statusData.logs.length > 0) {
                logsDisplay.innerHTML = statusData.logs
                    .map(log => `<div class="log-line">${escapeHtml(log)}</div>`)
                    .join('');

                logsDisplay.scrollTop = logsDisplay.scrollHeight;
            }

            const statusBadge = document.getElementById('network-test-status');
            if (statusData.status === 'completed' || statusData.status === 'failed') {
                isTesting = false;
                statusBadge.className = 'test-status-badge ' + (statusData.status === 'completed' ? 'success' : 'error');
                statusBadge.textContent = statusData.status === 'completed' ? ' Test Completed' : ' Test Failed';
            } else {
                statusBadge.textContent = '⏳ Testing...';
            }
        }

        addLog(' Network connectivity test completed');
    } catch (error) {
        addLog(` Error: ${error.message}`);
        const statusBadge = document.getElementById('network-test-status');
        statusBadge.className = 'test-status-badge error';
        statusBadge.textContent = ' Error';
    }
}

async function showAllLogs() {
    try {
        openModal('all-logs-modal');

        addLog(' Loading all system logs...');

        const response = await fetch('/api/logs/all');
        const data = await response.json();

        if (!data.success) {
            alert('Error loading logs: ' + data.error);
            return;
        }

        window.allLogsData = data.logs;

        displayDeploymentLogs(data.logs.deployment_logs);

        displayContainerLogs(data.logs.container_logs);

        displayHealthReports(data.logs.health_reports);

        addLog(' All logs loaded successfully');
    } catch (error) {
        addLog(` Error loading logs: ${error.message}`);
    }
}

function displayDeploymentLogs(logs) {
    const display = document.getElementById('deployment-logs-display');

    if (!logs || logs.length === 0) {
        display.innerHTML = '<p class="text-muted">No deployment logs available</p>';
        return;
    }

    const html = logs
        .map(log => `<div class="log-line">${escapeHtml(log)}</div>`)
        .join('');

    display.innerHTML = html;
}

function displayContainerLogs(logs) {
    const display = document.getElementById('container-logs-display');

    if (!logs || Object.keys(logs).length === 0) {
        display.innerHTML = '<p class="text-muted">No container logs available</p>';
        return;
    }

    let html = '';
    for (const [containerName, logLines] of Object.entries(logs)) {
        html += `<div class="container-log-section">`;
        html += `<h4 class="container-log-title"> ${escapeHtml(containerName)}</h4>`;

        if (Array.isArray(logLines)) {
            html += logLines
                .filter(line => line && line.trim())
                .map(line => `<div class="log-line">${escapeHtml(line)}</div>`)
                .join('');
        } else {
            html += `<div class="log-line">${escapeHtml(JSON.stringify(logLines))}</div>`;
        }

        html += `</div>`;
    }

    display.innerHTML = html;
}

function displayHealthReports(reports) {
    const display = document.getElementById('health-logs-display');

    if (!reports || Object.keys(reports).length === 0) {
        display.innerHTML = '<p class="text-muted">No health reports available</p>';
        return;
    }

    let html = '';
    for (const [reportName, reportData] of Object.entries(reports)) {
        html += `<div class="health-report-section">`;
        html += `<h4 class="health-report-title"> ${escapeHtml(reportName)}</h4>`;
        html += `<pre class="health-report-content">${escapeHtml(JSON.stringify(reportData, null, 2))}</pre>`;
        html += `</div>`;
    }

    display.innerHTML = html;
}

function switchLogsTab(tabName) {

    document.querySelectorAll('.logs-tab-content').forEach(tab => {
        tab.classList.remove('active');
    });

    document.querySelectorAll('.logs-tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    document.getElementById(tabName + '-logs-tab').classList.add('active');

    event.target.classList.add('active');
}

function filterAllLogs(logsType) {
    const searchInput = document.getElementById(logsType + '-logs-search').value.toLowerCase();
    const display = document.getElementById(logsType + '-logs-display');
    const lines = display.querySelectorAll('.log-line, .container-log-section');

    lines.forEach(line => {
        const text = line.textContent.toLowerCase();
        line.style.display = text.includes(searchInput) ? '' : 'none';
    });
}

function downloadLogs(logsType) {
    try {
        let content = '';
        let filename = `logs-${new Date().toISOString().slice(0, 19)}.txt`;

        if (logsType === 'deployment' && window.allLogsData) {
            content = window.allLogsData.deployment_logs.join('\n');
        } else if (logsType === 'containers' && window.allLogsData) {
            for (const [containerName, logLines] of Object.entries(window.allLogsData.container_logs)) {
                content += `\n=== ${containerName} ===\n`;
                if (Array.isArray(logLines)) {
                    content += logLines.join('\n');
                } else {
                    content += JSON.stringify(logLines, null, 2);
                }
            }
        } else if (logsType === 'health' && window.allLogsData) {
            for (const [reportName, reportData] of Object.entries(window.allLogsData.health_reports)) {
                content += `\n=== ${reportName} ===\n`;
                content += JSON.stringify(reportData, null, 2);
            }
        }

        const blob = new Blob([content], { type: 'text/plain' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        addLog(` Downloaded ${logsType} logs as ${filename}`);
    } catch (error) {
        addLog(` Error downloading logs: ${error.message}`);
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function refreshIDSStatus() {
    try {
        addLog(' Loading IDS status...');

        const response = await fetch('/api/ids/status');
        const data = await response.json();

        if (!data.status || data.status !== 'active') {
            document.getElementById('ids-models-status').innerHTML = '<p class="error">IDS not active</p>';
            return;
        }

        const stats = data.statistics;

        let modelsHtml = '<div class="models-grid">';
        const models = stats.models_loaded;
        modelsHtml += `<div class="model-card ${models.web_model ? 'loaded' : 'error'}">
            <span class="model-icon"></span>
            <strong>Web Model</strong>
            <span>${models.web_model ? ' Loaded' : ' Not Found'}</span>
        </div>`;
        modelsHtml += `<div class="model-card ${models.db_model ? 'loaded' : 'error'}">
            <span class="model-icon"></span>
            <strong>Database Model</strong>
            <span>${models.db_model ? ' Loaded' : ' Not Found'}</span>
        </div>`;
        modelsHtml += `<div class="model-card ${models.email_model ? 'loaded' : 'error'}">
            <span class="model-icon"></span>
            <strong>Email Model</strong>
            <span>${models.email_model ? ' Loaded' : ' Not Found'}</span>
        </div>`;
        modelsHtml += '</div>';
        document.getElementById('ids-models-status').innerHTML = modelsHtml;

        let statsHtml = '<div class="stats-grid">';
        statsHtml += `<div class="stat-box"><strong>Total Alerts</strong><span>${stats.total_alerts}</span></div>`;

        for (const [type, count] of Object.entries(stats.alert_types || {})) {
            statsHtml += `<div class="stat-box"><strong>${type}</strong><span>${count}</span></div>`;
        }

        for (const [severity, count] of Object.entries(stats.severity_distribution || {})) {
            const severityClass = severity === 'CRITICAL' ? 'critical' : severity === 'HIGH' ? 'high' : 'medium';
            statsHtml += `<div class="stat-box ${severityClass}"><strong>${severity}</strong><span>${count}</span></div>`;
        }

        statsHtml += '</div>';
        document.getElementById('ids-statistics').innerHTML = statsHtml;

        await loadIDSAlerts();

        addLog(' IDS status loaded');
    } catch (error) {
        addLog(` Error loading IDS status: ${error.message}`);
        document.getElementById('ids-models-status').innerHTML = `<p class="error">Error: ${error.message}</p>`;
    }
}

async function loadIDSAlerts() {
    try {
        const response = await fetch('/api/ids/alerts?limit=100');
        const data = await response.json();

        const alerts = data.alerts || [];

        if (alerts.length === 0) {
            document.getElementById('ids-alerts-list').innerHTML = '<p class="text-muted">No alerts detected</p>';
            return;
        }

        let html = '<div class="alerts-table">';

        for (const alert of alerts) {
            const severityClass = alert.severity === 'CRITICAL' ? 'critical' : 
                                 alert.severity === 'HIGH' ? 'high' : 'medium';

            html += `<div class="alert-item ${severityClass}">
                <div class="alert-header">
                    <strong class="alert-type">${alert.alert_type}</strong>
                    <span class="alert-severity">${alert.severity}</span>
                    <span class="alert-time">${new Date(alert.timestamp).toLocaleTimeString()}</span>
                </div>
                <div class="alert-details">
                    <p><strong>Attack Type:</strong> ${alert.attack_type}</p>
                    <p><strong>Source IP:</strong> ${alert.source_ip}</p>
                    <p><strong>Confidence:</strong> ${(alert.confidence * 100).toFixed(2)}%</p>
                    <p><strong>Payload:</strong> <code>${escapeHtml(alert.payload.substring(0, 100))}</code></p>
                </div>
            </div>`;
        }

        html += '</div>';
        document.getElementById('ids-alerts-list').innerHTML = html;
    } catch (error) {
        addLog(` Error loading alerts: ${error.message}`);
    }
}

async function clearIDSAlerts() {
    if (!confirm('Clear all IDS alerts? This cannot be undone.')) {
        return;
    }

    try {
        addLog(' Clearing IDS alerts...');

        const response = await fetch('/api/ids/alerts/clear', { method: 'POST' });
        const data = await response.json();

        addLog(' Alerts cleared');
        await refreshIDSStatus();
    } catch (error) {
        addLog(` Error clearing alerts: ${error.message}`);
    }
}

async function generateAttackSimulation() {
    try {
        const attackType = document.getElementById('attack-type-select').value;

        addLog(` Generating ${attackType} attack simulations...`);

        const response = await fetch('/api/ids/test-attack', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                attack_type: attackType,
                target: 'all'
            })
        });

        const data = await response.json();

        if (!response.ok) {
            addLog(` Error: ${data.error}`);
            return;
        }

        let detectedCount = 0;

        for (const simulation of data.simulations) {
            try {
                const analyzeResponse = await fetch('/api/ids/analyze', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        log_line: typeof simulation === 'string' ? simulation : JSON.stringify(simulation),
                        type: 'web'
                    })
                });

                const analyzeData = await analyzeResponse.json();

                if (analyzeData.detected) {
                    detectedCount++;
                }
            } catch (e) {

            }
        }

        addLog(` Generated ${data.count} simulations, detected ${detectedCount} as threats`);
        await refreshIDSStatus();
    } catch (error) {
        addLog(` Error: ${error.message}`);
    }
}

async function generateNormalLogs() {
    try {
        addLog(' Generating normal web server logs...');

        const response = await fetch('/api/ids/generate-logs', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (!response.ok) {
            addLog(` Error: ${data.error}`);
            return;
        }

        addLog(` Generated ${data.logs_generated} logs, detected ${data.alerts_detected} anomalies`);

        if (data.alerts && data.alerts.length > 0) {
            data.alerts.forEach(alert => {
                addLog(`    ${alert.severity}: ${alert.attack_type} (${(alert.confidence * 100).toFixed(2)}%)`);
            });
        }

        await refreshIDSStatus();
    } catch (error) {
        addLog(` Error: ${error.message}`);
    }
}

async function generateSuspiciousLogs() {
    try {
        addLog(' Generating suspicious web server logs with attack patterns...');

        const response = await fetch('/api/ids/generate-suspicious-logs', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (!response.ok) {
            addLog(` Error: ${data.error}`);
            return;
        }

        addLog(` Generated ${data.logs_generated} suspicious logs, detected ${data.alerts_detected} anomalies`);

        if (data.alerts && data.alerts.length > 0) {
            data.alerts.forEach(alert => {
                addLog(`    ${alert.severity}: ${alert.attack_type} from ${alert.source_ip}`);
            });
        }

        await refreshIDSStatus();
    } catch (error) {
        addLog(` Error: ${error.message}`);
    }
}

async function generateNormalDBLogs() {
    try {
        addLog(' Generating normal database queries...');

        const response = await fetch('/api/ids/generate-db-logs', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (!response.ok) {
            addLog(` Error: ${data.error}`);
            return;
        }

        addLog(` Generated ${data.logs_generated} database logs, detected ${data.alerts_detected} anomalies`);

        if (data.alerts && data.alerts.length > 0) {
            data.alerts.forEach(alert => {
                addLog(`    ${alert.severity}: ${alert.attack_type}`);
            });
        }

        await refreshIDSStatus();
    } catch (error) {
        addLog(` Error: ${error.message}`);
    }
}

async function generateSuspiciousDBLogs() {
    try {
        addLog(' Generating SQL injection attack queries...');

        const response = await fetch('/api/ids/generate-attacks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                attack_type: 'sql_injection',
                target_type: 'db'
            })
        });

        const data = await response.json();

        if (!response.ok) {
            addLog(` Error: ${data.error}`);
            return;
        }

        addLog(` Generated SQL injection attacks, detected ${data.alerts_detected} anomalies`);

        if (data.alerts && data.alerts.length > 0) {
            data.alerts.forEach(alert => {
                addLog(`    ${alert.severity}: ${alert.attack_type} (Confidence: ${(alert.confidence * 100).toFixed(1)}%)`);
            });
        }

        await refreshIDSStatus();
    } catch (error) {
        addLog(` Error: ${error.message}`);
    }
}

async function generateNormalEmailLogs() {
    try {
        addLog(' Generating normal email traffic...');

        const response = await fetch('/api/ids/generate-email-logs', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (!response.ok) {
            addLog(` Error: ${data.error}`);
            return;
        }

        addLog(` Generated ${data.logs_generated} email logs, detected ${data.alerts_detected} anomalies`);

        if (data.alerts && data.alerts.length > 0) {
            data.alerts.forEach(alert => {
                addLog(`    ${alert.severity}: ${alert.attack_type}`);
            });
        }

        await refreshIDSStatus();
    } catch (error) {
        addLog(` Error: ${error.message}`);
    }
}

async function generateSuspiciousEmailLogs() {
    try {
        addLog(' Generating phishing/malware email attacks...');

        const response = await fetch('/api/ids/generate-attacks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                attack_type: 'phishing',
                target_type: 'email'
            })
        });

        const data = await response.json();

        if (!response.ok) {
            addLog(` Error: ${data.error}`);
            return;
        }

        addLog(` Generated phishing/malware attacks, detected ${data.alerts_detected} anomalies`);

        if (data.alerts && data.alerts.length > 0) {
            data.alerts.forEach(alert => {
                addLog(`    ${alert.severity}: ${alert.attack_type} (Confidence: ${(alert.confidence * 100).toFixed(1)}%)`);
            });
        }

        await refreshIDSStatus();
    } catch (error) {
        addLog(` Error: ${error.message}`);
    }
}

function filterAlertsUI() {
    const filter = document.getElementById('alert-filter').value.toLowerCase();
    const alerts = document.querySelectorAll('.alert-item');

    alerts.forEach(alert => {
        const text = alert.textContent.toLowerCase();
        alert.style.display = text.includes(filter) ? '' : 'none';
    });
}

document.addEventListener('DOMContentLoaded', () => {
    refreshStatus();
    setInterval(refreshStatus, 5000);

    refreshLogs();
    setInterval(refreshLogs, 2000); 
});
