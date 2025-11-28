#!/usr/bin/env python3

import os
import sys
import json
import docker
import threading
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

# Add cms directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'cms'))

from cms.main import CentralManagementSystem
from cms.deploy import InfrastructureDeployer

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# Global variables
cms = None
deployment_in_progress = False
deployment_status = "idle"
deployment_logs = []


def init_cms():
    """Initialize the CMS system with better error handling"""
    global cms
    
    # Fix Docker socket permissions first
    docker_socket = '/var/run/docker.sock'
    if os.path.exists(docker_socket):
        try:
            # Ensure we have read/write permissions
            import stat
            st = os.stat(docker_socket)
            if not (st.st_mode & stat.S_IROTH and st.st_mode & stat.S_IWOTH):
                print(f"⚠️ Docker socket permissions: {oct(st.st_mode)}")
                print("📌 If permission errors occur, run: sudo chmod 666 /var/run/docker.sock")
        except Exception as e:
            print(f"⚠️ Could not check Docker socket permissions: {e}")
    
    try:
        print("🔧 Testing Docker connection...")
        
        # Set Docker environment explicitly
        os.environ['DOCKER_HOST'] = 'unix:///var/run/docker.sock'
        
        # Test Docker connection with timeout
        client = docker.from_env(timeout=10)
        client.ping()
        print("✅ Docker daemon is accessible")
        
        # Now initialize CMS
        print("🔧 Initializing CentralManagementSystem...")
        cms = CentralManagementSystem()
        print("✅ CMS initialized successfully with Docker")
        return True
        
    except docker.errors.DockerException as e:
        print(f"❌ Docker connection failed: {e}")
        
        # Try alternative connection methods
        connection_methods = [
            {'base_url': 'unix:///var/run/docker.sock'},
            {'base_url': 'unix:///var/run/docker.sock', 'version': 'auto'},
            {'base_url': 'unix:///var/run/docker.sock', 'timeout': 30},
        ]
        
        for config in connection_methods:
            try:
                print(f"🔧 Trying alternative connection: {config}...")
                client = docker.DockerClient(**config)
                client.ping()
                print("✅ Connected via alternative method")
                cms = CentralManagementSystem()
                return True
            except Exception as e:
                print(f"❌ Alternative failed: {e}")
                continue
        
        print(f"❌ All Docker connection attempts failed")
        print(f"📌 Please ensure:")
        print(f"   1. Docker is running: sudo systemctl start docker")
        print(f"   2. User has Docker permissions: sudo usermod -aG docker $USER && newgrp docker")
        print(f"   3. Socket permissions: sudo chmod 666 /var/run/docker.sock (temporary fix)")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error initializing CMS: {e}")
        import traceback
        traceback.print_exc()
        return False


def log_deployment(message):
    """Add message to deployment logs"""
    global deployment_logs
    deployment_logs.append(message)
    print(f"📝 {message}")

def deploy_in_background():
    """Deploy infrastructure in background thread"""
    global deployment_in_progress, deployment_status
    try:
        deployment_status = "deploying"
        log_deployment("🚀 Starting infrastructure deployment...")
        
        # Create networks
        log_deployment("📡 Creating networks...")
        cms.network_manager.create_networks()
        
        # Deploy containers
        log_deployment("🐳 Deploying containers...")
        cms.deployer.deploy_all()
        
        # Wait for containers to start
        log_deployment("⏳ Waiting for containers to initialize...")
        import time
        time.sleep(10)
        
        # Setup network connectivity
        log_deployment("🔗 Setting up network connectivity...")
        cms.network_manager.setup_network_connectivity()
        
        # Apply security hardening
        log_deployment("🔒 Applying security hardening...")
        cms.security_manager.harden_all_containers()
        
        # Wait for database
        log_deployment("⏳ Waiting for database to be ready...")
        time.sleep(15)
        
        # Test communications
        log_deployment("🔍 Testing communications...")
        cms.communication_tester.test_all_communications()
        
        deployment_status = "completed"
        log_deployment("✅ Infrastructure deployment completed successfully!")
        
    except Exception as e:
        deployment_status = "failed"
        log_deployment(f"❌ Deployment failed: {str(e)}")
        import traceback
        log_deployment(f"Stack trace: {traceback.format_exc()}")
    finally:
        deployment_in_progress = False

# ==================== API ENDPOINTS ====================

