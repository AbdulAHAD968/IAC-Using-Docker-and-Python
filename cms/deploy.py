import docker
import time

class InfrastructureDeployer:
    def __init__(self, docker_client, config):
        self.client = docker_client
        self.config = config
        self.containers = {}
    
    def cleanup_existing_containers(self):
        print("Checking for existing containers...")
        
        patterns = ['web-server-', 'db-server-', 'email-server-', 'client-pc-']
        for pattern in patterns:
            try:
                existing_containers = self.client.containers.list(
                    all=True, 
                    filters={'name': pattern}
                )
                for container in existing_containers:
                    print(f"  Removing existing {container.name}...")
                    try:
                        container.stop(timeout=5)
                        container.remove()
                    except Exception as e:
                        print(f"    Warning: Could not remove {container.name}: {e}")
            except Exception as e:
                print(f"    Error checking {pattern}: {e}")
    
    def deploy_all(self):
        print("Deploying containers...")
        
        self.cleanup_existing_containers()
        
        try:
            for i in range(self.config['infrastructure']['web_servers']['count']):
                self.deploy_web_server(i)
            
            self.deploy_db_server()
            
            self.deploy_email_server()
            
            for i in range(self.config['infrastructure']['client_pcs']['count']):
                self.deploy_client_pc(i)
                
            print("All containers deployed successfully!")
                
        except Exception as e:
            print(f"Deployment failed: {e}")
            raise
    
    def deploy_web_server(self, index):
        name = f"web-server-{index+1}"
        print(f"  Deploying {name}...")
        
        try:
            try:
                existing = self.client.containers.get(name)
                print(f"    Removing existing {name}...")
                existing.remove(force=True)
            except docker.errors.NotFound:
                pass
            
            try:
                self.client.images.get("nginx:alpine")
            except docker.errors.ImageNotFound:
                print(f"    Pulling nginx:alpine image...")
                self.client.images.pull("nginx:alpine")
            
            container = self.client.containers.run(
                "nginx:alpine",
                name=name,
                network="frontend_net",
                detach=True,
                ports={'80/tcp': 8080 + index} if index == 0 else {},
                restart_policy={"Name": "unless-stopped"}
            )
            self.containers[name] = container
            print(f"    {name} deployed")
            return container
            
        except docker.errors.APIError as e:
            print(f"    Error deploying {name}: {e}")
            raise
        except Exception as e:
            print(f"    Unexpected error deploying {name}: {e}")
            raise
    
    def deploy_db_server(self):
        name = "db-server-1"
        print(f"  Deploying {name}...")
        
        try:
            try:
                existing = self.client.containers.get(name)
                print(f"    Removing existing {name}...")
                existing.remove(force=True)
            except docker.errors.NotFound:
                pass
            
            try:
                self.client.images.get("mysql:8.0")
            except docker.errors.ImageNotFound:
                print(f"    Pulling mysql:8.0 image...")
                self.client.images.pull("mysql:8.0")
            
            container = self.client.containers.run(
                "mysql:8.0",
                name=name,
                network="backend_net",
                detach=True,
                environment={
                    'MYSQL_ROOT_PASSWORD': 'securepassword123',
                    'MYSQL_DATABASE': 'app_db',
                    'MYSQL_ROOT_HOST': '%'
                },
                restart_policy={"Name": "unless-stopped"}
            )
            self.containers[name] = container
            print(f"    {name} deployed")
            return container
            
        except docker.errors.APIError as e:
            print(f"    Error deploying {name}: {e}")
            raise
    
    def deploy_email_server(self):
        name = "email-server-1"
        print(f"  Deploying {name}...")
        
        try:
            try:
                existing = self.client.containers.get(name)
                print(f"    Removing existing {name}...")
                existing.remove(force=True)
            except docker.errors.NotFound:
                pass
            
            try:
                self.client.images.get("namshi/smtp:latest")
            except docker.errors.ImageNotFound:
                print(f"    Pulling namshi/smtp image...")
                self.client.images.pull("namshi/smtp:latest")
            
            container = self.client.containers.run(
                "namshi/smtp:latest",
                name=name,
                network="frontend_net",
                detach=True,
                ports={
                    '25/tcp': 1025
                },
                restart_policy={"Name": "unless-stopped"}
            )
            self.containers[name] = container
            print(f"    {name} deployed")
            return container
            
        except docker.errors.APIError as e:
            print(f"    Error deploying {name}: {e}")
            return self.deploy_email_server_alternative()
    
    def deploy_email_server_alternative(self):
        name = "email-server-1"
        try:
            container = self.client.containers.run(
                "ubuntu:20.04",
                name=name,
                network="frontend_net",
                detach=True,
                command="apt-get update && apt-get install -y postfix && tail -f /dev/null",
                ports={'25/tcp': 1025},
                restart_policy={"Name": "unless-stopped"}
            )
            self.containers[name] = container
            print(f"    {name} deployed (alternative)")
            return container
        except Exception as e:
            print(f"    Alternative deployment also failed: {e}")
            raise
    
    def deploy_client_pc(self, index):
        name = f"client-pc-{index+1}"
        print(f"  Deploying {name}...")
        
        try:
            try:
                existing = self.client.containers.get(name)
                print(f"    Removing existing {name}...")
                existing.remove(force=True)
            except docker.errors.NotFound:
                pass
            
            try:
                self.client.images.get("ubuntu:22.04")
            except docker.errors.ImageNotFound:
                print(f"    Pulling ubuntu:22.04 image...")
                self.client.images.pull("ubuntu:22.04")
            
            container = self.client.containers.run(
                "ubuntu:22.04",
                name=name,
                network="frontend_net",
                detach=True,
                command="tail -f /dev/null",
                restart_policy={"Name": "unless-stopped"}
            )
            self.containers[name] = container
            print(f"    {container.name} deployed")
            return container
            
        except docker.errors.APIError as e:
            print(f"    Error deploying {name}: {e}")
            raise
    
    def cleanup_all(self):
        print("Cleaning up all containers...")
        for name, container in self.containers.items():
            try:
                container.stop(timeout=10)
                container.remove()
                print(f"  Removed {name}")
            except Exception as e:
                print(f"  Error removing {name}: {e}")
        
        self.cleanup_existing_containers()