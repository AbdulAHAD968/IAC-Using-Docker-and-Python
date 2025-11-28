#!/usr/bin/env python3

import docker
import time

class CommunicationTester:
    def __init__(self, docker_client, config):
        self.client = docker_client
        self.config = config
    
    def prepare_containers(self):
        print("Preparing containers for testing...")
        
        client_containers = self.client.containers.list(filters={'name': 'client-pc-'})
        for client in client_containers:
            self.install_tools(client, ["curl", "netcat-openbsd", "python3"])
        
        web_containers = self.client.containers.list(filters={'name': 'web-server-'})
        for web in web_containers:
            self.install_tools(web, ["mysql-client"])
        
        print("Container preparation completed!")
    
    def install_tools(self, container, tools):
        try:
            container.reload()
            if container.status != "running":
                return False
            image_name = container.image.tags[0] if container.image.tags else ""
            if "ubuntu" in image_name or "client-pc" in container.name:
                commands = [
                    "apt-get update --allow-unauthenticated || true",
                    f"DEBIAN_FRONTEND=noninteractive apt-get install -y --allow-unauthenticated {' '.join(tools)} || true"
                ]
            elif "alpine" in image_name:
                commands = [f"apk add --no-cache {' '.join(tools)}"]
            else:
                commands = [
                    f"apk add --no-cache {' '.join(tools)} || true",
                    f"apt-get update && apt-get install -y {' '.join(tools)} || true"
                ]
            for cmd in commands:
                try:
                    result = container.exec_run(f"/bin/sh -c '{cmd}'", privileged=True)
                    if result.exit_code == 0:
                        return True
                except:
                    continue
            return False
        except:
            return False
    
    def test_all_communications(self):
        print("Testing network communications...")
        self.prepare_containers()
        time.sleep(10)
        self.test_client_to_web()
        self.test_client_to_email() 
        self.test_web_to_db()
        self.test_email_to_db()
        self.test_client_to_client()
        self.test_denied_communications()
        self.simulate_client_collaboration()
    
    def test_client_to_web(self):
        print("Testing Client -> Web Server (Port 80)")
        
        client_containers = self.client.containers.list(filters={'name': 'client-pc-'})
        web_containers = self.client.containers.list(filters={'name': 'web-server-'})
        
        for client in client_containers:
            for web in web_containers:
                web_ip = self.get_container_ip(web.name, "frontend_net")
                if web_ip:
                    result = self.execute_in_container(client, f"timeout 5 curl -s http://{web_ip}:80/ | head -c 100")
                    if result and result.exit_code == 0:
                        print(f"  {client.name} -> {web.name}:80 - SUCCESS")
                    else:
                        print(f"  {client.name} -> {web.name}:80 - FAILED")
                else:
                    print(f"  {client.name} -> {web.name}:80 - FAILED")
    
    def test_client_to_email(self):
        print("Testing Client -> Email Server (Port 25)")
        
        client_containers = self.client.containers.list(filters={'name': 'client-pc-'})
        email_containers = self.client.containers.list(filters={'name': 'email-server-'})
        
        for client in client_containers:
            for email in email_containers:
                email_ip = self.get_container_ip(email.name, "backend_net")
                if email_ip:
                    methods = [
                        f"timeout 5 nc -z -w 2 {email_ip} 25",
                        f"timeout 5 bash -c 'echo \"QUIT\" | telnet {email_ip} 25'",
                        f"timeout 5 python3 -c \"import socket; s=socket.socket(); s.settimeout(2); s.connect(('{email_ip}', 25)); s.close()\" 2>/dev/null"
                    ]
                    success = False
                    for method in methods:
                        result = self.execute_in_container(client, method)
                        if result and result.exit_code == 0:
                            success = True
                            break
                    if success:
                        print(f"  {client.name} -> {email.name}:25 - SUCCESS")
                    else:
                        print(f"  {client.name} -> {email.name}:25 - FAILED")
                else:
                    print(f"  {client.name} -> {email.name}:25 - FAILED")

    def test_email_to_db(self):
        print("Testing Email Server -> Database (Port 3306)")
        
        email_containers = self.client.containers.list(filters={'name': 'email-server-'})
        db_containers = self.client.containers.list(filters={'name': 'db-server-'})
        
        for email in email_containers:
            for db in db_containers:
                db_ip = self.get_container_ip(db.name, "backend_net")
                if db_ip:
                    self.install_tools(email, ["netcat-openbsd"])
                    result = self.execute_in_container(email, f"timeout 5 nc -z -w 2 {db_ip} 3306")
                    if result and result.exit_code == 0:
                        print(f"  {email.name} -> {db.name}:3306 - SUCCESS")
                    else:
                        print(f"  {email.name} -> {db.name}:3306 - FAILED")
                else:
                    print(f"  {email.name} -> {db.name}:3306 - FAILED")

    def get_container_networks(self, container_name):
        try:
            container = self.client.containers.get(container_name)
            return list(container.attrs['NetworkSettings']['Networks'].keys())
        except:
            return []

    def test_web_to_db(self):
        print("Testing Web Server -> Database (Port 3306)")
        
        web_containers = self.client.containers.list(filters={'name': 'web-server-'})
        db_containers = self.client.containers.list(filters={'name': 'db-server-'})
        
        for web in web_containers:
            for db in db_containers:
                db_ip = self.get_container_ip(db.name, "backend_net")
                if db_ip:
                    time.sleep(5)
                    result = self.execute_in_container(web, f"timeout 10 nc -z -w 5 {db_ip} 3306")
                    if result and result.exit_code == 0:
                        print(f"  {web.name} -> {db.name}:3306 - SUCCESS")
                    else:
                        print(f"  {web.name} -> {db.name}:3306 - FAILED")
                else:
                    print(f"  {web.name} -> {db.name}:3306 - FAILED")
    
    def test_client_to_client(self):
        print("Testing Client -> Client Communication")
        
        client_containers = self.client.containers.list(filters={'name': 'client-pc-'})
        
        if len(client_containers) < 2:
            print("  Need at least 2 clients for client-to-client testing")
            return
        
        print("  Testing SSH access (port 22)...")
        for i, client1 in enumerate(client_containers):
            for j, client2 in enumerate(client_containers):
                if client1 != client2:
                    client2_ip = self.get_container_ip(client2.name, "client_net")
                    if client2_ip:
                        result = self.execute_in_container(client1, f"timeout 5 nc -z -w 2 {client2_ip} 22")
                        if result and result.exit_code == 0:
                            print(f"    {client1.name} -> {client2.name}:22 - SSH accessible")
                        else:
                            print(f"    {client1.name} -> {client2.name}:22 - SSH not accessible")
        
        print("  Testing custom services (ports 8080-8090)...")
        for i, client1 in enumerate(client_containers):
            for j, client2 in enumerate(client_containers):
                if client1 != client2:
                    client2_ip = self.get_container_ip(client2.name, "client_net")
                    if client2_ip:
                        port = 8080 + i
                        self.start_test_service(client2, port)
                        result = self.execute_in_container(client1, f"timeout 5 curl -s http://{client2_ip}:{port}/")
                        if result and result.exit_code == 0:
                            print(f"    {client1.name} -> {client2.name}:{port} - Service accessible")
                        else:
                            print(f"    {client1.name} -> {client2.name}:{port} - Service not accessible")

    def start_test_service(self, container, port):
        try:
            cmd = f"python3 -m http.server {port} > /dev/null 2>&1 &"
            self.execute_in_container(container, cmd)
            time.sleep(2)
        except:
            pass

    def simulate_client_collaboration(self):
        print("Simulating Client Collaboration...")
        
        client_containers = self.client.containers.list(filters={'name': 'client-pc-'})
        
        if len(client_containers) >= 2:
            print("  Setting up shared collaboration...")
            
            client1 = client_containers[0]
            client1_ip = self.get_container_ip(client1.name, "client_net")
            
            self.execute_in_container(client1, "mkdir -p /shared_project")
            self.execute_in_container(client1, "echo 'Project started by Client 1' > /shared_project/README.txt")
            self.execute_in_container(client1, "echo 'config: v1.0' > /shared_project/config.json")
            self.execute_in_container(client1, "cd /shared_project && python3 -m http.server 8080 > /dev/null 2>&1 &")
            
            for i, client in enumerate(client_containers[1:], 2):
                if client1_ip:
                    result = self.execute_in_container(client, f"curl -s http://{client1_ip}:8080/README.txt")
                    if result and "Project started by Client 1" in result.output.decode():
                        print(f"    Client {i} successfully accessed shared files from Client 1")
                        self.execute_in_container(client, f"curl -X POST -d 'Client {i} contribution' http://{client1_ip}:8080/ || true")
                        print(f"    Client {i} contributed to shared project")
            
            print("  Simulating client messaging...")
            for i, client in enumerate(client_containers):
                client_ip = self.get_container_ip(client.name, "client_net")
                if client_ip:
                    for other_client in client_containers:
                        if client != other_client:
                            other_client_ip = self.get_container_ip(other_client.name, "client_net")
                            if other_client_ip:
                                self.execute_in_container(other_client, f"echo 'Client {i+1} is at {client_ip}' >> /tmp/network_peers.txt")
            
            for client in client_containers:
                result = self.execute_in_container(client, "cat /tmp/network_peers.txt 2>/dev/null || echo 'No peers discovered'")
                if result:
                    peer_count = result.output.decode().count('Client')
                    print(f"    {client.name} discovered {peer_count} peers")

    def test_denied_communications(self):
        print("Testing Denied Communications")
        
        client_containers = self.client.containers.list(filters={'name': 'client-pc-'})
        db_containers = self.client.containers.list(filters={'name': 'db-server-'})
        
        blocked_count = 0
        total_count = 0
        
        for client in client_containers:
            for db in db_containers:
                total_count += 1
                db_ip = self.get_container_ip(db.name, "backend_net")
                if db_ip:
                    result = self.execute_in_container(client, f"timeout 5 nc -z -w 2 {db_ip} 3306")
                    if result and result.exit_code != 0:
                        print(f"  {client.name} -> {db.name}:3306 - CORRECTLY BLOCKED")
                        blocked_count += 1
                    else:
                        print(f"  {client.name} -> {db.name}:3306 - UNEXPECTEDLY ALLOWED")
        
        print(f"  Security: {blocked_count}/{total_count} denied connections properly blocked")
    
    def execute_in_container(self, container, command):
        try:
            return container.exec_run(f"/bin/sh -c '{command}'")
        except:
            return None
    
    def get_container_ip(self, container_name, network_name):
        try:
            container = self.client.containers.get(container_name)
            networks = container.attrs['NetworkSettings']['Networks']
            return networks.get(network_name, {}).get('IPAddress')
        except:
            return None
