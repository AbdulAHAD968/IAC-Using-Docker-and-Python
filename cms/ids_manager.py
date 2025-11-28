import os
import sys
import json
import joblib
import pandas as pd
import threading
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'models'))

try:
    from preprocess import parse_log_line, extract_features
    from db_preprocess import parse_db_log, extract_sql_features
except ImportError:
    print("  Warning: Could not import model preprocessing modules")

class IDSManager:

    def __init__(self, base_dir=None):
        self.base_dir = base_dir or "."
        cms_dir = os.path.dirname(os.path.abspath(__file__))
        self.models_dir = os.path.join(os.path.dirname(cms_dir), 'models')
        self.alerts_dir = Path(self.base_dir) / "alerts"
        self.alerts_dir.mkdir(parents=True, exist_ok=True)

        print(f" Looking for models in: {self.models_dir}")

        self.web_model = self._load_model('web_model.pkl')
        self.db_model = self._load_model('db_model.pkl')
        self.email_model = self._load_model('email_model.pkl')

        self.alerts = []
        self.max_alerts = 100

        print("  IDS Manager initialized")

    def _load_model(self, model_name):
        model_path = os.path.join(self.models_dir, model_name)

        if not os.path.exists(model_path):
            print(f"  Model not found: {model_name}")
            print(f"   Expected path: {model_path}")
            return None

        try:
            model = joblib.load(model_path)
            print(f" Loaded model: {model_name}")
            return model
        except Exception as e:
            print(f" Error loading model {model_name}: {e}")
            return None

    def analyze_web_log(self, log_line):
        if not self.web_model:
            return None

        try:
            parsed = parse_log_line(log_line)
            if not parsed:
                return None

            manual_alert = False
            attack_reason = ""

            url = parsed.get('url', '').lower()

            if any(pattern in url for pattern in ['admin', 'cmd=', 'whoami', 'shell', 'exec', 'system', 'config', 'test', 'debug', 'api/admin']):
                manual_alert = True
                attack_reason = "Admin/command access detected"

            elif '..' in url or '%2e%2e' in url or '..%2f' in url or '%252e%252e' in url:
                manual_alert = True
                attack_reason = "Path traversal attempt"

            elif '<script' in url or 'javascript:' in url or '%3cscript' in url or '<iframe' in url:
                manual_alert = True
                attack_reason = "Script injection attempt"

            elif any(pattern in url for pattern in ["' or '", "or 1=1", "or+1=1", "%20or%20", "union select", "union+select", "exec(", "drop ", "drop+", "insert ", "insert+", "update ", "update+"]):
                manual_alert = True
                attack_reason = "SQL injection pattern detected"

            user_agent = parsed.get('user_agent', '').lower()
            if any(tool in user_agent for tool in ['sqlmap', 'curl', 'wget', 'nikto', 'nmap', 'burp', 'sqlmap', 'havij']):
                manual_alert = True
                attack_reason = f"Suspicious tool: {parsed.get('user_agent')}"

            status = parsed.get('status', 200)
            if status >= 400:
                pass

            if manual_alert:
                alert = self._create_alert(
                    alert_type="WEB_ANOMALY",
                    severity="HIGH",
                    source_ip=parsed.get('ip', 'Unknown'),
                    attack_type=attack_reason,
                    payload=f"{parsed['method']} {parsed['url']}",
                    user_agent=parsed.get('user_agent', 'Unknown'),
                    confidence=0.95
                )
                return alert

            df = pd.DataFrame([parsed])
            features = extract_features(df)
            prediction = self.web_model.predict(features)[0]

            confidence = 0.0
            try:
                confidence = abs(self.web_model.decision_function(features)[0])
            except (AttributeError, TypeError):
                try:
                    proba = self.web_model.predict_proba(features)
                    confidence = max(proba[0]) if proba is not None else 0.5
                except:
                    confidence = 0.5

            if prediction == -1:  
                alert = self._create_alert(
                    alert_type="WEB_ANOMALY",
                    severity="HIGH",
                    source_ip=parsed.get('ip', 'Unknown'),
                    attack_type="Web Layer Attack (ML Detection)",
                    payload=f"{parsed['method']} {parsed['url']}",
                    user_agent=parsed.get('user_agent', 'Unknown'),
                    confidence=float(confidence)
                )
                return alert
        except Exception as e:
            print(f" Error analyzing web log: {e}")

        return None

    def analyze_db_log(self, log_line):
        if not self.db_model:
            return None

        try:
            query = parse_db_log(log_line)
            if not query:
                return None

            query_lower = query.lower()
            manual_alert = False
            attack_reason = ""

            sql_injection_patterns = [
                "' or '1'='1",
                "' or 1=1",
                "' or 'a'='a",
                "admin' --",
                "' --",
                "'; drop",
                "'; delete",
                "'; exec",
                "'; execute",
                "union select",
                "union all",
                "exec(",
                "execute(",
                "script>",
                "<script",
            ]

            for pattern in sql_injection_patterns:
                if pattern in query_lower:
                    manual_alert = True
                    attack_reason = "SQL Injection detected"
                    break

            if '; ' in query_lower and len(query.split(';')) > 1:
                stacked_keywords = ['delete', 'drop', 'truncate', 'insert', 'update', 'exec', 'execute']
                for keyword in stacked_keywords:
                    if keyword in query_lower:
                        manual_alert = True
                        attack_reason = f"Stacked query with {keyword.upper()} detected"
                        break

            dangerous_ops = ["drop", "truncate", "delete from", "update", "insert into"]
            if "drop" in query_lower or "truncate" in query_lower:
                manual_alert = True
                attack_reason = "Dangerous operation detected (DROP/TRUNCATE)"

            if manual_alert:
                alert = self._create_alert(
                    alert_type="DB_ANOMALY",
                    severity="CRITICAL",
                    attack_type=attack_reason,
                    payload=query[:200],  
                    confidence=0.95
                )
                return alert

            df = pd.DataFrame([{'query': query}])
            features = extract_sql_features(df)
            prediction = self.db_model.predict(features)[0]

            confidence = 0.0
            try:
                confidence = abs(self.db_model.decision_function(features)[0])
            except (AttributeError, TypeError):
                try:
                    proba = self.db_model.predict_proba(features)
                    confidence = max(proba[0]) if proba is not None else 0.5
                except:
                    confidence = 0.5

            if prediction == -1:  
                alert = self._create_alert(
                    alert_type="DB_ANOMALY",
                    severity="CRITICAL",
                    attack_type="SQL Injection/Database Attack (ML Detection)",
                    payload=query[:200],  
                    confidence=float(confidence)
                )
                return alert
        except Exception as e:
            print(f" Error analyzing DB log: {e}")

        return None

    def analyze_email_log(self, log_line):
        if not self.email_model:
            return None

        try:
            parsed = parse_log_line(log_line)
            if not parsed:
                return None

            manual_alert = False
            attack_reason = ""
            severity = "MEDIUM"

            url = parsed.get('url', '').lower()
            user_agent = parsed.get('user_agent', '').lower()

            phishing_patterns = [
                'verify', 'confirm', 'urgent', 'action+required', 'action%20required',
                'update+account', 'update%20account', 'click+here', 'click%20here',
                'login+required', 'login%20required', 'verify+identity', 'verify%20identity',
                'confirm+identity', 'confirm%20identity', 'unusual+activity', 'unusual%20activity',
                'suspend', 'expire', 'locked', 'disable', 'compromised'
            ]

            if any(pattern in url for pattern in phishing_patterns):
                manual_alert = True
                attack_reason = "Phishing email pattern detected"
                severity = "HIGH"

            spam_patterns = [
                'viagra', 'casino', 'lottery', 'prize', 'click+link', 'click%20link',
                'open+attachment', 'open%20attachment', 'download', 'free+money',
                'free%20money', 'congrats', 'winner', 'claim+reward', 'claim%20reward'
            ]

            if any(pattern in url for pattern in spam_patterns):
                manual_alert = True
                attack_reason = "Spam/Malware email pattern detected"
                severity = "MEDIUM"

            dangerous_patterns = [
                '.exe', '.bat', '.cmd', '.scr', '.vbs', '.js', '.zip', '.rar',
                'malware', 'trojan', 'ransomware', 'exploit', 'backdoor'
            ]

            if any(pattern in url for pattern in dangerous_patterns):
                manual_alert = True
                attack_reason = "Dangerous file/payload pattern detected"
                severity = "CRITICAL"

            suspicious_agents = [
                'curl', 'wget', 'python', 'java', 'powershell', 'bash',
                'perl', 'ruby', 'node', 'scrapy', 'bot', 'exploit'
            ]

            if any(agent in user_agent for agent in suspicious_agents):
                manual_alert = True
                attack_reason = f"Suspicious email client: {parsed.get('user_agent', 'Unknown')}"
                severity = "HIGH"

            if manual_alert:
                alert = self._create_alert(
                    alert_type="EMAIL_ANOMALY",
                    severity=severity,
                    source_ip=parsed.get('ip', 'Unknown'),
                    attack_type=attack_reason,
                    payload=f"{parsed['method']} {parsed['url']}",
                    confidence=0.90
                )
                return alert

            df = pd.DataFrame([parsed])
            features = extract_features(df)
            prediction = self.email_model.predict(features)[0]

            confidence = 0.0
            try:
                confidence = abs(self.email_model.decision_function(features)[0])
            except (AttributeError, TypeError):
                try:
                    proba = self.email_model.predict_proba(features)
                    confidence = max(proba[0]) if proba is not None else 0.5
                except:
                    confidence = 0.5

            if prediction == -1:  
                alert = self._create_alert(
                    alert_type="EMAIL_ANOMALY",
                    severity="MEDIUM",
                    source_ip=parsed.get('ip', 'Unknown'),
                    attack_type="Email Service Attack (ML Detection)",
                    payload=f"{parsed['method']} {parsed['url']}",
                    confidence=float(confidence)
                )
                return alert
        except Exception as e:
            print(f" Error analyzing email log: {e}")

        return None

    def _create_alert(self, alert_type, severity, attack_type, payload, 
                      source_ip="Unknown", user_agent="Unknown", confidence=0.0):
        alert = {
            "id": len(self.alerts) + 1,
            "timestamp": datetime.now().isoformat(),
            "alert_type": alert_type,
            "severity": severity,
            "source_ip": source_ip,
            "attack_type": attack_type,
            "payload": payload,
            "user_agent": user_agent,
            "confidence": round(confidence, 4),
            "status": "active"
        }

        self.alerts.append(alert)
        if len(self.alerts) > self.max_alerts:
            self.alerts.pop(0)

        return alert

    def save_alerts(self):
        try:
            alert_file = self.alerts_dir / "alerts.json"
            with open(alert_file, 'w') as f:
                json.dump(self.alerts, f, indent=2)
        except Exception as e:
            print(f" Error saving alerts: {e}")

    def get_alerts(self, alert_type=None, severity=None, limit=50):
        filtered = self.alerts

        if alert_type:
            filtered = [a for a in filtered if a['alert_type'] == alert_type]

        if severity:
            filtered = [a for a in filtered if a['severity'] == severity]

        return filtered[-limit:]

    def clear_alerts(self):
        self.alerts.clear()
        self.save_alerts()

    def generate_attack_simulation(self, attack_type="sql_injection", target="database"):
        simulations = {
            "sql_injection": [
                "SELECT * FROM users WHERE username='admin' OR '1'='1'",
                "SELECT * FROM users; DROP TABLE users;--",
                "SELECT * FROM users WHERE id=1 UNION SELECT NULL,NULL,NULL",
                "UPDATE users SET password='hacked' WHERE id=1",
                "DELETE FROM users WHERE username LIKE 'a%'",
            ],
            "xss": [
                "/search?q=<script>alert('xss')</script>",
                "/profile?name=<img src=x onerror=alert('xss')>",
                "/?redirect=javascript:alert('xss')",
                "/api/comment?text=<svg onload=alert('xss')>",
            ],
            "brute_force": [
                {"method": "POST", "url": "/login", "user": "admin", "pass": "123456"},
                {"method": "POST", "url": "/login", "user": "admin", "pass": "password"},
                {"method": "POST", "url": "/login", "user": "root", "pass": "root"},
            ],
            "path_traversal": [
                "/files?path=../../etc/passwd",
                "/download?file=../../../../windows/system32/config/sam",
                "/api/config?id=../../secrets.env",
            ]
        }

        return simulations.get(attack_type, [])

    def get_statistics(self):
        total_alerts = len(self.alerts)

        alert_types = {}
        severities = {}

        for alert in self.alerts:
            alert_types[alert['alert_type']] = alert_types.get(alert['alert_type'], 0) + 1
            severities[alert['severity']] = severities.get(alert['severity'], 0) + 1

        return {
            'total_alerts': total_alerts,
            'alert_types': alert_types,
            'severity_distribution': severities,
            'models_loaded': {
                'web_model': self.web_model is not None,
                'db_model': self.db_model is not None,
                'email_model': self.email_model is not None,
            },
            'last_alert': self.alerts[-1] if self.alerts else None
        }
