#!/usr/bin/env python3
"""
IDS Continuous Monitoring Script
Generates logs and attacks continuously to populate the dashboard with data
"""

import requests
import random
import time
from datetime import datetime
import threading

BASE_URL = 'http://localhost:5001'

# Realistic attack payloads in proper Nginx format
SUSPICIOUS_WEB_LOGS = [
    '192.168.1.200 - - [27/Nov/2025:12:57:11 +0000] "GET /admin?cmd=whoami HTTP/1.1" 200 1024 "-" "curl/7.64.1"',
    '10.0.0.99 - - [27/Nov/2025:12:57:12 +0000] "POST /login HTTP/1.1" 401 512 "-" "sqlmap/1.4.5"',
    '172.16.0.50 - - [27/Nov/2025:12:57:13 +0000] "GET /../../../etc/passwd HTTP/1.1" 400 256 "-" "Mozilla"',
    '192.168.1.150 - - [27/Nov/2025:12:57:14 +0000] "GET /?id=<script>alert(1)</script> HTTP/1.1" 200 2048 "-" "Mozilla"',
    '10.0.0.88 - - [27/Nov/2025:12:57:15 +0000] "GET /search?q=%27%20OR%20%271%27=%271 HTTP/1.1" 200 1024 "-" "curl/7.64.1"',
    '192.168.1.180 - - [27/Nov/2025:12:57:16 +0000] "POST /api/upload HTTP/1.1" 400 256 "-" "wget/1.20.3"',
]

NORMAL_WEB_LOGS = [
    '192.168.1.100 - - [27/Nov/2025:12:57:11 +0000] "GET /index.html HTTP/1.1" 200 4096 "-" "Mozilla/5.0"',
    '192.168.1.101 - - [27/Nov/2025:12:57:12 +0000] "POST /api/users HTTP/1.1" 201 512 "-" "curl/7.64.1"',
    '10.0.0.50 - - [27/Nov/2025:12:57:13 +0000] "GET /images/logo.png HTTP/1.1" 200 8192 "-" "Mozilla/5.0"',
    '172.16.0.20 - - [27/Nov/2025:12:57:14 +0000] "GET /api/products HTTP/1.1" 200 2048 "-" "curl/7.64.1"',
    '192.168.1.102 - - [27/Nov/2025:12:57:15 +0000] "DELETE /api/users/123 HTTP/1.1" 204 0 "-" "curl/7.64.1"',
]

NORMAL_SQL_QUERIES = [
    "SELECT * FROM users WHERE id=1",
    "SELECT * FROM products ORDER BY price DESC LIMIT 10",
    "UPDATE users SET last_login=NOW() WHERE id=123",
    "INSERT INTO logs (action, timestamp) VALUES ('login', NOW())",
    "SELECT COUNT(*) FROM orders WHERE status='pending'",
]

SUSPICIOUS_SQL_QUERIES = [
    "SELECT * FROM users WHERE username='admin' AND password='password123'",
    "SELECT * FROM users WHERE id=1 OR 1=1",
    "SELECT * FROM users UNION SELECT * FROM admins",
    "SELECT * FROM users WHERE name LIKE '%'; DROP TABLE users; --'",
    "SELECT * FROM users WHERE id=1; DROP TABLE logs; --",
    "UPDATE users SET role='admin' WHERE id=1 OR 1=1",
    "DELETE FROM users WHERE 1=1",
]

