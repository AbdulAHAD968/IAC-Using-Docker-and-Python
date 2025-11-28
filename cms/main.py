#!/usr/bin/env python3

import yaml
import docker
import subprocess
import sys
import time
import os
from deploy import InfrastructureDeployer
from security import SecurityManager
from network import NetworkManager
from communication import CommunicationTester
from config_manager import ConfigManager
from enhanced_security import EnhancedSecurityManager
from deployment_manager import DeploymentManager
from health_monitor import HealthMonitor

class CentralManagementSystem:
    def __init__(self, config_path=None):
        if config_path is None:
            # Get the directory where this script is located
            script_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(script_dir, "config.yaml")
        
        # Initialize configuration manager first
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.current_config
        
        # Validate configuration
        self.config_manager.validate_config()
        
        # Initialize Docker client with proper socket handling
        try:
            # Set proper environment for Docker SDK
            os.environ['DOCKER_HOST'] = 'unix:///var/run/docker.sock'
            self.docker_client = docker.DockerClient(base_url='unix:///var/run/docker.sock')
            # Test the connection
            self.docker_client.ping()
        except Exception as e:
            print(f"❌ Could not connect to Docker: {e}")
            raise
        
        # Initialize all managers
        self.deployer = InfrastructureDeployer(self.docker_client, self.config)
        self.security_manager = SecurityManager(self.docker_client, self.config)
        self.enhanced_security = EnhancedSecurityManager(self.docker_client, self.config, self.config_manager)
        self.network_manager = NetworkManager(self.docker_client, self.config)
        self.communication_tester = CommunicationTester(self.docker_client, self.config)
        self.deployment_manager = DeploymentManager(self.docker_client)
        self.health_monitor = HealthMonitor(self.docker_client)
        
    def load_config(self, config_path):
        print(f"📁 Loading config from: {config_path}")
        try:
            with open(config_path, 'r') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            print(f"❌ Config file not found: {config_path}")
            print("Please make sure config.yaml exists in the cms directory")
            sys.exit(1)
        except yaml.YAMLError as e:
            print(f"❌ Error parsing config file: {e}")
            sys.exit(1)
    
    def deploy_infrastructure(self):
        print("🚀 Deploying complete infrastructure...")
        
        # Create deployment snapshot BEFORE deployment
        deployment_id = self.deployment_manager.create_deployment_snapshot(
            description="Infrastructure deployment started",
            config=self.config
        )
        
        try:
            # Create networks
            self.network_manager.create_networks()
            
            # Deploy containers
            self.deployer.deploy_all()
            
            # Wait for containers to start
            print("⏳ Waiting for containers to initialize...")
            time.sleep(10)
            
            # Setup network connectivity
            self.network_manager.setup_network_connectivity()
            
            # Apply comprehensive security hardening
            print("🔐 Applying enhanced security hardening...")
            self.enhanced_security.harden_all_containers()
            
            # Wait a bit more for MySQL to be ready
            print("⏳ Waiting for database to be ready...")
            time.sleep(15)
            
            # Run health checks
            print("🏥 Running health checks...")
            health_report = self.health_monitor.check_all_containers()
            
            # Test communications
            self.communication_tester.test_all_communications()
            
            # Mark deployment as successful
            self.deployment_manager.mark_deployment_complete(deployment_id, 'success')
            
            print("✅ Infrastructure deployment completed successfully!")
            return True
        
        except Exception as e:
            print(f"❌ Deployment failed: {e}")
            self.deployment_manager.mark_deployment_complete(deployment_id, 'failed')
            raise
    
    def test_communications(self):
        """Test communications after deployment"""
        print("🔍 Testing communications...")
        self.communication_tester.test_all_communications()
        self.communication_tester.simulate_real_traffic()
    
    def check_config_for_changes(self):
        """Check if configuration has changed and needs redeployment"""
        if self.config_manager.has_changed():
            print("⚠️  Configuration has changed!")
            return True
        return False
    
    def redeploy_on_config_change(self):
        """Re-deploy infrastructure if configuration has changed"""
        if not self.check_config_for_changes():
            print("✅ No configuration changes detected")
            return False
        
        print("🔄 Configuration has changed, re-deploying infrastructure...")
        self.config_manager.load_config()  # Reload fresh config
        self.config = self.config_manager.current_config
        
        # Backup current state
        self.deployment_manager.create_deployment_snapshot(
            description="Pre-redeployment snapshot after config change"
        )
        
        # Clean up existing and redeploy
        self.destroy_infrastructure()
        time.sleep(5)
        self.deploy_infrastructure()
        
        return True
    
    def get_deployment_history(self, limit=10):
        """Get deployment history"""
        return self.deployment_manager.list_deployments(limit)
    
    def rollback_to_deployment(self, deployment_id):
        """Rollback to a specific deployment"""
        print(f"🔄 Rolling back to deployment {deployment_id}...")
        
        # Create backup of current state
        self.deployment_manager.create_deployment_snapshot(
            description=f"Backup before rollback to {deployment_id}"
        )
        
        # Get rollback plan
        plan = self.deployment_manager.get_rollback_plan(deployment_id)
        if not plan:
            print("❌ Cannot generate rollback plan")
            return False
        
        print("📋 Rollback plan:")
        for action in plan['actions']:
            print(f"  - {action['type']}: {action['container']}")
        
        # Get target deployment config
        target_deployment = self.deployment_manager.get_deployment(deployment_id)
        if not target_deployment:
            print("❌ Target deployment not found")
            return False
        
        target_containers = target_deployment.get('containers', {})
        
        # Execute rollback actions
        print("\n🔄 Executing rollback actions...")
        
        # 1. Remove containers that shouldn't exist
        print("🛑 Removing extra containers...")
        for action in plan['actions']:
            if action['type'] == 'remove':
                container_name = action['container']
                try:
                    container = self.docker_client.containers.get(container_name)
                    if container.status == 'running':
                        container.stop(timeout=10)
                    container.remove()
                    print(f"  ✅ Removed {container_name}")
                except Exception as e:
                    print(f"  ⚠️  Could not remove {container_name}: {e}")
        
        # 2. Create missing containers
        print("\n🐳 Creating missing containers...")
        for action in plan['actions']:
            if action['type'] == 'create':
                container_name = action['container']
                image = action['image']
                
                # Determine which network based on container type
                if 'web-server' in container_name:
                    networks = ['frontend_net', 'backend_net']
                elif 'db-server' in container_name:
                    networks = ['backend_net']
                elif 'email-server' in container_name:
                    networks = ['frontend_net', 'backend_net']
                elif 'client-pc' in container_name:
                    networks = ['frontend_net', 'client_net']
                else:
                    networks = ['frontend_net']
                
                try:
                    # Create container on first network
                    container = self.docker_client.containers.run(
                        image,
                        name=container_name,
                        network=networks[0],
                        detach=True,
                        restart_policy={"Name": "unless-stopped"}
                    )
                    
                    # Connect to additional networks if needed
                    for network_name in networks[1:]:
                        try:
                            network = self.docker_client.networks.get(network_name)
                            network.connect(container)
                        except:
                            pass
                    
                    print(f"  ✅ Created {container_name}")
                except Exception as e:
                    print(f"  ⚠️  Could not create {container_name}: {e}")
        
        # 3. Wait for containers to start
        print("\n⏳ Waiting for containers to initialize...")
        time.sleep(10)
        
        # 4. Setup network connectivity
        print("🔗 Setting up network connectivity...")
        self.network_manager.setup_network_connectivity()
        
        # 5. Apply security hardening
        print("🔐 Applying security hardening...")
        self.enhanced_security.harden_all_containers()
        
        # 6. Run health checks
        print("🏥 Running health checks...")
        health_report = self.health_monitor.check_all_containers()
        
        # 7. Create final snapshot
        self.deployment_manager.create_deployment_snapshot(
            description=f"Rollback completed to {deployment_id}"
        )
        
        print("✅ Rollback completed successfully!")
        return True
    
    def get_system_health(self):
        """Get overall system health"""
        return self.health_monitor.get_health_statistics()
    
    def check_infrastructure_health(self):
        """Check health of all infrastructure"""
        print("🔍 Checking infrastructure health...")
        return self.health_monitor.check_all_containers()


    def update_infrastructure(self):
        print("🔄 Updating infrastructure...")
        self.deploy_infrastructure()
    
    def destroy_infrastructure(self):
        print("🗑️ Destroying infrastructure...")
        self.deployer.cleanup_all()
        self.network_manager.cleanup_networks()
    
    def status_check(self):
        print("📊 Infrastructure Status:")
        try:
            containers = self.docker_client.containers.list(all=True)
            if not containers:
                print("  No containers running")
                return
                
            for container in containers:
                status = "🟢 Running" if container.status == "running" else "🔴 Stopped"
                print(f"  {container.name}: {status}")
        except Exception as e:
            print(f"❌ Error checking status: {e}")
    
    def security_audit(self):
        print("🔒 Running comprehensive security audit...")
        return self.enhanced_security.audit_all_containers()

