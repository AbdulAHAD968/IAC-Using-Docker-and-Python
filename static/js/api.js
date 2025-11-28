// ==================== API CLIENT ====================

class APIClient {
    constructor(baseURL = '') {
        this.baseURL = baseURL || window.location.origin;
        this.timeout = 30000;
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
            ...options,
        };

        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), this.timeout);

            const response = await fetch(url, {
                ...config,
                signal: controller.signal,
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.error || `HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            throw error;
        }
    }

    // GET request
    get(endpoint) {
        return this.request(endpoint, { method: 'GET' });
    }

    // POST request
    post(endpoint, data = {}) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    // DELETE request
    delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    }
}

// ==================== API ENDPOINTS ====================

const api = new APIClient();

const API = {
    // Get system status
    getStatus: () => api.get('/api/status'),

    // Get deployment status
    getDeploymentStatus: () => api.get('/api/deployment/status'),

    // Deploy infrastructure
    deploy: () => api.post('/api/deploy'),

    // Create new client
    createClient: (name) => api.post('/api/create-client', { name }),

    // Stop container
    stopContainer: (containerName) => api.post(`/api/stop-container/${containerName}`),

    // Start container
    startContainer: (containerName) => api.post(`/api/start-container/${containerName}`),

    // Remove container
    removeContainer: (containerName) => api.delete(`/api/remove-container/${containerName}`),

    // Cleanup all
    cleanup: () => api.post('/api/cleanup'),

    // Test connectivity
    testConnectivity: () => api.post('/api/test-connectivity'),

    // Harden security
    hardenSecurity: () => api.post('/api/harden-security'),

    // Security audit
    securityAudit: () => api.get('/api/security-audit'),
};

// ==================== POLLING & STATUS UPDATES ====================

class StatusPoller {
    constructor(interval = 3000) {
        this.interval = interval;
        this.timerId = null;
        this.isRunning = false;
    }

    start(callback) {
        if (this.isRunning) return;
        this.isRunning = true;
        
        // Call immediately
        callback();
        
        // Then poll
        this.timerId = setInterval(() => {
            if (this.isRunning) {
                callback();
            }
        }, this.interval);
    }

    stop() {
        if (this.timerId) {
            clearInterval(this.timerId);
            this.timerId = null;
        }
        this.isRunning = false;
    }

    setInterval(interval) {
        this.interval = interval;
        if (this.isRunning) {
            this.stop();
            this.start();
        }
    }
}

// Create global poller instance
const statusPoller = new StatusPoller(3000);

// ==================== UTILITY FUNCTIONS ====================

function formatTime(date) {
    return new Date(date).toLocaleTimeString();
}

function showAlert(message, type = 'info') {
    const alertId = `alert-${Date.now()}`;
    const alertHTML = `
        <div id="${alertId}" class="alert alert-${type}">
            ${message}
        </div>
    `;
    
    // Add to a container or create one
    let alertContainer = document.getElementById('alert-container');
    if (!alertContainer) {
        alertContainer = document.createElement('div');
        alertContainer.id = 'alert-container';
        alertContainer.style.position = 'fixed';
        alertContainer.style.top = '20px';
        alertContainer.style.right = '20px';
        alertContainer.style.zIndex = '2000';
        alertContainer.style.maxWidth = '400px';
        document.body.appendChild(alertContainer);
    }
    
    const alert = document.createElement('div');
    alert.innerHTML = alertHTML;
    alertContainer.appendChild(alert);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        const alertEl = document.getElementById(alertId);
        if (alertEl) {
            alertEl.style.opacity = '0';
            alertEl.style.transition = 'opacity 0.3s ease';
            setTimeout(() => alertEl.remove(), 300);
        }
    }, 5000);
}

function formatContainerName(name) {
    return name.replace(/-/g, ' ').toUpperCase();
}

function getContainerType(name) {
    if (name.includes('web-server')) return 'Web Server';
    if (name.includes('db-server')) return 'Database';
    if (name.includes('email-server')) return 'Email Server';
    if (name.includes('client-pc')) return 'Client';
    return 'Container';
}

function getContainerColor(type) {
    const colors = {
        'web-server': '#3b82f6',
        'db-server': '#8b5cf6',
        'email-server': '#ec4899',
        'client-pc': '#10b981',
    };
    for (const [key, color] of Object.entries(colors)) {
        if (type.includes(key)) return color;
    }
    return '#6b7280';
}
