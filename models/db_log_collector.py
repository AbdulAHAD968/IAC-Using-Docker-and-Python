import docker
import time
import os
import sys
import re

# Configuration
LOG_DIR = "data"
DB_LOG_FILE = os.path.join(LOG_DIR, "db_query.log")

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

client = docker.from_env()

def get_clean_log_path(container):
    """Asks MySQL for the log path and filters out the Password Warning"""
    print(f"🔧 Configured MySQL Logging on {container.name}...")
    try:
        # 1. Enable Logging
        container.exec_run('mysql -psecurepassword123 -e "SET GLOBAL general_log = \'ON\';"')
        container.exec_run('mysql -psecurepassword123 -e "SET GLOBAL log_output = \'FILE\';"')
        
        # 2. Get the path (This command triggers the 'Using password' warning)
        cmd = 'mysql -psecurepassword123 -N -e "SELECT @@general_log_file;"'
        exit_code, output = container.exec_run(cmd)
        
        # 3. Parse the output line-by-line to find the real path
        # The output will look like:
        # "mysql: [Warning] Using a password...\n/var/lib/mysql/db-server-1.log"
        lines = output.decode().split('\n')
        for line in lines:
            clean_line = line.strip()
            # Valid path usually starts with / and is not the warning message
            if clean_line.startswith('/') and "Warning" not in clean_line:
                print(f"   ✅ Found Log Path: {clean_line}")
                return clean_line
        
        print(f"   ❌ Could not find path in output: {output.decode()}")
        return None

    except Exception as e:
        print(f"   ❌ Failed to enable logging: {e}")
        return None

def stream_db_logs():
    # Clear the old log file so we don't see previous errors
    with open(DB_LOG_FILE, 'w') as f:
        f.write("")
    print("🚀 DB Log Collector started (Log file cleared).")
    
    try:
        container = client.containers.get("db-server-1")
        internal_log_path = get_clean_log_path(container)
        
        if not internal_log_path:
            print("   ❌ Exiting: No log path found.")
            return

        print(f"🔌 Streaming logs from {container.name}...")
        
        # Stream the file using 'tail -f'
        exec_stream = container.exec_run(f"tail -f {internal_log_path}", stream=True)
        
        for line in exec_stream.output:
            decoded_line = line.decode('utf-8', errors='ignore').strip()
            
            # Filter out internal MySQL noise (Connect, Quit, Statistics)
            # and the "tail" errors if they somehow persist
            if not decoded_line: continue
            if "tail: cannot open" in decoded_line: continue 
            if "mysql: [Warning]" in decoded_line: continue
            
            # Write clean logs
            with open(DB_LOG_FILE, "a") as f:
                f.write(decoded_line + "\n")
                f.flush()

    except docker.errors.NotFound:
        print("❌ db-server-1 not found.")
    except KeyboardInterrupt:
        print("🛑 DB Collector stopped.")

if __name__ == "__main__":
    stream_db_logs()