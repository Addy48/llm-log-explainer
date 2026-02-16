from flask import Flask, jsonify, request
from datetime import datetime, timedelta
import random
import uuid

app = Flask(__name__)

# Realistic log message templates categorized by severity
LOG_TEMPLATES = {
    'ERROR': [
        {'message': 'Database connection timeout after 30 seconds', 'module': 'db_handler'},
        {'message': 'Failed to authenticate user: invalid credentials', 'module': 'auth_service'},
        {'message': 'FileNotFoundError: config.yaml not found in /etc/app/', 'module': 'config_loader'},
        {'message': 'OutOfMemoryError: Java heap space exceeded', 'module': 'memory_manager'},
        {'message': 'Connection refused to Redis server at 127.0.0.1:6379', 'module': 'cache_service'},
        {'message': 'SSL certificate verification failed for api.external.com', 'module': 'http_client'},
        {'message': 'Deadlock detected in transaction processing', 'module': 'transaction_handler'},
        {'message': 'Maximum retry attempts exceeded for message queue', 'module': 'mq_consumer'}
    ],
    'WARNING': [
        {'message': 'High memory usage detected: 85% of available RAM', 'module': 'system_monitor'},
        {'message': 'Slow query detected: SELECT took 3.2 seconds', 'module': 'db_handler'},
        {'message': 'API rate limit approaching: 450/500 requests used', 'module': 'api_gateway'},
        {'message': 'Disk space running low: 15% remaining on /dev/sda1', 'module': 'disk_monitor'},
        {'message': 'Deprecated function called: use new_method() instead', 'module': 'legacy_adapter'},
        {'message': 'Session expiring in 5 minutes for user_id=12847', 'module': 'session_manager'},
        {'message': 'Connection pool near capacity: 48/50 connections in use', 'module': 'pool_manager'}
    ],
    'INFO': [
        {'message': 'Server started successfully on port 8080', 'module': 'main'},
        {'message': 'User login successful: user_id=12847', 'module': 'auth_service'},
        {'message': 'Request processed in 145ms: GET /api/users', 'module': 'request_handler'},
        {'message': 'Database migration completed: version 2.3.1', 'module': 'migration_runner'},
        {'message': 'Cache refreshed: 1247 entries updated', 'module': 'cache_service'},
        {'message': 'Scheduled job completed: daily_report_generation', 'module': 'scheduler'},
        {'message': 'New connection established from 192.168.1.105', 'module': 'connection_handler'},
        {'message': 'Configuration reloaded from environment variables', 'module': 'config_loader'}
    ]
}

