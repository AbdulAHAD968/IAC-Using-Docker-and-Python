#!/usr/bin/env python3
"""
Generate realistic logs in proper format for IDS analysis
"""

import requests
import random
from datetime import datetime, timedelta

BASE_URL = 'http://localhost:5001'

# ==================== REALISTIC LOG GENERATORS ====================

def generate_nginx_logs(count=10):
    """Generate realistic Nginx access logs in Combined format"""
    ips = ['192.168.1.100', '192.168.1.101', '10.0.0.50', '172.16.0.20']
    paths = ['/index.html', '/api/users', '/admin', '/uploads', '/images/file.jpg']
    methods = ['GET', 'POST', 'PUT', 'DELETE']
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Chrome/90.0.4430.85',
        'curl/7.64.1',
        'sqlmap/1.4.5'
    ]
    status_codes = [200, 201, 400, 401, 403, 404, 500, 503]
    
    logs = []
    for _ in range(count):
        ip = random.choice(ips)
        method = random.choice(methods)
        path = random.choice(paths)
        status = random.choice(status_codes)
        bytes_sent = random.randint(1024, 102400)
        referer = random.choice(['"-"', '"https://google.com"', '"https://example.com"'])
        ua = random.choice(user_agents)
        
        timestamp = datetime.now().strftime('%d/%b/%Y:%H:%M:%S +0000')
        
        log = f'{ip} - - [{timestamp}] "{method} {path} HTTP/1.1" {status} {bytes_sent} {referer} "{ua}"'
        logs.append(log)
    
    return logs

def generate_sql_logs(count=10, suspicious=False):
    """Generate realistic SQL queries"""
    normal_queries = [
        "SELECT * FROM users WHERE id=1",
        "SELECT * FROM products ORDER BY price DESC LIMIT 10",
        "UPDATE users SET last_login=NOW() WHERE id=123",
        "INSERT INTO logs (action, timestamp) VALUES ('login', NOW())",
        "DELETE FROM sessions WHERE expires < NOW()",
        "SELECT COUNT(*) FROM orders WHERE status='pending'",
    ]
    
    suspicious_queries = [
        "SELECT * FROM users WHERE username='admin' AND password='password123'",
        "SELECT * FROM users WHERE id=1 OR 1=1",
        "SELECT * FROM users UNION SELECT * FROM admins",
        "SELECT * FROM users WHERE name LIKE '%'; DROP TABLE users; --'",
        "SELECT * FROM users WHERE id=1; DROP TABLE logs; --",
        "UPDATE users SET role='admin' WHERE id=1 OR 1=1",
        "DELETE FROM users WHERE 1=1",
    ]
    
    queries = suspicious_queries if suspicious else normal_queries
    return random.choices(queries, k=count)

def generate_suspicious_logs(count=5):
    """Generate logs with attack patterns"""
    suspicious_nginx = [
        '192.168.1.200 - - [27/Nov/2025:12:57:11 +0000] "GET /admin?cmd=whoami HTTP/1.1" 200 1024 "-" "curl/7.64.1"',
        '10.0.0.99 - - [27/Nov/2025:12:57:12 +0000] "POST /login HTTP/1.1" 401 512 "-" "sqlmap/1.4.5"',
        '172.16.0.50 - - [27/Nov/2025:12:57:13 +0000] "GET /../../../etc/passwd HTTP/1.1" 400 256 "-" "Mozilla"',
        '192.168.1.150 - - [27/Nov/2025:12:57:14 +0000] "GET /?id=<script>alert(1)</script> HTTP/1.1" 200 2048 "-" "Mozilla"',
        '10.0.0.88 - - [27/Nov/2025:12:57:15 +0000] "GET /search?q=%27%20OR%20%271%27=%271 HTTP/1.1" 200 1024 "-" "curl/7.64.1"',
    ]
    
    return suspicious_nginx[:count]

# ==================== ANALYSIS FUNCTIONS ====================

