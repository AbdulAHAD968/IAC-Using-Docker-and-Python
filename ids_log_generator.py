#!/usr/bin/env python3
"""
IDS Log Generator and Attack Simulator
Generates realistic logs from web, database, and email servers
Feeds them to the IDS for threat detection
"""

import requests
import subprocess
import time
import random
from datetime import datetime, timedelta
import json

BASE_URL = 'http://localhost:5001'

# ==================== LOG COLLECTION ====================

def get_nginx_logs(container_name):
    """Collect Nginx access logs from a container"""
    try:
        result = subprocess.run(
            ['docker', 'exec', container_name, 'cat', '/var/log/nginx/access.log'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout.split('\n') if result.returncode == 0 else []
    except Exception as e:
        print(f"❌ Error getting Nginx logs from {container_name}: {e}")
        return []

def get_mysql_logs(container_name):
    """Collect MySQL query logs from a container"""
    try:
        result = subprocess.run(
            ['docker', 'exec', container_name, 'bash', '-c', 
             'mysql -u root -proot -e "SELECT * FROM mysql.general_log LIMIT 50;" 2>/dev/null'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout.split('\n') if result.returncode == 0 else []
    except Exception as e:
        print(f"❌ Error getting MySQL logs from {container_name}: {e}")
        return []

def get_email_logs(container_name):
    """Collect email server logs"""
    try:
        result = subprocess.run(
            ['docker', 'logs', container_name],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout.split('\n') if result.returncode == 0 else []
    except Exception as e:
        print(f"❌ Error getting email logs from {container_name}: {e}")
        return []

# ==================== LOG ANALYSIS ====================

def analyze_web_logs():
    """Collect and analyze web server logs"""
    print("\n📡 Analyzing Web Server Logs...")
    print("   " + "─" * 60)
    
    for container in ['web-server-1', 'web-server-2']:
        logs = get_nginx_logs(container)
        valid_logs = [log for log in logs if log.strip()]
        
        if valid_logs:
            print(f"   Found {len(valid_logs)} log lines from {container}")
            
            # Analyze each log
            analyzed = 0
            for log in valid_logs[-10:]:  # Analyze last 10 logs
                try:
                    response = requests.post(
                        f'{BASE_URL}/api/ids/analyze',
                        json={'type': 'web', 'log_line': log},
                        timeout=5
                    )
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('alert'):
                            print(f"   🚨 ALERT: {data['alert']['alert_type']} - {data['alert']['attack_type']}")
                        analyzed += 1
                except:
                    pass
            
            print(f"   ✅ Analyzed {analyzed} web logs")

def analyze_db_logs():
    """Collect and analyze database logs"""
    print("\n🗄️  Analyzing Database Logs...")
    print("   " + "─" * 60)
    
    logs = get_mysql_logs('db-server-1')
    valid_logs = [log for log in logs if log.strip() and 'SELECT' in log.upper()]
    
    if valid_logs:
        print(f"   Found {len(valid_logs)} database queries")
        
        # Analyze queries
        analyzed = 0
        for query in valid_logs[-10:]:
            try:
                response = requests.post(
                    f'{BASE_URL}/api/ids/analyze',
                    json={'type': 'db', 'log_line': query},
                    timeout=5
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get('alert'):
                        print(f"   🚨 ALERT: {data['alert']['alert_type']}")
                    analyzed += 1
            except:
                pass
        
        print(f"   ✅ Analyzed {analyzed} database logs")
    else:
        print("   ℹ️  No database queries found in logs")

def analyze_email_logs():
    """Collect and analyze email server logs"""
    print("\n📧 Analyzing Email Server Logs...")
    print("   " + "─" * 60)
    
    logs = get_email_logs('email-server-1')
    valid_logs = [log for log in logs if log.strip()]
    
    if valid_logs:
        print(f"   Found {len(valid_logs)} email server events")
        
        # Analyze logs
        analyzed = 0
        for log in valid_logs[-10:]:
            try:
                response = requests.post(
                    f'{BASE_URL}/api/ids/analyze',
                    json={'type': 'email', 'log_line': log},
                    timeout=5
                )
                if response.status_code == 200:
                    analyzed += 1
            except:
                pass
        
        print(f"   ✅ Analyzed {analyzed} email logs")

# ==================== ATTACK SIMULATION ====================

def generate_and_test_attacks():
    """Generate attack simulations and feed them to IDS"""
    print("\n🎯 Generating and Testing Attack Simulations...")
    print("   " + "─" * 60)
    
    attack_configs = [
        ('sql_injection', 'db', 5),
        ('xss', 'web', 5),
        ('brute_force', 'web', 3),
        ('path_traversal', 'web', 3),
    ]
    
    total_alerts = 0
    
    for attack_type, target_type, count in attack_configs:
        print(f"\n   🔴 {attack_type.upper()} Attacks:")
        
        # Generate attacks
        try:
            response = requests.post(
                f'{BASE_URL}/api/ids/test-attack',
                json={'attack_type': attack_type, 'count': count},
                timeout=5
            )
            
            if response.status_code != 200:
                print(f"      ❌ Failed to generate {attack_type}")
                continue
            
            data = response.json()
            simulations = data.get('simulations', [])
            print(f"      Generated {len(simulations)} payloads")
            
            # Analyze attacks
            alerts_created = 0
            for sim in simulations:
                try:
                    response = requests.post(
                        f'{BASE_URL}/api/ids/analyze',
                        json={'type': target_type, 'log_line': sim},
                        timeout=5
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        if result.get('alert'):
                            alerts_created += 1
                            alert = result['alert']
                            confidence = alert.get('confidence', 0)
                            print(f"      ✅ {alert['severity']}: {alert['attack_type']} (Conf: {confidence:.2%})")
                except:
                    pass
            
            total_alerts += alerts_created
            print(f"      → {alerts_created} alerts created from {attack_type}")
            
        except Exception as e:
            print(f"      ❌ Error: {e}")
    
    return total_alerts

# ==================== MAIN ====================

def main():
    """Main execution"""
    print("\n" + "╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "IDS LOG GENERATOR AND ATTACK SIMULATOR" + " " * 13 + "║")
    print("╚" + "═" * 68 + "╝")
    
    print(f"\n⏰ Starting at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Target: {BASE_URL}")
    
    start_time = time.time()
    
    try:
        # Step 1: Collect and analyze real logs
        print("\n" + "─" * 70)
        print("PHASE 1: REAL LOG ANALYSIS")
        print("─" * 70)
        
        analyze_web_logs()
        analyze_db_logs()
        analyze_email_logs()
        
        # Step 2: Generate and test attacks
        print("\n" + "─" * 70)
        print("PHASE 2: ATTACK SIMULATION AND DETECTION")
        print("─" * 70)
        
        alerts = generate_and_test_attacks()
        
        # Step 3: Get final IDS status
        print("\n" + "─" * 70)
        print("PHASE 3: FINAL IDS STATUS")
        print("─" * 70)
        
        response = requests.get(f'{BASE_URL}/api/ids/status', timeout=5)
        if response.status_code == 200:
            data = response.json()
            stats = data['statistics']
            print(f"\n📊 IDS Statistics:")
            print(f"   Total Alerts: {stats['total_alerts']}")
            print(f"   Alert Types: {len(stats['alert_types'])}")
            for alert_type, count in stats.get('alert_types', {}).items():
                print(f"      • {alert_type}: {count}")
            
            # Get alerts
            response = requests.get(f'{BASE_URL}/api/ids/alerts?limit=10', timeout=5)
            if response.status_code == 200:
                alerts_data = response.json()
                alert_list = alerts_data.get('alerts', [])
                if alert_list:
                    print(f"\n🚨 Recent Alerts:")
                    for alert in alert_list[-5:]:
                        print(f"   {alert['timestamp']}: {alert['severity']} - {alert['alert_type']}")
        
        elapsed = time.time() - start_time
        print(f"\n✅ Complete! Took {elapsed:.2f} seconds")
        print(f"📡 Total Alerts Detected: {alerts}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
