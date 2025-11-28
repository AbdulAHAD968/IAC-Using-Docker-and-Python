import time
import joblib
import pandas as pd
import os
import sys
import json
from datetime import datetime
from preprocess import parse_log_line, extract_features

# Configuration
MODEL_FILE = "web_model.pkl"
LOG_FILE = "data/web_access.log"
ALERTS_FILE = "data/alerts.json"

def load_model():
    if not os.path.exists(MODEL_FILE):
        print(f"❌ Model {MODEL_FILE} not found!")
        return None
    print(f"🧠 Loading AI Brain: {MODEL_FILE}...")
    return joblib.load(MODEL_FILE)

def save_alert(alert_data):
    """Saves alert to JSON file for the Frontend to read"""
    alerts = []
    
    # Read existing alerts
    if os.path.exists(ALERTS_FILE):
        try:
            with open(ALERTS_FILE, 'r') as f:
                alerts = json.load(f)
        except:
            alerts = []
    
    # Add new alert
    alerts.append(alert_data)
    
    # Write back (keep last 50 alerts to avoid file getting too huge)
    with open(ALERTS_FILE, 'w') as f:
        json.dump(alerts[-50:], f, indent=2)

def monitor_logs():
    clf = load_model()
    if not clf: return

    # Ensure files exist
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w') as f: pass
    
    if not os.path.exists(ALERTS_FILE):
        with open(ALERTS_FILE, 'w') as f: f.write("[]")

    print(f"🛡️  IDS Active. Monitoring {LOG_FILE} and writing to {ALERTS_FILE}...")
    
    with open(LOG_FILE, 'r') as f:
        f.seek(0, os.SEEK_END)
        
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.1)
                continue
                
            parsed_data = parse_log_line(line.strip())
            
            if parsed_data:
                df = pd.DataFrame([parsed_data])
                features = extract_features(df)
                prediction = clf.predict(features)[0]
                
                if prediction == -1:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Create Alert Object
                    alert = {
                        "timestamp": timestamp,
                        "severity": "CRITICAL",
                        "source_ip": parsed_data.get('ip', 'Unknown'), # Ensure preprocess.py returns ip
                        "attack_type": "Anomaly Detected",
                        "payload": f"{parsed_data['method']} {parsed_data['url']}",
                        "user_agent": parsed_data['user_agent']
                    }
                    
                    # Save for Frontend
                    save_alert(alert)
                    
                    # Print for Console
                    print(f"\n🚨 [ALERT] {timestamp} | {alert['payload']}")

if __name__ == "__main__":
    try:
        monitor_logs()
    except KeyboardInterrupt:
        pass