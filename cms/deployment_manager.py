import json
import os
from datetime import datetime
from pathlib import Path
import docker

class DeploymentManager:
    def __init__(self, docker_client, base_dir=None):
        self.client = docker_client
        self.base_dir = base_dir or os.path.dirname(__file__)
        self.deployments_dir = os.path.join(self.base_dir, '..', 'deployments')
        self.state_file = os.path.join(self.deployments_dir, 'deployment_state.json')

        Path(self.deployments_dir).mkdir(parents=True, exist_ok=True)

        self.state = self._load_state()

        print(f" Deployment Manager initialized")

    def _load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"  Error loading deployment state: {e}")

        return {
            'current_deployment': None,
            'deployment_history': [],
            'containers': {},
            'networks': []
        }

    def _save_state(self):
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
            return True
        except Exception as e:
            print(f" Error saving deployment state: {e}")
            return False

    def create_deployment_snapshot(self, description="", config=None):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        deployment_id = f"deploy_{timestamp}"

        containers_state = {}
        try:
            containers = self.client.containers.list(all=True)
            for container in containers:
                if any(pattern in container.name for pattern in ['web-server-', 'db-server-', 'email-server-', 'client-pc-']):
                    containers_state[container.name] = {
                        'image': container.image.tags[0] if container.image.tags else 'unknown',
                        'status': container.status,
                        'id': container.id[:12],
                        'created': container.attrs['Created']
                    }
        except Exception as e:
            print(f"  Error capturing container state: {e}")

        snapshot = {
            'deployment_id': deployment_id,
            'timestamp': datetime.now().isoformat(),
            'description': description,
            'containers': containers_state,
            'config': config,
            'status': 'created'
        }

        snapshot_file = os.path.join(self.deployments_dir, f"{deployment_id}.json")
        try:
            with open(snapshot_file, 'w') as f:
                json.dump(snapshot, f, indent=2)

            self.state['current_deployment'] = deployment_id
            self.state['deployment_history'].append({
                'deployment_id': deployment_id,
                'timestamp': snapshot['timestamp'],
                'description': description,
                'container_count': len(containers_state)
            })
            self._save_state()

            print(f" Deployment snapshot created: {deployment_id}")
            return deployment_id
        except Exception as e:
            print(f" Error creating deployment snapshot: {e}")
            return None

    def list_deployments(self, limit=10):
        history = self.state.get('deployment_history', [])
        return history[-limit:] if limit else history

    def get_deployment(self, deployment_id):
        snapshot_file = os.path.join(self.deployments_dir, f"{deployment_id}.json")

        if not os.path.exists(snapshot_file):
            print(f" Deployment not found: {deployment_id}")
            return None

        try:
            with open(snapshot_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f" Error loading deployment: {e}")
            return None

    def get_current_deployment(self):
        current_id = self.state.get('current_deployment')
        if not current_id:
            return None

        return self.get_deployment(current_id)

    def compare_deployments(self, deployment_id1, deployment_id2):
        dep1 = self.get_deployment(deployment_id1)
        dep2 = self.get_deployment(deployment_id2)

        if not dep1 or not dep2:
            print(" One or both deployments not found")
            return None

        differences = {
            'deployment_1': deployment_id1,
            'deployment_2': deployment_id2,
            'containers_added': [],
            'containers_removed': [],
            'containers_modified': [],
            'timestamp_1': dep1['timestamp'],
            'timestamp_2': dep2['timestamp']
        }

        containers1 = dep1.get('containers', {})
        containers2 = dep2.get('containers', {})

        for name in containers2.keys():
            if name not in containers1:
                differences['containers_added'].append(name)

        for name in containers1.keys():
            if name not in containers2:
                differences['containers_removed'].append(name)

        for name in containers1.keys():
            if name in containers2:
                if containers1[name] != containers2[name]:
                    differences['containers_modified'].append({
                        'name': name,
                        'from': containers1[name],
                        'to': containers2[name]
                    })

        return differences

    def mark_deployment_complete(self, deployment_id, status='success'):
        snapshot_file = os.path.join(self.deployments_dir, f"{deployment_id}.json")

        if not os.path.exists(snapshot_file):
            print(f" Deployment not found: {deployment_id}")
            return False

        try:
            with open(snapshot_file, 'r') as f:
                snapshot = json.load(f)

            snapshot['status'] = status
            snapshot['completed_at'] = datetime.now().isoformat()

            with open(snapshot_file, 'w') as f:
                json.dump(snapshot, f, indent=2)

            print(f" Deployment marked as {status}: {deployment_id}")
            return True
        except Exception as e:
            print(f" Error updating deployment: {e}")
            return False

    def can_rollback_to(self, deployment_id):
        deployment = self.get_deployment(deployment_id)
        if not deployment:
            return False, "Deployment not found"

        containers_status = deployment.get('containers', {})

        for container_name, container_info in containers_status.items():
            pass

        return True, "Rollback available"

    def get_rollback_plan(self, deployment_id):
        target_deployment = self.get_deployment(deployment_id)
        current_deployment = self.get_current_deployment()

        if not target_deployment:
            return None

        if not current_deployment:
            current_containers = {}
        else:
            current_containers = current_deployment.get('containers', {})

        target_containers = target_deployment.get('containers', {})

        plan = {
            'source_deployment': current_deployment['deployment_id'] if current_deployment else 'unknown',
            'target_deployment': deployment_id,
            'actions': []
        }

        for container_name in current_containers.keys():
            if container_name not in target_containers:
                plan['actions'].append({
                    'type': 'remove',
                    'container': container_name,
                    'reason': 'Not in target deployment'
                })

        for container_name, container_info in target_containers.items():
            if container_name not in current_containers:
                plan['actions'].append({
                    'type': 'create',
                    'container': container_name,
                    'image': container_info['image'],
                    'reason': 'Missing in current deployment'
                })

        for container_name in target_containers.keys():
            if container_name in current_containers:
                plan['actions'].append({
                    'type': 'verify',
                    'container': container_name,
                    'reason': 'Verify state matches'
                })

        return plan

    def export_deployment_report(self, deployment_id=None):
        if deployment_id is None:
            deployment_id = self.state.get('current_deployment')

        if not deployment_id:
            print(" No deployment to export")
            return None

        deployment = self.get_deployment(deployment_id)
        if not deployment:
            return None

        report = {
            'deployment_id': deployment['deployment_id'],
            'timestamp': deployment['timestamp'],
            'description': deployment['description'],
            'status': deployment['status'],
            'container_summary': {
                'total': len(deployment.get('containers', {})),
                'by_type': {
                    'web': len([c for c in deployment.get('containers', {}).keys() if 'web-server' in c]),
                    'db': len([c for c in deployment.get('containers', {}).keys() if 'db-server' in c]),
                    'email': len([c for c in deployment.get('containers', {}).keys() if 'email-server' in c]),
                    'client': len([c for c in deployment.get('containers', {}).keys() if 'client-pc' in c])
                }
            },
            'containers': deployment.get('containers', {})
        }

        return report

    def get_deployment_statistics(self):
        history = self.state.get('deployment_history', [])

        return {
            'total_deployments': len(history),
            'current_deployment': self.state.get('current_deployment'),
            'recent_deployments': history[-5:] if len(history) >= 5 else history,
            'deployments_directory': self.deployments_dir,
            'storage_used': self._get_directory_size(self.deployments_dir)
        }

    def _get_directory_size(self, directory):
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(directory):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)
        except Exception as e:
            print(f"  Error calculating directory size: {e}")

        return total_size
