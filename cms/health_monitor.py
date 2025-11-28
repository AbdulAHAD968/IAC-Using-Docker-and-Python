import docker
import time
from datetime import datetime
import json
from pathlib import Path

class HealthMonitor:
    def __init__(self, docker_client, base_dir=None):
        self.client = docker_client
        self.base_dir = base_dir or "."
        self.health_reports_dir = Path(self.base_dir) / "health_reports"
        self.health_reports_dir.mkdir(parents=True, exist_ok=True)

        self.health_checks = {}
        self.unhealthy_containers = set()

        print(f" Health Monitor initialized")

    def check_container_health(self, container):
        try:
            container.reload()

            health_status = {
                'name': container.name,
                'timestamp': datetime.now().isoformat(),
                'status': container.status,
                'healthy': True,
                'issues': []
            }

            if container.status != 'running':
                health_status['healthy'] = False
                health_status['issues'].append(f"Container not running (status: {container.status})")
                return health_status

            try:
                stats = container.stats(stream=False)
                memory_usage = stats['memory_stats']['usage'] / (1024 * 1024)  
                memory_limit = stats['memory_stats']['limit'] / (1024 * 1024)
                memory_percent = (memory_usage / memory_limit) * 100 if memory_limit > 0 else 0

                health_status['memory_usage_mb'] = round(memory_usage, 2)
                health_status['memory_limit_mb'] = round(memory_limit, 2)
                health_status['memory_percent'] = round(memory_percent, 2)

                if memory_percent > 90:
                    health_status['issues'].append(f"High memory usage: {memory_percent:.1f}%")
            except:
                health_status['memory_usage_mb'] = 'N/A'
                health_status['memory_limit_mb'] = 'N/A'
                health_status['memory_percent'] = 0

            try:
                cpu_stats = stats['cpu_stats']
                cpu_percent = self._calculate_cpu_percent(cpu_stats)
                health_status['cpu_percent'] = round(cpu_percent, 2)
            except:
                health_status['cpu_percent'] = 0

            try:
                networks = container.attrs['NetworkSettings']['Networks']
                health_status['networks'] = list(networks.keys())

                has_ip = False
                for network_name, network_info in networks.items():
                    if network_info.get('IPAddress'):
                        has_ip = True
                        break

                if not has_ip:
                    health_status['healthy'] = False
                    health_status['issues'].append("No IP address assigned")
            except:
                health_status['networks'] = []

            if not health_status['healthy']:
                self.unhealthy_containers.add(container.name)
            else:
                self.unhealthy_containers.discard(container.name)

            return health_status

        except Exception as e:
            return {
                'name': container.name,
                'timestamp': datetime.now().isoformat(),
                'healthy': False,
                'issues': [f"Health check error: {str(e)}"],
                'status': 'error'
            }

    def _calculate_cpu_percent(self, stats):
        try:
            cpu_delta = stats['cpu_usage']['total_usage'] - stats.get('precpu_stats', {}).get('cpu_usage', {}).get('total_usage', 0)
            system_delta = stats['system_cpu_usage'] - stats.get('precpu_stats', {}).get('system_cpu_usage', 0)

            if system_delta > 0:
                cpu_percent = (cpu_delta / system_delta) * 100
                return cpu_percent
            return 0
        except:
            return 0

    def _run_service_specific_checks(self, container, health_status):
        pass

    def check_all_containers(self):
        print(" Running health checks...")

        try:
            containers = self.client.containers.list(all=True)
            health_report = {
                'timestamp': datetime.now().isoformat(),
                'total_containers': len(containers),
                'checked_containers': [],
                'summary': {
                    'healthy': 0,
                    'unhealthy': 0,
                    'stopped': 0
                }
            }

            for container in containers:
                if any(pattern in container.name for pattern in ['web-server-', 'db-server-', 'email-server-', 'client-pc-']):
                    health = self.check_container_health(container)
                    health_report['checked_containers'].append(health)

                    if health.get('status') == 'running':
                        if health.get('healthy'):
                            health_report['summary']['healthy'] += 1
                        else:
                            health_report['summary']['unhealthy'] += 1
                    else:
                        health_report['summary']['stopped'] += 1

            self._save_health_report(health_report)

            summary = health_report['summary']
            print(f" Health Check Summary:")
            print(f"   Healthy: {summary['healthy']}")
            print(f"   Unhealthy: {summary['unhealthy']}")
            print(f"   Stopped: {summary['stopped']}")

            return health_report

        except Exception as e:
            print(f" Health check failed: {e}")
            return None

    def check_network_connectivity(self):
        print(" Checking network connectivity...")

        connectivity_report = {
            'timestamp': datetime.now().isoformat(),
            'connections': []
        }

        try:
            containers = self.client.containers.list()
            container_list = [c for c in containers if any(pattern in c.name for pattern in ['web-server-', 'db-server-', 'email-server-', 'client-pc-'])]

            for source in container_list:
                for target in container_list:
                    if source.name != target.name:
                        target_networks = target.attrs['NetworkSettings']['Networks']
                        for network_name, network_info in target_networks.items():
                            if network_name in ['frontend_net', 'backend_net', 'client_net']:
                                target_ip = network_info.get('IPAddress')
                                if target_ip:
                                    result = source.exec_run(f"timeout 2 nc -z -w 1 {target_ip} 22")
                                    connectivity_report['connections'].append({
                                        'source': source.name,
                                        'target': target.name,
                                        'network': network_name,
                                        'reachable': result.exit_code == 0,
                                        'timestamp': datetime.now().isoformat()
                                    })

        except Exception as e:
            print(f"  Network check error: {e}")

        return connectivity_report

    def _save_health_report(self, report):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = self.health_reports_dir / f"health_report_{timestamp}.json"

            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)

            reports = sorted(self.health_reports_dir.glob("health_report_*.json"))
            if len(reports) > 100:
                for report_to_delete in reports[:-100]:
                    report_to_delete.unlink()

            return True
        except Exception as e:
            print(f"  Error saving health report: {e}")
            return False

    def get_latest_health_report(self):
        try:
            reports = sorted(self.health_reports_dir.glob("health_report_*.json"), reverse=True)
            if reports:
                with open(reports[0], 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"  Error loading health report: {e}")

        return None

    def get_unhealthy_containers(self):
        return list(self.unhealthy_containers)

    def get_health_statistics(self):
        report = self.get_latest_health_report()

        if not report:
            return {
                'status': 'no_data',
                'message': 'No health reports available'
            }

        return {
            'status': 'ok' if report['summary']['unhealthy'] == 0 else 'warning',
            'last_check': report['timestamp'],
            'summary': report['summary'],
            'unhealthy_containers': self.get_unhealthy_containers(),
            'detailed_report': report
        }

    def restart_unhealthy_containers(self, auto_restart=True):
        if not auto_restart:
            return False

        print(" Attempting to restart unhealthy containers...")

        try:
            containers = self.client.containers.list()
            restarted_count = 0

            for container_name in self.unhealthy_containers:
                try:
                    container = self.client.containers.get(container_name)
                    print(f"  ⏸  Restarting {container.name}...")
                    container.restart(timeout=10)
                    print(f"   Restarted {container.name}")
                    restarted_count += 1
                except Exception as e:
                    print(f"   Failed to restart {container_name}: {e}")

            print(f" Restart attempt completed ({restarted_count} containers)")
            return True

        except Exception as e:
            print(f" Auto-restart failed: {e}")
            return False
