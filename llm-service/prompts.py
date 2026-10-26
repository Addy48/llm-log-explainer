EXPLANATION_TEMPLATES = {
    'HIGH': {
        'prefix': 'CRITICAL ISSUE DETECTED.',
        'action': 'Immediate investigation required. Escalate to on-call engineer.'
    },
    'MEDIUM': {
        'prefix': 'WARNING: Potential issue detected.',
        'action': 'Monitor closely. Prepare rollback plan if severity increases.'
    },
    'LOW': {
        'prefix': 'INFO: Normal operation with minor anomalies.',
        'action': 'Log for future reference. No immediate action needed.'
    }
}

SCENARIO_PATTERNS = {
    'database_failure': {
        'root_cause': 'Database server became unreachable due to network partition or service crash.',
        'actions': [
            'Check database server health and connectivity',
            'Verify network routing and firewall rules',
            'Review database logs for errors',
            'Initiate failover if replica available'
        ]
    },
    'auth_breach': {
        'root_cause': 'Unauthorized access attempt detected. Possible credential compromise.',
        'actions': [
            'Isolate affected user accounts immediately',
            'Reset credentials for compromised accounts',
            'Review authentication logs for unauthorized access',
            'Enable additional security monitoring'
        ]
    },
    'memory_leak': {
        'root_cause': 'Memory usage growing uncontrollably. Process leaking resources.',
        'actions': [
            'Identify memory-consuming processes',
            'Review recent code changes for leak sources',
            'Restart affected services',
            'Increase monitoring for memory thresholds'
        ]
    },
    'api_overload': {
        'root_cause': 'API received request volume exceeding capacity. Rate limiting or scaling needed.',
        'actions': [
            'Activate auto-scaling policies',
            'Enable request rate limiting',
            'Route traffic to secondary regions',
            'Notify API consumers of capacity constraints'
        ]
    },
    'disk_failure': {
        'root_cause': 'Disk storage exhausted or hardware failure imminent.',
        'actions': [
            'Clear temporary files and old logs',
            'Activate disk cleanup procedures',
            'Check for corrupted filesystem',
            'Prepare for hardware replacement'
        ]
    },
    'redis_cache_stampede': {
        'root_cause': 'Cache key TTL expired simultaneously under high concurrent traffic, causing a thundering herd where multiple threads bypass cache and saturate backend database.',
        'actions': [
            'Implement probabilistic early expiration (XFetch algorithm) on hot cache keys',
            'Use distributed mutex locks (Redlock) so only one thread recomputes the cache value',
            'Increase Redis connection pool sizing and configure stale-while-revalidate caching headers'
        ]
    }
}

# Per-category explanations used by analyzer.py when no scenario is known.
CATEGORY_PLAYBOOK = {
    'database': {
        'label': 'Database connectivity',
        'summary': 'the service cannot reliably reach or use its database (timeouts, failed retries, lock contention).',
        'root_cause': 'Database became slow or unreachable; callers are timing out and retrying.',
        'actions': SCENARIO_PATTERNS['database_failure']['actions'],
        'low_note': 'Routine database activity.',
        'low_action': 'No action. Keep watching query latency.',
    },
    'security': {
        'label': 'Authentication / security',
        'summary': 'authentication is failing or being abused (repeated bad passwords, lockouts, certificate errors).',
        'root_cause': 'Repeated authentication failures suggest a credential problem or an attack.',
        'actions': SCENARIO_PATTERNS['auth_breach']['actions'],
        'low_note': 'Normal sign-in or security bookkeeping.',
        'low_action': 'No action. Normal auth traffic.',
    },
    'memory': {
        'label': 'Memory pressure',
        'summary': 'memory use is climbing and garbage collection is not reclaiming it, a typical leak pattern.',
        'root_cause': SCENARIO_PATTERNS['memory_leak']['root_cause'],
        'actions': SCENARIO_PATTERNS['memory_leak']['actions'],
        'low_note': 'Memory reading within normal range.',
        'low_action': 'No action. Track the memory trend.',
    },
    'traffic': {
        'label': 'Traffic / rate limiting',
        'summary': 'request volume is above capacity; latency is rising and clients are being throttled.',
        'root_cause': SCENARIO_PATTERNS['api_overload']['root_cause'],
        'actions': SCENARIO_PATTERNS['api_overload']['actions'],
        'low_note': 'Traffic or scaling event within capacity.',
        'low_action': 'No action. Capacity is holding.',
    },
    'storage': {
        'label': 'Disk / storage',
        'summary': 'the disk is running out of space or showing hardware errors.',
        'root_cause': SCENARIO_PATTERNS['disk_failure']['root_cause'],
        'actions': SCENARIO_PATTERNS['disk_failure']['actions'],
        'low_note': 'Routine storage housekeeping.',
        'low_action': 'No action. Disk usage is fine.',
    },
    'cache': {
        'label': 'Cache',
        'summary': 'the cache layer is failing or expired at once, pushing load onto the backend.',
        'root_cause': SCENARIO_PATTERNS['redis_cache_stampede']['root_cause'],
        'actions': SCENARIO_PATTERNS['redis_cache_stampede']['actions'],
        'low_note': 'Normal cache maintenance.',
        'low_action': 'No action. Cache is healthy.',
    },
    'config': {
        'label': 'Configuration',
        'summary': 'a config file or setting is missing, invalid, or deprecated.',
        'root_cause': 'Service started with missing or outdated configuration.',
        'actions': [
            'Confirm the config file exists at the expected path',
            'Diff the deployed config against the last known good version',
            'Replace deprecated calls before the next release',
        ],
        'low_note': 'Configuration loaded normally.',
        'low_action': 'No action. Config reload was clean.',
    },
    'network': {
        'label': 'Network',
        'summary': 'a downstream service is refusing or dropping connections.',
        'root_cause': 'A dependency is unreachable over the network (refused, timed out, or host down).',
        'actions': [
            'Check the dependency is running and listening on the expected port',
            'Verify DNS, security groups and firewall rules',
            'Add retries with backoff and a circuit breaker',
        ],
        'low_note': 'Normal connection activity.',
        'low_action': 'No action. Connections are healthy.',
    },
    'general': {
        'label': 'General',
        'summary': 'no known failure pattern matched this line; review it alongside nearby logs.',
        'root_cause': 'No single failure pattern dominates these logs.',
        'actions': [
            'Read the surrounding log lines for context',
            'Group by request_id to follow one request end to end',
            'Add a rule for this message if it recurs',
        ],
        'low_note': 'Informational, no known risk pattern.',
        'low_action': 'No action needed.',
    },
}

# System prompt for the optional Claude explanation (llm.py).
LLM_SYSTEM_PROMPT = """You are an on-call site reliability engineer. You receive a short window of \
application logs, plus the output of a rule-based pre-classifier. Explain what happened in plain \
language a student could follow: the likely root cause, how the failure unfolded, and what to do \
next. Base every claim on the log lines given; when evidence is thin, say so. Keep the summary to \
three or four sentences and give at most four concrete actions."""