def send_log(log_line, log_type='web'):
    """Send a log to the IDS for analysis"""
    try:
        response = requests.post(
            f'{BASE_URL}/api/ids/analyze',
            json={'type': log_type, 'log_line': log_line},
            timeout=3
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get('alert') is not None
        return False
    except:
        return False

def generate_web_logs_batch(suspicious=False, count=5):
    """Generate batch of web logs and return alert count"""
    logs = random.sample(SUSPICIOUS_WEB_LOGS if suspicious else NORMAL_WEB_LOGS, min(count, len(SUSPICIOUS_WEB_LOGS if suspicious else NORMAL_WEB_LOGS)))
    alerts = 0
    for log in logs:
        if send_log(log, 'web'):
            alerts += 1
    return alerts, len(logs)

def generate_db_logs_batch(suspicious=False, count=5):
    """Generate batch of database logs and return alert count"""
    if suspicious:
        queries = random.choices(SUSPICIOUS_SQL_QUERIES, k=count)
    else:
        queries = random.choices(NORMAL_SQL_QUERIES, k=count)
    
    alerts = 0
    for query in queries:
        if send_log(query, 'db'):
            alerts += 1
    return alerts, len(queries)

def get_status():
    """Get current IDS status"""
    try:
        response = requests.get(f'{BASE_URL}/api/ids/status', timeout=3)
        if response.status_code == 200:
            data = response.json()
            return data['statistics']
        return None
    except:
        return None

def continuous_monitoring(duration_seconds=300, interval=10):
    """Run continuous monitoring and log generation"""
    print("\n" + "╔" + "═" * 76 + "╗")
    print("║" + " " * 18 + "IDS CONTINUOUS MONITORING MODE" + " " * 28 + "║")
    print("╚" + "═" * 76 + "╝\n")
    
    start_time = time.time()
    iteration = 0
    total_alerts = 0
    
    print(f"📊 Starting continuous monitoring for {duration_seconds} seconds")
    print(f"🔄 Generating logs every {interval} seconds\n")
    
    while time.time() - start_time < duration_seconds:
        iteration += 1
        elapsed = int(time.time() - start_time)
        
        print(f"\n[{elapsed}s] Iteration {iteration}")
        print("─" * 76)
        
        # Generate mix of normal and suspicious logs
        if iteration % 3 == 0:
            # Suspicious round (every 3rd iteration)
            logs = random.sample(SUSPICIOUS_WEB_LOGS, 2)
            log_type = "web"
            print("🔴 Testing SUSPICIOUS web logs...")
        else:
            # Normal round
            logs = random.sample(NORMAL_WEB_LOGS, 2)
            log_type = "web"
            print("🟢 Testing NORMAL web logs...")
        
        alerts_this_round = 0
        for log in logs:
            if send_log(log, log_type):
                alerts_this_round += 1
                print(f"   ✅ Alert triggered")
            else:
                print(f"   ✓ Log analyzed")
        
        total_alerts += alerts_this_round
        
        # Get current status
        stats = get_status()
        if stats:
            print(f"   📊 Total Alerts: {stats.get('total_alerts', 0)}")
        
        # Wait before next iteration
        remaining = duration_seconds - (time.time() - start_time)
        if remaining > 0:
            wait_time = min(interval, remaining)
            time.sleep(wait_time)
    
    # Final summary
    print("\n" + "═" * 76)
    print("MONITORING COMPLETE")
    print("═" * 76)
    
    stats = get_status()
    if stats:
        print(f"\n📊 Final Statistics:")
        print(f"   Total Alerts Created: {stats.get('total_alerts', 0)}")
        print(f"   Alert Types: {len(stats.get('alert_types', {}))}")
        for alert_type, count in stats.get('alert_types', {}).items():
            print(f"      • {alert_type}: {count}")
        print(f"   Severity Distribution:")
        for severity, count in stats.get('severity_distribution', {}).items():
            print(f"      • {severity}: {count}")
    
    print(f"\n✅ Completed {iteration} iterations in {int(time.time() - start_time)} seconds")
    print(f"📈 Total Alerts Detected: {total_alerts}\n")

def quick_test():
    """Run a quick test to verify IDS is working"""
    print("\n" + "╔" + "═" * 76 + "╗")
    print("║" + " " * 28 + "QUICK IDS TEST" + " " * 32 + "║")
    print("╚" + "═" * 76 + "╝\n")
    
    # Test normal web log
    print("1️⃣  Testing NORMAL web log...")
    normal = NORMAL_WEB_LOGS[0]
    if send_log(normal, 'web'):
        print("   ⚠️  Alert triggered (unexpected)")
    else:
        print("   ✅ Normal log passed (as expected)\n")
    
    # Test suspicious web log
    print("2️⃣  Testing SUSPICIOUS web log...")
    suspicious = SUSPICIOUS_WEB_LOGS[0]
    if send_log(suspicious, 'web'):
        print("   ✅ Alert triggered (as expected)\n")
    else:
        print("   ⚠️  No alert (may need tuning)\n")
    
    # Test normal SQL query
    print("3️⃣  Testing NORMAL SQL query...")
    normal_query = NORMAL_SQL_QUERIES[0]
    if send_log(normal_query, 'db'):
        print("   ⚠️  Alert triggered (unexpected)")
    else:
        print("   ✅ Normal query passed (as expected)\n")
    
    # Test suspicious SQL query
    print("4️⃣  Testing SUSPICIOUS SQL query...")
    suspicious_query = SUSPICIOUS_SQL_QUERIES[0]
    if send_log(suspicious_query, 'db'):
        print("   ✅ Alert triggered (as expected)\n")
    else:
        print("   ⚠️  No alert (may need tuning)\n")
    
    # Show status
    print("5️⃣  Current IDS Status:")
    stats = get_status()
    if stats:
        print(f"   Total Alerts: {stats.get('total_alerts', 0)}")
        print(f"   Models Loaded: {all(stats.get('models_loaded', {}).values())}")
        print()
    
    print("✅ Quick test complete!\n")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'quick':
            quick_test()
        elif sys.argv[1] == 'monitor':
            duration = int(sys.argv[2]) if len(sys.argv) > 2 else 300
            continuous_monitoring(duration)
        else:
            print("Usage: python3 ids_monitor.py [quick|monitor] [duration_seconds]")
    else:
        # Default: quick test then 60 second monitoring
        quick_test()
        print("Starting 60-second monitoring...")
        continuous_monitoring(60)