def main():
    cms = CentralManagementSystem()
    
    if len(sys.argv) < 2:
        print("Usage: python3 main.py [deploy|update|destroy|status|audit|health|history|rollback|check-config]")
        print("\nCommands:")
        print("  deploy          - Deploy complete infrastructure")
        print("  update          - Update infrastructure")
        print("  destroy         - Destroy all infrastructure")
        print("  status          - Show infrastructure status")
        print("  audit           - Run comprehensive security audit")
        print("  health          - Check infrastructure health")
        print("  history         - Show deployment history")
        print("  rollback ID     - Rollback to specific deployment")
        print("  check-config    - Check for configuration changes")
        print("  test-comms      - Test inter-container communications")
        return
    
    command = sys.argv[1]
    
    if command == "deploy":
        cms.deploy_infrastructure()
    elif command == "update":
        cms.update_infrastructure()
    elif command == "destroy":
        cms.destroy_infrastructure()
    elif command == "status":
        cms.status_check()
    elif command == "audit":
        cms.security_audit()
    elif command == "test-comms":
        cms.test_communications()
    elif command == "health":
        health = cms.check_infrastructure_health()
        print(json.dumps(health, indent=2) if health else "No health data")
    elif command == "history":
        history = cms.get_deployment_history()
        for dep in history:
            print(f"  {dep['deployment_id']}: {dep['timestamp']} - {dep['description']}")
    elif command == "rollback" and len(sys.argv) > 2:
        cms.rollback_to_deployment(sys.argv[2])
    elif command == "check-config":
        if cms.check_config_for_changes():
            print("Configuration has changed!")
        else:
            print("No changes detected")
    else:
        print("Invalid command. Use 'python3 main.py' for help")

if __name__ == "__main__":
    import json
    main()

