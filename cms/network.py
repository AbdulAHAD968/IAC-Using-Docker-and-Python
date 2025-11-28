import docker
import time

class NetworkManager:
    def __init__(self, docker_client, config):
        self.client = docker_client
        self.config = config
        self.networks = {}

    
    def setup_network_connectivity(self):
        """Connect containers to appropriate networks based on communication rules"""
        print("🔗 Setting up network connectivity...")
        
        # Get all networks first
        try:
            frontend_net = self.client.networks.get("frontend_net")
            backend_net = self.client.networks.get("backend_net") 
            management_net = self.client.networks.get("management_net")
        except docker.errors.NotFound as e:
            print(f"❌ Network not found: {e}")
            return
        
        # Connect web servers to backend network
        web_containers = self.client.containers.list(filters={'name': 'web-server-'})
        for container in web_containers:
            try:
                backend_net.connect(container)
                print(f"  ✅ {container.name} connected to backend_net")
            except docker.errors.APIError as e:
                if "already exists" in str(e):
                    print(f"  ℹ️  {container.name} already in backend_net")
        
        # Connect email server to backend network (to reach database)
        email_containers = self.client.containers.list(filters={'name': 'email-server-'})
        for container in email_containers:
            try:
                backend_net.connect(container)
                print(f"  ✅ {container.name} connected to backend_net")
            except docker.errors.APIError as e:
                if "already exists" in str(e):
                    print(f"  ℹ️  {container.name} already in backend_net")
        
        # Connect client PCs to frontend network
        client_containers = self.client.containers.list(filters={'name': 'client-pc-'})
        for container in client_containers:
            try:
                frontend_net.connect(container)
                print(f"  ✅ {container.name} connected to frontend_net")
            except docker.errors.APIError as e:
                if "already exists" in str(e):
                    print(f"  ℹ️  {container.name} already in frontend_net")
        
        print("🔗 Network connectivity setup completed!")

    def connect_container_to_network(self, container, network_name):
        """Connect a container to a specific network"""
        try:
            network = self.client.networks.get(network_name)
            network.connect(container)
        except docker.errors.APIError as e:
            print(f"    Warning: Could not connect {container.name} to {network_name}: {e}")
    
    def get_container_ip(self, container_name, network_name):
        """Get container IP address on specific network"""
        try:
            container = self.client.containers.get(container_name)
            network_settings = container.attrs['NetworkSettings']['Networks']
            return network_settings.get(network_name, {}).get('IPAddress')
        except:
            return None
    
    def cleanup_existing_networks(self):
        """Clean up any existing networks"""
        print("🧹 Checking for existing networks...")
        
        network_names = ['frontend_net', 'backend_net', 'management_net', 'client_net']
        for net_name in network_names:
            try:
                existing_net = self.client.networks.get(net_name)
                print(f"  Removing existing {net_name}...")
                
                # Disconnect all containers from the network first
                for container in existing_net.containers:
                    try:
                        existing_net.disconnect(container)
                    except Exception as e:
                        print(f"    Warning: Could not disconnect {container.name}: {e}")
                
                # Remove the network
                existing_net.remove()
                time.sleep(1)  # Small delay
                
            except docker.errors.NotFound:
                pass
            except Exception as e:
                print(f"    Error removing {net_name}: {e}")
    
    def create_networks(self):
        print("🌐 Creating Docker networks...")
        
        # Clean up existing networks first
        self.cleanup_existing_networks()
        
        time.sleep(2)  # Give Docker time to clean up
        
        network_configs = {
            'frontend_net': {'subnet': '10.10.1.0/24'},
            'backend_net': {'subnet': '10.10.2.0/24'},
            'management_net': {'subnet': '10.10.3.0/24'},
            'client_net': {'subnet': '10.10.4.0/24'}  # Add client network
        }
        
        for net_name, net_config in network_configs.items():
            print(f"  Creating {net_name}...")
            
            try:
                # Create new network
                network = self.client.networks.create(
                    net_name,
                    driver="bridge",
                    ipam=docker.types.IPAMConfig(
                        pool_configs=[
                            docker.types.IPAMPool(subnet=net_config['subnet'])
                        ]
                    ),
                    check_duplicate=True
                )
                self.networks[net_name] = network
                print(f"    ✅ {net_name} created")
                
            except docker.errors.APIError as e:
                print(f"    ❌ Error creating {net_name}: {e}")
                # Try without subnet specification
                try:
                    network = self.client.networks.create(net_name, driver="bridge")
                    self.networks[net_name] = network
                    print(f"    ✅ {net_name} created (without subnet)")
                except Exception as e2:
                    print(f"    ❌ Failed to create {net_name}: {e2}")

    def setup_network_connectivity(self):
        """Connect containers to appropriate networks based on communication rules"""
        print("🔗 Setting up network connectivity...")
        
        # Get all networks first
        try:
            frontend_net = self.client.networks.get("frontend_net")
            backend_net = self.client.networks.get("backend_net") 
            management_net = self.client.networks.get("management_net")
            client_net = self.client.networks.get("client_net")  # Add client network
        except docker.errors.NotFound as e:
            print(f"❌ Network not found: {e}")
            return
        
        # Connect web servers to backend network
        web_containers = self.client.containers.list(filters={'name': 'web-server-'})
        for container in web_containers:
            try:
                backend_net.connect(container)
                print(f"  ✅ {container.name} connected to backend_net")
            except docker.errors.APIError as e:
                if "already exists" in str(e):
                    print(f"  ℹ️  {container.name} already in backend_net")
        
        # Connect email server to backend network
        email_containers = self.client.containers.list(filters={'name': 'email-server-'})
        for container in email_containers:
            try:
                backend_net.connect(container)
                print(f"  ✅ {container.name} connected to backend_net")
            except docker.errors.APIError as e:
                if "already exists" in str(e):
                    print(f"  ℹ️  {container.name} already in backend_net")
        
        # Connect client PCs to frontend and client networks
        client_containers = self.client.containers.list(filters={'name': 'client-pc-'})
        for container in client_containers:
            # Frontend network (for web/email access)
            try:
                frontend_net.connect(container)
                print(f"  ✅ {container.name} connected to frontend_net")
            except docker.errors.APIError as e:
                if "already exists" in str(e):
                    print(f"  ℹ️  {container.name} already in frontend_net")
            
            # Client network (for client-to-client communication)
            try:
                client_net.connect(container)
                print(f"  ✅ {container.name} connected to client_net")
            except docker.errors.APIError as e:
                if "already exists" in str(e):
                    print(f"  ℹ️  {container.name} already in client_net")
        
        print("🔗 Network connectivity setup completed!")

    def cleanup_networks(self):
        print("🧹 Cleaning up networks...")
        for name, network in self.networks.items():
            try:
                # Disconnect all containers first
                for container in network.containers:
                    try:
                        network.disconnect(container)
                    except Exception as e:
                        print(f"    Warning: Could not disconnect {container.name}: {e}")
                
                network.remove()
                print(f"  Removed {name}")
            except Exception as e:
                print(f"  Error removing {name}: {e}")
        
        # Clean up any remaining networks
        self.cleanup_existing_networks()