# Correlated log sequences simulating real failure scenarios
SCENARIOS = {
    'database_failure': [
        {'level': 'INFO', 'message': 'Initiating database connection to postgres://db.internal:5432', 'module': 'db_handler', 'delay': 0},
        {'level': 'INFO', 'message': 'Connection pool initialized with max_connections=50', 'module': 'pool_manager', 'delay': 1},
        {'level': 'WARNING', 'message': 'Connection attempt 1 failed: connection timed out', 'module': 'db_handler', 'delay': 5},
        {'level': 'INFO', 'message': 'Retry scheduled in 2 seconds (attempt 2/5)', 'module': 'db_handler', 'delay': 2},
        {'level': 'WARNING', 'message': 'Connection attempt 2 failed: connection timed out', 'module': 'db_handler', 'delay': 5},
        {'level': 'INFO', 'message': 'Retry scheduled in 4 seconds (attempt 3/5)', 'module': 'db_handler', 'delay': 4},
        {'level': 'WARNING', 'message': 'Connection attempt 3 failed: host unreachable', 'module': 'db_handler', 'delay': 5},
        {'level': 'ERROR', 'message': 'Database connection failed after 5 retry attempts', 'module': 'db_handler', 'delay': 0},
        {'level': 'ERROR', 'message': 'Critical service dependency unavailable: database', 'module': 'health_checker', 'delay': 1},
        {'level': 'WARNING', 'message': 'Switching to degraded mode: read-only cache serving', 'module': 'fallback_handler', 'delay': 0}
    ],
    'auth_breach': [
        {'level': 'INFO', 'message': 'Login attempt from IP 203.45.67.89 for user admin@company.com', 'module': 'auth_service', 'delay': 0},
        {'level': 'WARNING', 'message': 'Failed login attempt 1/5 for admin@company.com: incorrect password', 'module': 'auth_service', 'delay': 2},
        {'level': 'WARNING', 'message': 'Failed login attempt 2/5 for admin@company.com: incorrect password', 'module': 'auth_service', 'delay': 1},
        {'level': 'WARNING', 'message': 'Failed login attempt 3/5 for admin@company.com: incorrect password', 'module': 'auth_service', 'delay': 1},
        {'level': 'WARNING', 'message': 'Unusual login pattern detected: rapid successive attempts', 'module': 'anomaly_detector', 'delay': 0},
        {'level': 'WARNING', 'message': 'Failed login attempt 4/5 for admin@company.com: incorrect password', 'module': 'auth_service', 'delay': 1},
        {'level': 'ERROR', 'message': 'Account locked: admin@company.com exceeded maximum login attempts', 'module': 'auth_service', 'delay': 1},
        {'level': 'WARNING', 'message': 'Security alert triggered: potential brute force attack from 203.45.67.89', 'module': 'security_monitor', 'delay': 0},
        {'level': 'INFO', 'message': 'IP 203.45.67.89 added to temporary block list for 30 minutes', 'module': 'firewall_manager', 'delay': 1},
        {'level': 'INFO', 'message': 'Security notification sent to admin@company.com via email', 'module': 'notification_service', 'delay': 2}
    ],
    'memory_leak': [
        {'level': 'INFO', 'message': 'Application started with initial heap size 512MB', 'module': 'jvm_monitor', 'delay': 0},
        {'level': 'INFO', 'message': 'Memory usage: 45% (230MB/512MB)', 'module': 'system_monitor', 'delay': 10},
        {'level': 'INFO', 'message': 'Memory usage: 58% (297MB/512MB)', 'module': 'system_monitor', 'delay': 10},
        {'level': 'WARNING', 'message': 'Memory usage trending upward: 72% (368MB/512MB)', 'module': 'system_monitor', 'delay': 10},
        {'level': 'INFO', 'message': 'Garbage collection triggered: freed 45MB', 'module': 'gc_handler', 'delay': 2},
        {'level': 'WARNING', 'message': 'Memory usage still high after GC: 68% (348MB/512MB)', 'module': 'system_monitor', 'delay': 5},
        {'level': 'WARNING', 'message': 'Potential memory leak detected in module: image_processor', 'module': 'leak_detector', 'delay': 3},
        {'level': 'WARNING', 'message': 'Memory usage critical: 89% (456MB/512MB)', 'module': 'system_monitor', 'delay': 10},
        {'level': 'ERROR', 'message': 'OutOfMemoryError: Java heap space exhausted', 'module': 'jvm_monitor', 'delay': 5},
        {'level': 'ERROR', 'message': 'Application crash: initiating emergency restart', 'module': 'process_manager', 'delay': 0},
        {'level': 'INFO', 'message': 'Heap dump saved to /var/logs/heapdump_20260209_143052.hprof', 'module': 'diagnostic_handler', 'delay': 3}
    ],
    'api_overload': [
        {'level': 'INFO', 'message': 'API request rate: 120 requests/minute', 'module': 'rate_limiter', 'delay': 0},
        {'level': 'INFO', 'message': 'API request rate: 280 requests/minute', 'module': 'rate_limiter', 'delay': 5},
        {'level': 'WARNING', 'message': 'API rate limit 75% consumed: 375/500 requests this window', 'module': 'rate_limiter', 'delay': 5},
        {'level': 'WARNING', 'message': 'Response latency increasing: avg 850ms (threshold 500ms)', 'module': 'performance_monitor', 'delay': 3},
        {'level': 'WARNING', 'message': 'API rate limit 90% consumed: 450/500 requests this window', 'module': 'rate_limiter', 'delay': 2},
        {'level': 'INFO', 'message': 'Auto-scaling triggered: requesting 2 additional instances', 'module': 'scaling_manager', 'delay': 1},
        {'level': 'ERROR', 'message': 'API rate limit exceeded: returning 429 Too Many Requests', 'module': 'rate_limiter', 'delay': 2},
        {'level': 'WARNING', 'message': 'Request queue depth: 847 pending requests', 'module': 'queue_monitor', 'delay': 1},
        {'level': 'INFO', 'message': 'New instance api-server-3 online and accepting traffic', 'module': 'scaling_manager', 'delay': 30},
        {'level': 'INFO', 'message': 'Load balanced: traffic distributed across 3 instances', 'module': 'load_balancer', 'delay': 2},
        {'level': 'INFO', 'message': 'API request rate normalized: 95 requests/minute per instance', 'module': 'rate_limiter', 'delay': 10}
    ],
    'disk_failure': [
        {'level': 'INFO', 'message': 'Disk usage check: /dev/sda1 at 72% capacity', 'module': 'disk_monitor', 'delay': 0},
        {'level': 'WARNING', 'message': 'Disk usage warning: /dev/sda1 at 85% capacity', 'module': 'disk_monitor', 'delay': 60},
        {'level': 'INFO', 'message': 'Log rotation triggered: archived 15 files totaling 2.3GB', 'module': 'log_rotator', 'delay': 5},
        {'level': 'WARNING', 'message': 'Disk usage still critical after cleanup: 82% capacity', 'module': 'disk_monitor', 'delay': 3},
        {'level': 'WARNING', 'message': 'Write latency degraded: 450ms avg (threshold 100ms)', 'module': 'io_monitor', 'delay': 10},
        {'level': 'ERROR', 'message': 'Disk I/O error: read failure on sector 0x7F3A2B1C', 'module': 'disk_driver', 'delay': 5},
        {'level': 'WARNING', 'message': 'SMART warning: disk /dev/sda1 reporting 847 reallocated sectors', 'module': 'smart_monitor', 'delay': 1},
        {'level': 'ERROR', 'message': 'File write failed: /var/data/cache.db - I/O error', 'module': 'file_handler', 'delay': 2},
        {'level': 'WARNING', 'message': 'Disk health critical: immediate replacement recommended', 'module': 'smart_monitor', 'delay': 0},
        {'level': 'INFO', 'message': 'Failover initiated: redirecting writes to backup volume /dev/sdb1', 'module': 'storage_manager', 'delay': 3}
    ]
}

