#!/usr/bin/env python3
"""
Comprehensive IDS testing script
Tests all three detection models (Web, Database, Email) with realistic attack scenarios
"""

import sys
import json
from cms.ids_manager import IDSManager

def print_header(title):
    print("\n" + "=" * 80)
    print(title.center(80))
    print("=" * 80)

def test_web_detection():
    """Test web server attack detection"""
    print_header("WEB SERVER ATTACK DETECTION")
    
    ids = IDSManager()
    
    test_cases = [
        # Normal traffic
        ('192.168.1.100 - - [27/Nov/2024:10:30:00 +0000] "GET /index.html HTTP/1.1" 200 5678 "-" "Mozilla/5.0"',
         'Normal: Homepage access', False),
        ('192.168.1.101 - - [27/Nov/2024:10:30:01 +0000] "POST /api/login HTTP/1.1" 200 1024 "-" "Mozilla/5.0"',
         'Normal: Login request', False),
        
        # Admin/Command access
        ('10.0.0.1 - - [27/Nov/2024:10:30:02 +0000] "GET /admin HTTP/1.1" 200 2048 "-" "Mozilla/5.0"',
         'Attack: Admin panel access', True),
        ('10.0.0.2 - - [27/Nov/2024:10:30:03 +0000] "GET /?cmd=whoami HTTP/1.1" 200 512 "-" "Mozilla/5.0"',
         'Attack: Command execution attempt', True),
        
        # Path traversal
        ('10.0.0.3 - - [27/Nov/2024:10:30:04 +0000] "GET /../../etc/passwd HTTP/1.1" 403 256 "-" "Mozilla/5.0"',
         'Attack: Path traversal to /etc/passwd', True),
        ('10.0.0.4 - - [27/Nov/2024:10:30:05 +0000] "GET /%2e%2e%2fadmin HTTP/1.1" 200 1024 "-" "Mozilla/5.0"',
         'Attack: URL-encoded path traversal', True),
        
        # XSS/Script injection
        ('10.0.0.5 - - [27/Nov/2024:10:30:06 +0000] "GET /?search=<script>alert(1)</script> HTTP/1.1" 200 2048 "-" "Mozilla/5.0"',
         'Attack: XSS injection', True),
        ('10.0.0.6 - - [27/Nov/2024:10:30:07 +0000] "GET /?url=javascript:eval HTTP/1.1" 200 512 "-" "Mozilla/5.0"',
         'Attack: JavaScript protocol', True),
        
        # SQL injection patterns
        ('10.0.0.7 - - [27/Nov/2024:10:30:08 +0000] "GET /?id=1+OR+1=1 HTTP/1.1" 200 1024 "-" "Mozilla/5.0"',
         'Attack: SQL OR injection', True),
        ('10.0.0.8 - - [27/Nov/2024:10:30:09 +0000] "GET /?search=union+select HTTP/1.1" 200 1536 "-" "Mozilla/5.0"',
         'Attack: UNION SELECT injection', True),
        
        # Suspicious tools
        ('10.0.0.9 - - [27/Nov/2024:10:30:10 +0000] "GET /api/test HTTP/1.1" 200 512 "-" "sqlmap/1.0"',
         'Attack: SQLmap scanner', True),
        ('10.0.0.10 - - [27/Nov/2024:10:30:11 +0000] "GET / HTTP/1.1" 200 512 "-" "nikto/2.1.6"',
         'Attack: Nikto vulnerability scanner', True),
    ]
    
    detected = 0
    for log, description, should_detect in test_cases:
        alert = ids.analyze_web_log(log)
        result = "🚨 DETECTED" if alert else "✅ CLEAR"
        status = "✓" if (alert is not None) == should_detect else "✗"
        
        print(f"{status} {result:15} | {description}")
        if alert and should_detect:
            detected += 1
        elif not alert and not should_detect:
            detected += 1
    
    print(f"\n✅ Web Detection: {detected}/{len(test_cases)} correct")
    return detected == len(test_cases)

