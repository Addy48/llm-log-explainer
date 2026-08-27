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
