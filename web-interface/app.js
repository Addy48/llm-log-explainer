const API_BASE = 'http://localhost:8000';
let logsList = [];
let explanationsList = [];

document.addEventListener('DOMContentLoaded', function() {
    checkServiceHealth();
    setInterval(checkServiceHealth, 30000);
});

async function checkServiceHealth() {
    try {
        const response = await fetch(API_BASE + '/health');
        if (response.ok) {
            updateServiceStatus(true);
        } else {
            updateServiceStatus(false);
        }
    } catch (error) {
        updateServiceStatus(false);
    }
}

function updateServiceStatus(isOnline) {
    const status = document.getElementById('service-status');
    if (isOnline) {
        status.textContent = '✓ Services Online';
        status.classList.remove('offline');
        status.classList.add('online');
    } else {
        status.textContent = '✗ Services Offline';
        status.classList.remove('online');
        status.classList.add('offline');
    }
}

async function generateRandomLog() {
    showLoading(true);
    try {
        clearContainers();
        const response = await fetch(API_BASE + '/fetch-and-explain');
        if (!response.ok) throw new Error('Failed to fetch log');
        const data = await response.json();
        addLogAndExplanation(data);
    } catch (error) {
        showError('Failed to generate log: ' + error.message);
    } finally {
        showLoading(false);
    }
}

async function analyzeScenario(scenario) {
    showLoading(true);
    try {
        clearContainers();
        const response = await fetch(API_BASE + '/fetch-and-explain?scenario=' + scenario);
        if (!response.ok) throw new Error('Failed to fetch scenario');
        const data = await response.json();
        
        if (data.explanations && Array.isArray(data.explanations)) {
            data.explanations.forEach(exp => {
                const logsContainer = document.getElementById('logs-container');
                const explanationsContainer = document.getElementById('explanations-container');
                
                const explanationItem = createExplanationItem(exp);
                explanationsContainer.appendChild(explanationItem);
                
                explanationsList.push(exp);
            });
            
            if (data.summary || data.root_cause) {
                addScenarioSummary(data);
            }
        } else {
            addLogAndExplanation(data);
        }
    } catch (error) {
        showError('Failed to analyze scenario: ' + error.message);
    } finally {
        showLoading(false);
    }
}

function clearContainers() {
    logsList = [];
    explanationsList = [];
    const logsContainer = document.getElementById('logs-container');
    const explanationsContainer = document.getElementById('explanations-container');
    logsContainer.innerHTML = '';
    explanationsContainer.innerHTML = '';
}

function addLogAndExplanation(data) {
    const logData = data.log || data;
    const explanationData = data.explanation || data;
    
    const logsContainer = document.getElementById('logs-container');
    const explanationsContainer = document.getElementById('explanations-container');
    
    const logItem = createLogItem(logData);
    const explanationItem = createExplanationItem(explanationData);
    
    logsContainer.appendChild(logItem);
    explanationsContainer.appendChild(explanationItem);
    
    logsList.push(logData);
    explanationsList.push(explanationData);
    
    updateCounts();
}

function createLogItem(log) {
    const div = document.createElement('div');
    div.className = 'log-item ' + (log.level || 'INFO');
    
    const timestamp = log.timestamp || new Date().toISOString();
    const level = log.level || 'INFO';
    const message = log.message || '';
    const module = log.context ? log.context.module : 'unknown';
    const line = log.context ? log.context.line : 'N/A';
    const processId = log.context ? log.context.process_id : 'N/A';
    
    div.innerHTML = '<div class="log-timestamp">' + timestamp + '</div><div><span class="log-level ' + level + '">' + level + '</span><strong>' + message + '</strong></div><div class="log-context"><span class="log-context-item">Module: ' + module + '</span><span class="log-context-item">Line: ' + line + '</span><span class="log-context-item">PID: ' + processId + '</span></div>';
    
    return div;
}

function createExplanationItem(data) {
    const div = document.createElement('div');
    div.className = 'explanation-item';
    
    const severity = data.severity || 'low';
    const explanation = data.explanation || 'Processing...';
    const suggestion = data.suggestion || 'Monitor system status.';
    
    div.innerHTML = '<div class="severity-badge ' + severity + '">' + severity.toUpperCase() + '</div><div class="explanation-text">' + explanation + '</div><div class="suggestion-box"><strong>Recommended Action:</strong><br>' + suggestion + '</div>';
    
    return div;
}

function addScenarioSummary(data) {
    const explanationsContainer = document.getElementById('explanations-container');
    const summary = document.createElement('div');
    summary.className = 'explanation-item scenario-summary';
    summary.style.marginTop = '16px';
    
    let actions = '';
    if (data.recommended_actions && Array.isArray(data.recommended_actions)) {
        actions = '<div style="margin-top: 12px;"><strong style="color: #2563eb;">Recommended Actions:</strong><ul>';
        data.recommended_actions.forEach(function(a) {
            actions += '<li>' + a + '</li>';
        });
        actions += '</ul></div>';
    }
    
    summary.innerHTML = '<div style="color: #2563eb; font-weight: 700; margin-bottom: 10px;">Scenario Analysis: ' + (data.scenario || 'Unknown') + '</div><div class="explanation-text">' + (data.summary || '') + '</div><div class="suggestion-box"><strong>Root Cause:</strong><br>' + (data.root_cause || 'Analyzing...') + '</div>' + actions;
    
    explanationsContainer.appendChild(summary);
}

function showLoading(show) {
    const loading = document.getElementById('loading');
    if (loading) {
        loading.classList.toggle('hidden', !show);
    }
}

function showError(message) {
    const error = document.getElementById('error-message');
    if (error) {
        error.textContent = message;
        error.classList.remove('hidden');
        setTimeout(() => { error.classList.add('hidden'); }, 5000);
    }
}

function updateCounts() {
    const logsCount = document.getElementById('logs-count');
    const explCount = document.getElementById('explanations-count');
    if (logsCount) logsCount.textContent = logsList.length + ' logs';
    if (explCount) explCount.textContent = explanationsList.length + ' analyzed';
}

function clearAll() {
    logsList = [];
    explanationsList = [];
    const logsContainer = document.getElementById('logs-container');
    const explanationsContainer = document.getElementById('explanations-container');
    logsContainer.innerHTML = '<div class="empty-state">No logs yet. Click "Generate Log" to start.</div>';
    explanationsContainer.innerHTML = '<div class="empty-state">Explanations appear here.</div>';
    updateCounts();
}

function refreshPage() {
    location.reload();
}