# Request tracking for correlation
request_context = {}

def generate_request_id():
    """Generate a unique request ID for log correlation."""
    return f"req_{uuid.uuid4().hex[:12]}"

def generate_timestamp(base_time, delay_seconds):
    """Generate timestamp with specified delay from base time."""
    return (base_time + timedelta(seconds=delay_seconds)).isoformat()

def generate_log_entry(level=None, request_id=None):
    """Generate a single realistic log entry."""
    if level is None:
        level = random.choices(
            ['ERROR', 'WARNING', 'INFO'],
            weights=[0.2, 0.3, 0.5]
        )[0]
    
    template = random.choice(LOG_TEMPLATES[level])
    
    return {
        'id': str(uuid.uuid4()),
        'request_id': request_id or generate_request_id(),
        'timestamp': datetime.now().isoformat(),
        'level': level,
        'message': template['message'],
        'context': {
            'module': template['module'],
            'line': random.randint(10, 500),
            'process_id': random.randint(1000, 9999),
            'thread_id': f"thread-{random.randint(1, 16)}"
        }
    }

def generate_scenario_logs(scenario_name):
    """Generate a correlated sequence of logs for a given scenario."""
    if scenario_name not in SCENARIOS:
        return None
    
    scenario = SCENARIOS[scenario_name]
    base_time = datetime.now()
    request_id = generate_request_id()
    cumulative_delay = 0
    logs = []
    
    for entry in scenario:
        cumulative_delay += entry['delay']
        log = {
            'id': str(uuid.uuid4()),
            'request_id': request_id,
            'timestamp': generate_timestamp(base_time, cumulative_delay),
            'level': entry['level'],
            'message': entry['message'],
            'context': {
                'module': entry['module'],
                'line': random.randint(10, 500),
                'process_id': random.randint(1000, 9999),
                'thread_id': 'thread-1'
            }
        }
        logs.append(log)
    
    return logs

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for container orchestration."""
    return jsonify({
        'status': 'healthy',
        'service': 'log-generator',
        'version': '1.1.0',
        'available_scenarios': list(SCENARIOS.keys())
    })

# Single log generation endpoints
@app.route('/generate', methods=['GET'])
def generate_single_log():
    """Generate a single random log entry."""
    level = request.args.get('level', None)
    if level and level.upper() not in LOG_TEMPLATES:
        return jsonify({'error': 'Invalid level. Use ERROR, WARNING, or INFO'}), 400
    
    log_entry = generate_log_entry(level.upper() if level else None)
    return jsonify(log_entry)

@app.route('/generate/batch', methods=['GET'])
def generate_batch_logs():
    """Generate multiple random log entries."""
    count = request.args.get('count', 5, type=int)
    count = min(count, 50)
    
    request_id = generate_request_id()
    logs = [generate_log_entry(request_id=request_id) for _ in range(count)]
    return jsonify({'logs': logs, 'count': len(logs), 'request_id': request_id})

@app.route('/generate/error', methods=['GET'])
def generate_error_log():
    """Generate specifically an ERROR level log."""
    return jsonify(generate_log_entry('ERROR'))

@app.route('/generate/warning', methods=['GET'])
def generate_warning_log():
    """Generate specifically a WARNING level log."""
    return jsonify(generate_log_entry('WARNING'))

@app.route('/generate/info', methods=['GET'])
def generate_info_log():
    """Generate specifically an INFO level log."""
    return jsonify(generate_log_entry('INFO'))

# Scenario-based correlated log sequences
@app.route('/scenario', methods=['GET'])
def list_scenarios():
    """List all available failure scenarios."""
    scenario_descriptions = {
        'database_failure': 'Simulates database connection failure with retry logic and fallback',
        'auth_breach': 'Simulates brute force login attempt with account lockout and security response',
        'memory_leak': 'Simulates gradual memory exhaustion leading to application crash',
        'api_overload': 'Simulates API rate limiting and auto-scaling response',
        'disk_failure': 'Simulates disk degradation with SMART warnings and failover'
    }
    return jsonify({
        'available_scenarios': scenario_descriptions,
        'usage': 'GET /scenario/<scenario_name> to generate correlated log sequence'
    })

@app.route('/scenario/<scenario_name>', methods=['GET'])
def get_scenario_logs(scenario_name):
    """Generate a correlated log sequence for a specific failure scenario."""
    logs = generate_scenario_logs(scenario_name)
    
    if logs is None:
        return jsonify({
            'error': f'Unknown scenario: {scenario_name}',
            'available_scenarios': list(SCENARIOS.keys())
        }), 404
    
    return jsonify({
        'scenario': scenario_name,
        'description': f'Correlated log sequence simulating {scenario_name.replace("_", " ")}',
        'log_count': len(logs),
        'logs': logs
    })

# Combined endpoint for LLM service integration
@app.route('/explain-request', methods=['GET'])
def get_logs_for_explanation():
    """
    Primary endpoint for LLM service integration.
    Returns either a single log or a scenario based on query params.
    """
    scenario = request.args.get('scenario', None)
    
    if scenario:
        logs = generate_scenario_logs(scenario)
        if logs is None:
            return jsonify({'error': f'Unknown scenario: {scenario}'}), 404
        return jsonify({
            'type': 'scenario',
            'scenario': scenario,
            'logs': logs
        })
    else:
        log = generate_log_entry()
        return jsonify({
            'type': 'single',
            'logs': [log]
        })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