def test_database_detection():
    """Test database attack detection"""
    print_header("DATABASE ATTACK DETECTION")
    
    ids = IDSManager()
    
    test_cases = [
        # Normal queries
        ('127.0.0.1 - - [27/Nov/2024:10:30:00 +0000] "SELECT * FROM users WHERE id=1" 200',
         'Normal: Simple SELECT', False),
        ('127.0.0.2 - - [27/Nov/2024:10:30:01 +0000] "SELECT name, email FROM products" 200',
         'Normal: Product query', False),
        
        # SQL injection
        ('10.0.0.1 - - [27/Nov/2024:10:30:02 +0000] "SELECT * FROM users WHERE id=\' OR \'1\'=\'1\'" 200',
         'Attack: OR injection', True),
        ('10.0.0.2 - - [27/Nov/2024:10:30:03 +0000] "SELECT * FROM users UNION SELECT 1,2,3" 200',
         'Attack: UNION injection', True),
        
        # Dangerous operations
        ('10.0.0.3 - - [27/Nov/2024:10:30:04 +0000] "DROP TABLE users;" 403',
         'Attack: DROP TABLE', True),
        ('10.0.0.4 - - [27/Nov/2024:10:30:05 +0000] "TRUNCATE TABLE products;" 403',
         'Attack: TRUNCATE TABLE', True),
        
        # Stacked queries
        ('10.0.0.5 - - [27/Nov/2024:10:30:06 +0000] "SELECT * FROM users; DELETE FROM logs;" 200',
         'Attack: Stacked query with DELETE', True),
        ('10.0.0.6 - - [27/Nov/2024:10:30:07 +0000] "SELECT * FROM users; EXEC xp_cmdshell;" 200',
         'Attack: Stacked with EXEC', True),
    ]
    
    detected = 0
    for log, description, should_detect in test_cases:
        alert = ids.analyze_db_log(log)
        result = "🚨 DETECTED" if alert else "✅ CLEAR"
        status = "✓" if (alert is not None) == should_detect else "✗"
        
        print(f"{status} {result:15} | {description}")
        if alert and should_detect:
            detected += 1
        elif not alert and not should_detect:
            detected += 1
    
    print(f"\n✅ Database Detection: {detected}/{len(test_cases)} correct")
    return detected == len(test_cases)

def test_email_detection():
    """Test email threat detection"""
    print_header("EMAIL THREAT DETECTION")
    
    ids = IDSManager()
    
    test_cases = [
        # Normal email traffic
        ('192.168.1.100 - - [27/Nov/2024:10:30:00 +0000] "GET /mail HTTP/1.1" 200 1024 "-" "Mozilla/5.0"',
         'Normal: Email access', False),
        
        # Phishing
        ('10.0.0.1 - - [27/Nov/2024:10:30:01 +0000] "GET /verify_account HTTP/1.1" 200 2048 "-" "Mozilla/5.0"',
         'Attack: Account verification phishing', True),
        ('10.0.0.2 - - [27/Nov/2024:10:30:02 +0000] "GET /confirm_identity HTTP/1.1" 200 1536 "-" "Mozilla/5.0"',
         'Attack: Identity confirmation phishing', True),
        ('10.0.0.3 - - [27/Nov/2024:10:30:03 +0000] "GET /?urgent=action+required HTTP/1.1" 200 1024 "-" "Mozilla/5.0"',
         'Attack: Urgent action phishing', True),
        
        # Spam/Malware
        ('10.0.0.4 - - [27/Nov/2024:10:30:04 +0000] "GET /viagra HTTP/1.1" 200 512 "-" "Mozilla/5.0"',
         'Attack: Viagra spam', True),
        ('10.0.0.5 - - [27/Nov/2024:10:30:05 +0000] "GET /claim+reward HTTP/1.1" 200 768 "-" "Mozilla/5.0"',
         'Attack: Reward scam', True),
        
        # Dangerous payloads
        ('10.0.0.6 - - [27/Nov/2024:10:30:06 +0000] "GET /malware.exe HTTP/1.1" 200 8192 "-" "Mozilla/5.0"',
         'Attack: Executable attachment', True),
        ('10.0.0.7 - - [27/Nov/2024:10:30:07 +0000] "GET /ransomware.zip HTTP/1.1" 200 4096 "-" "Mozilla/5.0"',
         'Attack: Ransomware archive', True),
        
        # Suspicious clients
        ('10.0.0.8 - - [27/Nov/2024:10:30:08 +0000] "GET /mail HTTP/1.1" 200 1024 "-" "curl/7.64.1"',
         'Attack: Curl email client', True),
        ('10.0.0.9 - - [27/Nov/2024:10:30:09 +0000] "GET /mail HTTP/1.1" 200 1024 "-" "python-requests/2.25.1"',
         'Attack: Python email client', True),
    ]
    
    detected = 0
    for log, description, should_detect in test_cases:
        alert = ids.analyze_email_log(log)
        result = "🚨 DETECTED" if alert else "✅ CLEAR"
        status = "✓" if (alert is not None) == should_detect else "✗"
        
        print(f"{status} {result:15} | {description}")
        if alert and should_detect:
            detected += 1
        elif not alert and not should_detect:
            detected += 1
    
    print(f"\n✅ Email Detection: {detected}/{len(test_cases)} correct")
    return detected == len(test_cases)

def main():
    """Run comprehensive IDS tests"""
    print("\n" + "=" * 80)
    print("COMPREHENSIVE IDS TESTING SUITE".center(80))
    print("Testing Web, Database, and Email threat detection models".center(80))
    print("=" * 80)
    
    results = {
        'web': test_web_detection(),
        'database': test_database_detection(),
        'email': test_email_detection(),
    }
    
    print_header("FINAL RESULTS")
    
    for model_type, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} | {model_type.upper()} Detection")
    
    all_passed = all(results.values())
    print("\n" + "=" * 80)
    if all_passed:
        print("🎉 ALL TESTS PASSED! IDS is working correctly.".center(80))
    else:
        print("⚠️  SOME TESTS FAILED. Review the detection patterns.".center(80))
    print("=" * 80 + "\n")
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())
