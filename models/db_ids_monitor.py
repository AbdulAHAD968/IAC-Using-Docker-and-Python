import warnings
# Suppress version mismatch warnings from scikit-learn
warnings.filterwarnings("ignore", category=UserWarning)

import time
import joblib
import pandas as pd
import os
import sys
import json
from datetime import datetime
from db_preprocess import parse_db_log, extract_sql_features

# Configuration
MODEL_FILE = "db_model.pkl"
LOG_FILE = "data/db_query.log"
ALERTS_FILE = "data/alerts.json"

def load_model():
    if not os.path.exists(MODEL_FILE):
        print(f"❌ Model {MODEL_FILE} not found!")
        return None
    print(f"🧠 Loading DB Brain: {MODEL_FILE}...")
    return joblib.load(MODEL_FILE)

def save_alert(alert_data):
    alerts = []
    if os.path.exists(ALERTS_FILE):
        try:
            with open(ALERTS_FILE, 'r') as f:
                alerts = json.load(f)
        except:
            alerts = []
    
    alerts.append(alert_data)
    # Keep last 50 alerts
    with open(ALERTS_FILE, 'w') as f:
        json.dump(alerts[-50:], f, indent=2)

def monitor_db_logs():
    clf = load_model()
    if not clf: return

    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w') as f: pass

    print(f"🛡️  DB IDS Active. Monitoring {LOG_FILE}...")
    
    with open(LOG_FILE, 'r') as f:
        f.seek(0, os.SEEK_END)
        
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.1)
                continue
            
            # Clean and Parse
            query = parse_db_log(line.strip())
            
            # Skip empty or system queries
            if not query or len(query) < 5: continue

            # Prepare features
            df = pd.DataFrame([{"query": query}])
            features = extract_sql_features(df)
            
            # Predict (1 = Attack, 0 = Normal)
            prediction = clf.predict(features)[0]
            
            if prediction == 1:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                alert = {
                    "timestamp": timestamp,
                    "severity": "CRITICAL",
                    "source_ip": "Internal DB", 
                    "attack_type": "SQL Injection Detected",
                    "payload": query[:150], # Truncate long queries
                    "user_agent": "N/A"
                }
                save_alert(alert)
                print(f"\n🚨 [DB ALERT] {alert['payload']}")

if __name__ == "__main__":
    try:
        monitor_db_logs()
    except KeyboardInterrupt:
        pass