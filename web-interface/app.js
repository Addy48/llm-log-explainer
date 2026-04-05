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
        status.textContent = '● Online';
        status.classList.remove('offline');
        status.classList.add('online');
    } else {
        status.textContent = '● Offline';
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
        showError('Error: ' + error.message);
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
        showError('Error: ' + error.message);
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
    
    const levelBadge = '<span class="log-level-badge ' + level + '">' + level + '</span>';
    const header = '<div class="log-header">' + levelBadge + '</div>';
    const msg = '<div class="log-message">' + message + '</div>';
    const context = '<div class="log-context-grid"><div class="log-context-item"><span class="log-context-label">Module:</span><span>' + module + '</span></div><div class="log-context-item"><span class="log-context-label">Line:</span><span>' + line + '</span></div><div class="log-context-item"><span class="log-context-label">PID:</span><span>' + processId + '</span></div></div>';
    const ts = '<div class="log-timestamp">' + timestamp + '</div>';
    
    div.innerHTML = ts + header + msg + context;
    
    return div;
}

function createExplanationItem(data) {
    const div = document.createElement('div');
    div.className = 'explanation-item';
    
    const severity = data.severity || 'low';
    const explanation = data.explanation || 'Processing...';
    const suggestion = data.suggestion || 'Monitor system status.';
    
    const severityBadge = '<div class="severity-badge ' + severity + '">' + severity.toUpperCase() + '</div>';
    const explanationText = '<div class="explanation-text">' + explanation + '</div>';
    const suggestionBox = '<div class="suggestion-box"><strong>Action:</strong> ' + suggestion + '</div>';
    
    div.innerHTML = severityBadge + explanationText + suggestionBox;
    
    return div;
}

function addScenarioSummary(data) {
    const explanationsContainer = document.getElementById('explanations-container');
    const summary = document.createElement('div');
    summary.className = 'explanation-item scenario-summary';
    
    let actions = '';
    if (data.recommended_actions && Array.isArray(data.recommended_actions)) {
        actions = '<div class="scenario-actions"><h4>Recommended Actions</h4><ul>';
        data.recommended_actions.forEach(function(a) {
            actions += '<li>' + a + '</li>';
        });
        actions += '</ul></div>';
    }
    
    const rootCause = data.root_cause || 'Analyzing...';
    const summaryText = data.summary || '';
    
    summary.innerHTML = '<div class="explanation-text">Scenario: ' + (data.scenario || 'Unknown') + '</div><div class="suggestion-box"><strong>Root Cause:</strong> ' + rootCause + '</div>' + (summaryText ? '<div class="explanation-text" style="margin-top: 8px; font-size: 11px; color: #6b7280;">' + summaryText + '</div>' : '') + actions;
    
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
        setTimeout(() => { error.classList.add('hidden'); }, 4000);
    }
}

function updateCounts() {
    const logsCount = document.getElementById('logs-count');
    if (logsCount) logsCount.textContent = logsList.length;
}

function clearAll() {
    logsList = [];
    explanationsList = [];
    const logsContainer = document.getElementById('logs-container');
    const explanationsContainer = document.getElementById('explanations-container');
    logsContainer.innerHTML = '<div class="empty-state"><p>Click "Generate Log" or select a scenario to view logs.</p></div>';
    explanationsContainer.innerHTML = '<div class="empty-state"><p>Analysis results appear here.</p></div>';
    updateCounts();
}

function refreshPage() {
    location.reload();
}
