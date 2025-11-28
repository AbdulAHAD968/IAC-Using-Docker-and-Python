import docker
import time
import threading
import re
import os
import sys

# Configuration
LOG_DIR = "data"
WEB_LOG_FILE = os.path.join(LOG_DIR, "web_access.log")

# Ensure data directory exists
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

client = docker.from_env()

# Regex to parse standard Nginx "Combined" Log Format
# Matches: IP - - [Date] "Request" Status Bytes "Referer" "UserAgent" "Extra"
NGINX_PATTERN = re.compile(r'^(\S+) (\S+) (\S+) \[(.*?)\] "(.*?)" (\d+) (\d+) "(.*?)" "(.*?)"(.*)?')

def format_to_kagggle_style(raw_line):
    """
    Converts raw Docker string to the exact Kaggle Dataset format.
    """
    match = NGINX_PATTERN.match(raw_line)
    if match:
        # Extract fields
        ip, ident, auth, timestamp, request, status, bytes_sent, referer, ua, extra = match.groups()
        
        # Clean up the 'extra' field
        extra = extra.strip().replace('"', '') if extra else "-"
        if not extra: extra = "-"

        # Reconstruct exactly like the Kaggle sample
        return f'{ip} {ident} {auth} [{timestamp}] "{request}" {status} {bytes_sent} "{referer}" "{ua}" "{extra}"\n'
    
    return None

def stream_container_logs(container_name):
    print(f"🔌 Connected to log stream: {container_name}")
    try:
        container = client.containers.get(container_name)
        # Stream logs (tail=0 means only new logs)
        for line in container.logs(stream=True, follow=True, tail=0):
            decoded_line = line.decode('utf-8').strip()
            
            # Transform log format
            formatted_log = format_to_kagggle_style(decoded_line)
            
            if formatted_log:
                # Append to central CMS log file
                with open(WEB_LOG_FILE, "a") as f:
                    f.write(formatted_log)
                    f.flush() 
                
                # Print to console for debugging (when running manually)
                # In background mode, this goes to /dev/null
                # print(f"📝 [LOG]: {formatted_log.strip()}")
                
    except docker.errors.NotFound:
        print(f"❌ Container {container_name} not found.")
    except Exception as e:
        print(f"❌ Error streaming {container_name}: {e}")

def start_collector():
    print(f"🚀 CMS Log Collector started.")
    print(f"📂 Saving logs to: {os.path.abspath(WEB_LOG_FILE)}")
    print("   Waiting for traffic...")

    # Find all web servers
    web_containers = client.containers.list(filters={'name': 'web-server-'})
    
    threads = []
    for container in web_containers:
        t = threading.Thread(target=stream_container_logs, args=(container.name,))
        t.daemon = True
        t.start()
        threads.append(t)

    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Collector stopped.")
        sys.exit(0)

if __name__ == "__main__":
    start_collector()