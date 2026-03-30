const API_BASE = 'http://llm-service:8000';
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
        const response = await fetch(API_BASE + '/fetch-and-explain?scenario=' + scenario);
        if (!response.ok) throw new Error('Failed to fetch scenario');
        const data = await response.json();
        if (data.log_explanations) {
            logsList = [];
            explanationsList = [];
            data.log_explanations.forEach(exp => {
                addLogAndExplanation(exp);
            });
            addScenarioSummary(data);
        } else {
            addLogAndExplanation(data);
        }
    } catch (error) {
        showError('Failed to analyze scenario: ' + error.message);
    } finally {
        showLoading(false);
    }
}

function addLogAndExplanation(data) {
    const logItem = createLogItem(data);
    const explanationItem = createExplanationItem(data);
    
    const logsContainer = document.getElementById('logs-container');
    const explanationsContainer = document.getElementById('explanations-container');
    
    if (logsContainer.querySelector('.empty-state')) {
        logsContainer.innerHTML = '';
    }
    if (explanationsContainer.querySelector('.empty-state')) {
        explanationsContainer.innerHTML = '';
    }
    
    logsContainer.appendChild(logItem);
    explanationsContainer.appendChild(explanationItem);
    
    logsList.push(data);
    explanationsList.push(data);
    
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
    const explanation = data.explanation || 'No explanation available.';
    const suggestion = data.suggestion || 'Monitor system status.';
    
    div.innerHTML = '<div class="severity-badge ' + severity + '">' + severity + '</div><div class="explanation-text">' + explanation + '</div><div class="suggestion-box"><strong>Recommended Action:</strong><br>' + suggestion + '</div>';
    
    return div;
}

function addScenarioSummary(data) {
    const explanationsContainer = document.getElementById('explanations-container');
    const summary = document.createElement('div');
    summary.className = 'explanation-item';
    summary.style.background = 'rgba(37, 99, 235, 0.1)';
    summary.style.borderLeft = '4px solid var(--primary)';
    
    let actions = '';
    if (data.recommended_actions) {
        actions = '<div style="margin-top: 12px;"><strong style="color: var(--primary);">Actions:</strong><ul style="margin-left: 20px; margin-top: 8px;">';
        data.recommended_actions.forEach(function(a) {
            actions += '<li>' + a + '</li>';
        });
        actions += '</ul></div>';
    }
    
    summary.innerHTML = '<div style="color: var(--primary); font-weight: 700; margin-bottom: 10px;">Scenario Analysis: ' + (data.scenario || 'Unknown') + '</div><div class="explanation-text">' + (data.summary || '') + '</div><div class="suggestion-box"><strong>Root Cause:</strong><br>' + (data.root_cause || 'Analysis in progress...') + '</div>' + actions;
    
    explanationsContainer.insertBefore(summary, explanationsContainer.firstChild);
}

function refreshLogs() {
    if (logsList.length > 0) {
        generateRandomLog();
    }
}

function clearAll() {
    logsList = [];
    explanationsList = [];
    document.getElementById('logs-container').innerHTML = '<div class="empty-state"><p>No logs yet. Click a button above to generate or analyze logs.</p></div>';
    document.getElementById('explanations-container').innerHTML = '<div class="empty-state"><p>Explanations will appear here.</p></div>';
    updateCounts();
}

function updateCounts() {
    document.getElementById('log-count').textContent = logsList.length + ' logs';
    document.getElementById('analysis-count').textContent = explanationsList.length + ' analyzed';
}

function showLoading(show) {
    const modal = document.getElementById('loading-modal');
    if (show) {
        modal.classList.remove('hidden');
    } else {
        modal.classList.add('hidden');
    }
}

function showError(message) {
    const toast = document.getElementById('error-toast');
    toast.textContent = message;
    toast.classList.remove('hidden');
    setTimeout(function() {
        toast.classList.add('hidden');
    }, 5000);
}