def analyze_logs(logs, log_type='web'):
    """Send logs to IDS for analysis"""
    print(f"\n📊 Analyzing {len(logs)} {log_type} logs...")
    alerts_created = 0
    
    for i, log in enumerate(logs, 1):
        try:
            response = requests.post(
                f'{BASE_URL}/api/ids/analyze',
                json={'type': log_type, 'log_line': log},
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                alert = result.get('alert')
                
                if alert:
                    alerts_created += 1
                    print(f"   ✅ [{i}] {alert['severity']:8} | {alert['alert_type']:15} | Conf: {alert['confidence']:.2%}")
                else:
                    print(f"   ℹ️  [{i}] Normal log")
            else:
                print(f"   ❌ [{i}] Error: {response.status_code}")
        except Exception as e:
            print(f"   ❌ [{i}] Exception: {str(e)[:40]}")
    
    return alerts_created

# ==================== MAIN ====================

def main():
    print("\n" + "╔" + "═" * 68 + "╗")
    print("║" + " " * 12 + "IDS LOG ANALYSIS - REALISTIC LOG GENERATOR" + " " * 15 + "║")
    print("╚" + "═" * 68 + "╝\n")
    
    total_alerts = 0
    
    # Test 1: Normal web logs
    print("1️⃣  PHASE 1: Normal Web Server Logs")
    print("   " + "─" * 64)
    web_logs = generate_nginx_logs(5)
    total_alerts += analyze_logs(web_logs, 'web')
    
    # Test 2: Normal SQL logs
    print("\n2️⃣  PHASE 2: Normal Database Logs")
    print("   " + "─" * 64)
    sql_logs = generate_sql_logs(5)
    total_alerts += analyze_logs(sql_logs, 'db')
    
    # Test 3: Suspicious web logs with attacks
    print("\n3️⃣  PHASE 3: Suspicious Web Logs (Attack Patterns)")
    print("   " + "─" * 64)
    suspicious_logs = generate_suspicious_logs(5)
    total_alerts += analyze_logs(suspicious_logs, 'web')
    
    # Test 4: Attack simulation
    print("\n4️⃣  PHASE 4: Attack Simulation")
    print("   " + "─" * 64)
    
    attack_types = ['sql_injection', 'xss']
    for attack_type in attack_types:
        try:
            response = requests.post(
                f'{BASE_URL}/api/ids/test-attack',
                json={'attack_type': attack_type, 'count': 3},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                attacks = data.get('simulations', [])
                log_type = 'db' if attack_type == 'sql_injection' else 'web'
                
                print(f"\n   🎯 {attack_type.upper()}: {len(attacks)} payloads")
                alerts = analyze_logs(attacks, log_type)
                total_alerts += alerts
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Get final status
    print("\n" + "─" * 68)
    print("5️⃣  FINAL IDS STATUS")
    print("─" * 68)
    
    try:
        response = requests.get(f'{BASE_URL}/api/ids/status', timeout=5)
        data = response.json()
        stats = data['statistics']
        
        print(f"\n📊 Statistics:")
        print(f"   Total Alerts: {stats['total_alerts']}")
        print(f"   Models Loaded: {all(stats['models_loaded'].values())}")
        
        # Get recent alerts
        response = requests.get(f'{BASE_URL}/api/ids/alerts?limit=20', timeout=5)
        alerts_data = response.json()
        alerts_list = alerts_data.get('alerts', [])
        
        if alerts_list:
            print(f"\n🚨 Recent Alerts ({len(alerts_list)}):")
            for alert in alerts_list[-10:]:
                print(f"   • [{alert['severity']:8}] {alert['alert_type']:15} - {alert.get('attack_type', 'N/A')}")
        else:
            print(f"\n📋 No alerts detected")
    except Exception as e:
        print(f"❌ Error getting status: {e}")
    
    print(f"\n✅ Analysis Complete! Total Alerts: {total_alerts}")
    print("╚" + "═" * 68 + "╝\n")

if __name__ == '__main__':
    main()
