import pandas as pd
import re
import os
import numpy as np

# Regex for Nginx Combined Format (Same as collector)
LOG_PATTERN = re.compile(r'^(\S+) (\S+) (\S+) \[(.*?)\] "(.*?)" (\d+) (\d+) "(.*?)" "(.*?)"(.*)?')

def parse_log_line(line):
    """
    Parses a single log line into a dictionary.
    """
    match = LOG_PATTERN.match(line)
    if match:
        ip, ident, auth, timestamp, request, status, bytes_sent, referer, ua, extra = match.groups()
        
        # Split Request into Method and URL (e.g., "GET /index.html HTTP/1.1")
        if len(request.split()) >= 2:
            method = request.split()[0]
            url = request.split()[1]
        else:
            method = "UNKNOWN"
            url = request
            
        return {
            "ip": ip,
            "timestamp": timestamp,
            "method": method,
            "url": url,
            "status": int(status),
            "bytes": int(bytes_sent),
            "referer": referer,
            "user_agent": ua
        }
    return None

def extract_features(df):
    """
    Converts Raw Text Columns into Numerical Features for ML.
    """
    print("⚙️  Extracting features from logs...")
    
    # 1. URL Length (Long URLs = Potential Buffer Overflow/XSS)
    df['url_length'] = df['url'].apply(len)
    
    # 2. Special Character Count (High count = Potential SQL Injection)
    # We count: % (hex), ' (quote), " (quote), < > (script), = (logic), ; (command chaining)
    def count_specials(text):
        return sum(text.count(char) for char in ["%", "'", '"', "<", ">", "=", ";", "(", ")"])
    
    df['special_chars'] = df['url'].apply(count_specials)
    
    # 3. Status Code Categories (One-Hot Encoding Concept)
    # 4xx = Client Error (Scanning), 5xx = Server Error (Exploit Success), 2xx = Normal
    df['is_error'] = df['status'].apply(lambda x: 1 if x >= 400 else 0)
    
    # 4. HTTP Method (POST is common for Brute Force)
    df['is_post'] = df['method'].apply(lambda x: 1 if x.upper() == 'POST' else 0)
    
    # 5. User Agent Length (Scanners often have very short or weirdly long UAs)
    df['ua_length'] = df['user_agent'].apply(len)
    
    # Return only the numerical features for the model
    feature_cols = ['url_length', 'special_chars', 'is_error', 'is_post', 'ua_length', 'bytes']
    return df[feature_cols]

def load_and_process_logs(filepath, chunk_size=100000):
    """
    Loads a log file and returns the processed Feature Matrix (X).
    """
    data = []
    print(f"📂 Loading log file: {filepath}")
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            # Read line by line to handle 3.5GB files without crashing RAM
            for i, line in enumerate(f):
                parsed = parse_log_line(line.strip())
                if parsed:
                    data.append(parsed)
                
                # Optional: Break early for testing small chunks
                # if i > 5000: break 
    except FileNotFoundError:
        print("❌ File not found.")
        return None

    if not data:
        print("⚠️  No valid log lines found.")
        return None

    # Convert to DataFrame
    raw_df = pd.DataFrame(data)
    print(f"✅ Parsed {len(raw_df)} lines.")
    
    # Extract Features
    features_df = extract_features(raw_df)
    
    return features_df

if __name__ == "__main__":
    # TEST RUN
    # Use the live log file you just generated
    target_file = "data/web_access.log"
    
    if os.path.exists(target_file):
        X = load_and_process_logs(target_file)
        print("\n📊 Feature Matrix Preview (First 5 rows):")
        print(X.head())
        print("\n✅ Ready for ML Training!")
    else:
        print(f"❌ Run log_collector.py first to generate {target_file}")