@app.route('/')
def index():
    """Serve the frontend"""
    return render_template('index.html')

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get overall system status"""
    try:
        if cms is None:
            return jsonify({
                'status': 'limited',
                'message': 'Docker daemon not available - limited mode',
                'deployment_status': deployment_status,
                'containers': [],
                'container_count': 0
            }), 200
        
        containers = cms.docker_client.containers.list(all=True)
        
        container_status = []
        for container in containers:
            if any(pattern in container.name for pattern in ['web-server-', 'db-server-', 'email-server-', 'client-pc-']):
                container_status.append({
                    'name': container.name,
                    'status': container.status,
                    'image': container.image.tags[0] if container.image.tags else 'unknown',
                    'id': container.id[:12]
                })
        
        return jsonify({
            'status': 'running',
            'deployment_status': deployment_status,
            'deployment_in_progress': deployment_in_progress,
            'containers': container_status,
            'container_count': len(container_status)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/deployment/status', methods=['GET'])
def get_deployment_status():
    """Get deployment status"""
    return jsonify({
        'status': deployment_status,
        'in_progress': deployment_in_progress,
        'logs': deployment_logs[-50:]  # Last 50 log entries
    }), 200

@app.route('/api/deploy', methods=['POST'])
def deploy():
    """Deploy the entire infrastructure"""
    global deployment_in_progress
    
    if deployment_in_progress:
        return jsonify({'error': 'Deployment already in progress'}), 400
    
    if cms is None:
        return jsonify({
            'error': 'CMS not initialized',
            'message': 'Docker daemon is not accessible. Please check Docker is running and permissions are set.'
        }), 503
    
    deployment_in_progress = True
    deployment_logs.clear()
    
    # Start deployment in background thread
    thread = threading.Thread(target=deploy_in_background)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'message': 'Deployment started',
        'status': 'deploying'
    }), 202

@app.route('/api/create-client', methods=['POST'])
def create_client():
    """Create a new client container"""
    try:
        if cms is None:
            return jsonify({'error': 'CMS not initialized'}), 500
        
        data = request.get_json()
        client_name = data.get('name', 'client-pc-new')
        
        # Get next client number
        client_containers = cms.docker_client.containers.list(filters={'name': 'client-pc-'})
        next_number = len(client_containers) + 1
        final_name = f"client-pc-{next_number}"
        
        log_deployment(f"🐳 Creating new client: {final_name}")
        
        # Deploy new client
        container = cms.docker_client.containers.run(
            "ubuntu:22.04",
            name=final_name,
            network="frontend_net",
            detach=True,
            command="tail -f /dev/null",
            restart_policy={"Name": "unless-stopped"}
        )
        
        log_deployment(f"✅ Client {final_name} created successfully")
        
        return jsonify({
            'message': f'Client {final_name} created successfully',
            'container': {
                'name': final_name,
                'id': container.id[:12],
                'status': container.status
            }
        }), 201
        
    except Exception as e:
        log_deployment(f"❌ Failed to create client: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stop-container/<container_name>', methods=['POST'])
def stop_container(container_name):
    """Stop a specific container"""
    try:
        if cms is None:
            return jsonify({'error': 'CMS not initialized'}), 500
        
        container = cms.docker_client.containers.get(container_name)
        log_deployment(f"🛑 Stopping container: {container_name}")
        
        container.stop(timeout=10)
        log_deployment(f"✅ Container {container_name} stopped successfully")
        
        return jsonify({
            'message': f'Container {container_name} stopped successfully',
            'container': {
                'name': container_name,
                'status': 'stopped'
            }
        }), 200
        
    except docker.errors.NotFound:
        return jsonify({'error': f'Container {container_name} not found'}), 404
    except Exception as e:
        log_deployment(f"❌ Failed to stop container: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/start-container/<container_name>', methods=['POST'])
def start_container(container_name):
    """Start a stopped container"""
    try:
        if cms is None:
            return jsonify({'error': 'CMS not initialized'}), 500
        
        container = cms.docker_client.containers.get(container_name)
        log_deployment(f"▶️ Starting container: {container_name}")
        
        container.start()
        log_deployment(f"✅ Container {container_name} started successfully")
        
        return jsonify({
            'message': f'Container {container_name} started successfully',
            'container': {
                'name': container_name,
                'status': 'running'
            }
        }), 200
        
    except docker.errors.NotFound:
        return jsonify({'error': f'Container {container_name} not found'}), 404
    except Exception as e:
        log_deployment(f"❌ Failed to start container: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/remove-container/<container_name>', methods=['DELETE'])
def remove_container(container_name):
    """Remove a container"""
    try:
        if cms is None:
            return jsonify({'error': 'CMS not initialized'}), 500
        
        container = cms.docker_client.containers.get(container_name)
        log_deployment(f"🗑️ Removing container: {container_name}")
        
        if container.status == 'running':
            container.stop(timeout=10)
        
        container.remove()
        log_deployment(f"✅ Container {container_name} removed successfully")
        
        return jsonify({
            'message': f'Container {container_name} removed successfully'
        }), 200
        
    except docker.errors.NotFound:
        return jsonify({'error': f'Container {container_name} not found'}), 404
    except Exception as e:
        log_deployment(f"❌ Failed to remove container: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/cleanup', methods=['POST'])
def cleanup():
    """Cleanup all infrastructure"""
    try:
        if cms is None:
            return jsonify({'error': 'CMS not initialized'}), 500
        
        log_deployment("🗑️ Cleaning up all infrastructure...")
        cms.destroy_infrastructure()
        log_deployment("✅ Infrastructure cleaned up successfully")
        
        return jsonify({
            'message': 'Infrastructure cleaned up successfully'
        }), 200
        
    except Exception as e:
        log_deployment(f"❌ Cleanup failed: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/security-audit', methods=['GET'])
def security_audit():
    """Run security audit"""
    try:
        if cms is None:
            return jsonify({'error': 'CMS not initialized'}), 500
        
        log_deployment("🔒 Running security audit...")
        # Call the security audit method
        audit_result = cms.security_manager.audit_all_containers()
        log_deployment("✅ Security audit completed")
        
        return jsonify({
            'message': 'Security audit completed',
            'result': audit_result if audit_result else 'Check logs for details'
        }), 200
        
    except Exception as e:
        log_deployment(f"❌ Security audit failed: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'Server error'}), 500

if __name__ == '__main__':
    print("🚀 Initializing CMS system...")
    cms_initialized = init_cms()
    if cms_initialized:
        print("✅ CMS initialized successfully - Full mode (all features available)")
    else:
        print("⚠️ CMS initialization failed - Limited mode (dashboard only)")
        print("📌 To enable full functionality:")
        print("   → Ensure Docker is running: sudo systemctl start docker")
        print("   → Check permissions: ls -la /var/run/docker.sock")
        print("   → Add user to docker group: sudo usermod -aG docker $USER && newgrp docker")
    
    print("")
    print("🌐 Starting Flask server on http://0.0.0.0:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)