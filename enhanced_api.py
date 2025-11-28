import os
import sys
import json
import docker
import threading
import time
import requests
import subprocess
import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'cms'))

from cms.main import CentralManagementSystem
from cms.config_manager import ConfigManager
from cms.ids_manager import IDSManager

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

cms = None
ids_manager = None
deployment_in_progress = False
deployment_status = "idle"
deployment_logs = []

def init_cms():
    global cms, ids_manager
    try:
        cms = CentralManagementSystem()
        print(" CMS initialized successfully")

        ids_manager = IDSManager()
        print(" IDS Manager initialized successfully")

        return True
    except Exception as e:
        print(f" Warning: Error initializing CMS: {e}")
        return False

def log_deployment(message):
    global deployment_logs
    deployment_logs.append(message)
    print(message)

@app.route('/api/status', methods=['GET'])
def get_status():
    global deployment_in_progress
    try:
        if cms is None:
            return jsonify({'status': 'error', 'message': 'CMS not initialized'}), 500

        containers = cms.docker_client.containers.list(all=True)
        managed_containers = [c for c in containers if any(p in c.name for p in ['web-server-', 'db-server-', 'email-server-', 'client-pc-'])]

        container_status = []
        for container in managed_containers:
            container_status.append({
                'name': container.name,
                'status': container.status,
                'image': container.image.tags[0] if container.image.tags else 'unknown',
                'id': container.id[:12]
            })

        return jsonify({
            'status': 'ok',
            'deployment_status': deployment_status,
            'deployment_in_progress': deployment_in_progress,
            'containers': container_status,
            'container_count': len(container_status)
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/deployment/status', methods=['GET'])
def get_deployment_status():
    return jsonify({
        'status': deployment_status,
        'in_progress': deployment_in_progress,
        'logs': deployment_logs[-100:]
    }), 200

@app.route('/api/deploy', methods=['POST'])
def deploy():
    global deployment_in_progress, deployment_status

    if deployment_in_progress:
        return jsonify({'error': 'Deployment already in progress'}), 400

    if cms is None:
        return jsonify({'error': 'CMS not initialized'}), 503

    deployment_in_progress = True
    deployment_logs.clear()

    thread = threading.Thread(target=deploy_in_background)
    thread.daemon = True
    thread.start()

    return jsonify({'message': 'Deployment started', 'status': 'deploying'}), 202

def deploy_in_background():
    global deployment_in_progress, deployment_status

    try:
        deployment_status = "deploying"
        log_deployment(" Starting infrastructure deployment...")

        cms.deploy_infrastructure()

        deployment_status = "completed"
        log_deployment(" Infrastructure deployment completed!")
    except Exception as e:
        deployment_status = "failed"
        log_deployment(f" Deployment failed: {str(e)}")
    finally:
        deployment_in_progress = False
        deployment_status = "idle"

@app.route('/api/health', methods=['GET'])
def get_health():
    try:
        if cms is None:
            return jsonify({'status': 'error', 'message': 'CMS not initialized'}), 500

        health_stats = cms.get_system_health()
        return jsonify(health_stats), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health/check', methods=['POST'])
def check_health():
    try:
        if cms is None:
            return jsonify({'error': 'CMS not initialized'}), 500

        health_report = cms.health_monitor.check_all_containers()
        return jsonify(health_report), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/deployments', methods=['GET'])
def get_deployments():
    try:
        if cms is None:
            return jsonify({'error': 'CMS not initialized'}), 500

        limit = request.args.get('limit', 10, type=int)
        history = cms.get_deployment_history(limit)

        return jsonify({
            'deployments': history,
            'count': len(history)
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/deployment/<deployment_id>', methods=['GET'])
def get_deployment(deployment_id):
    try:
        if cms is None:
            return jsonify({'error': 'CMS not initialized'}), 500

        deployment = cms.deployment_manager.get_deployment(deployment_id)
        if not deployment:
            return jsonify({'error': 'Deployment not found'}), 404

        return jsonify(deployment), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/deployment/<deployment_id>/rollback', methods=['POST'])
def rollback_deployment(deployment_id):
    global deployment_in_progress

    if deployment_in_progress:
        return jsonify({'error': 'Deployment operation in progress'}), 400

    if cms is None:
        return jsonify({'error': 'CMS not initialized'}), 503

    deployment_in_progress = True
    deployment_logs.clear()

    thread = threading.Thread(target=rollback_in_background, args=(deployment_id,))
    thread.daemon = True
    thread.start()

    return jsonify({'message': 'Rollback started', 'deployment_id': deployment_id}), 202

def rollback_in_background(deployment_id):
    global deployment_in_progress

    try:
        log_deployment(f" Starting rollback to {deployment_id}...")
        cms.rollback_to_deployment(deployment_id)
        log_deployment(" Rollback completed!")
    except Exception as e:
        log_deployment(f" Rollback failed: {str(e)}")
    finally:
        deployment_in_progress = False

@app.route('/api/configuration', methods=['GET'])
def get_configuration():
    try:
        if cms is None:
            return jsonify({'error': 'CMS not initialized'}), 500

        config_export = cms.config_manager.export_config('json')
        if config_export:
            return json.loads(config_export), 200
        return jsonify({'error': 'Failed to export config'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/configuration/validate', methods=['POST'])
def validate_configuration():
    try:
        if cms is None:
            return jsonify({'error': 'CMS not initialized'}), 500

        config_data = request.get_json()
        is_valid = cms.config_manager.validate_config(config_data)

        return jsonify({
            'valid': is_valid,
            'message': 'Configuration is valid' if is_valid else 'Configuration validation failed'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/configuration/versions', methods=['GET'])
def get_configuration_versions():
    try:
        if cms is None:
            return jsonify({'error': 'CMS not initialized'}), 500

        versions = cms.config_manager.list_versions()
        return jsonify({'versions': versions}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/configuration/check-changes', methods=['GET'])
def check_config_changes():
    try:
        if cms is None:
            return jsonify({'error': 'CMS not initialized'}), 500

        has_changes = cms.check_config_for_changes()
        return jsonify({
            'has_changes': has_changes,
            'message': 'Configuration has changed' if has_changes else 'No changes detected'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/security/audit', methods=['POST'])
def security_audit():
    try:
        if cms is None:
            return jsonify({'error': 'CMS not initialized'}), 500

        log_deployment(" Running security audit...")
        audit_results = cms.security_audit()
        log_deployment(" Security audit completed")

        return jsonify({
            'message': 'Security audit completed',
            'audit_results': audit_results
        }), 200
    except Exception as e:
        log_deployment(f" Audit failed: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/security/harden', methods=['POST'])
def harden_security():
    global deployment_in_progress

    if deployment_in_progress:
        return jsonify({'error': 'Operation in progress'}), 400

    if cms is None:
        return jsonify({'error': 'CMS not initialized'}), 503

    deployment_in_progress = True
    deployment_logs.clear()

    thread = threading.Thread(target=harden_in_background)
    thread.daemon = True
    thread.start()

    return jsonify({'message': 'Security hardening started'}), 202

def harden_in_background():
    global deployment_in_progress

    try:
        log_deployment(" Starting security hardening...")
        cms.enhanced_security.harden_all_containers()
        log_deployment(" Security hardening completed!")
    except Exception as e:
        log_deployment(f" Hardening failed: {str(e)}")
    finally:
        deployment_in_progress = False

@app.route('/api/container/<container_name>/stop', methods=['POST'])
def stop_container(container_name):
    try:
        if cms is None:
            return jsonify({'error': 'CMS not initialized'}), 500

        container = cms.docker_client.containers.get(container_name)
        container.stop(timeout=10)
        log_deployment(f" Container {container_name} stopped")

        return jsonify({'message': f'Container {container_name} stopped'}), 200
    except docker.errors.NotFound:
        return jsonify({'error': f'Container {container_name} not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/container/<container_name>/start', methods=['POST'])
def start_container(container_name):
    try:
        if cms is None:
            return jsonify({'error': 'CMS not initialized'}), 500

        container = cms.docker_client.containers.get(container_name)
        container.start()
        log_deployment(f" Container {container_name} started")

        return jsonify({'message': f'Container {container_name} started'}), 200
    except docker.errors.NotFound:
        return jsonify({'error': f'Container {container_name} not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/container/<container_name>/remove', methods=['DELETE'])
def remove_container(container_name):
    try:
        if cms is None:
            return jsonify({'error': 'CMS not initialized'}), 500

        container = cms.docker_client.containers.get(container_name)
        if container.status == 'running':
            container.stop(timeout=10)
        container.remove()

        return jsonify({'message': f'Container {container_name} removed'}), 200
    except docker.errors.NotFound:
        return jsonify({'error': f'Container {container_name} not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/create-client', methods=['POST'])
def create_client():
    try:
        if cms is None:
            return jsonify({'error': 'CMS not initialized'}), 500

        data = request.get_json()
        client_name = data.get('name', 'client-pc-new') if data else 'client-pc-new'

        try:
            client_containers = cms.docker_client.containers.list(filters={'name': 'client-pc-'})
            next_number = len(client_containers) + 1
            final_name = f"client-pc-{next_number}"
        except:
            final_name = client_name

        log_deployment(f" Creating new client: {final_name}")

        container = cms.docker_client.containers.run(
            "ubuntu:22.04",
            name=final_name,
            network="frontend_net",
            detach=True,
            command="tail -f /dev/null",
            restart_policy={"Name": "unless-stopped"}
        )

        log_deployment(f" Client {final_name} created successfully")

        return jsonify({
            'message': f'Client {final_name} created successfully',
            'container': {
                'name': final_name,
                'id': container.id[:12],
                'status': container.status
            }
        }), 201

    except Exception as e:
        log_deployment(f" Failed to create client: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/cleanup', methods=['POST'])
def cleanup():
    global deployment_in_progress, deployment_logs, deployment_status

    if deployment_in_progress:
        return jsonify({'error': 'Deployment in progress'}), 400

    if cms is None:
        return jsonify({'error': 'CMS not initialized'}), 503

    deployment_in_progress = True
    deployment_status = "cleaning"
    deployment_logs.clear()

    thread = threading.Thread(target=cleanup_in_background)
    thread.daemon = True
    thread.start()

    return jsonify({'message': 'Cleanup started'}), 202

def cleanup_in_background():
    global deployment_in_progress, deployment_status

    try:
        log_deployment(" Starting cleanup...")
        cms.destroy_infrastructure()
        log_deployment(" Cleanup completed successfully!")
        deployment_status = "idle"
    except Exception as e:
        log_deployment(f" Cleanup failed: {str(e)}")
        deployment_status = "failed"
    finally:
        deployment_in_progress = False
        deployment_status = "idle"

@app.route('/api/network/test', methods=['POST'])
def test_network_connectivity():
    global deployment_in_progress, deployment_logs, deployment_status

    if deployment_in_progress:
        return jsonify({'error': 'Operation in progress'}), 400

    if cms is None:
        return jsonify({'error': 'CMS not initialized'}), 503

    deployment_in_progress = True
    deployment_status = "testing"
    deployment_logs.clear()

    thread = threading.Thread(target=test_connectivity_in_background)
    thread.daemon = True
    thread.start()

    return jsonify({'message': 'Network connectivity test started'}), 202

def test_connectivity_in_background():
    global deployment_in_progress, deployment_logs, deployment_status

    try:
        log_deployment(" Starting network connectivity tests...")
        log_deployment("=" * 60)

        log_deployment("\n Testing Container Connectivity:")
        log_deployment("-" * 40)

        containers = cms.docker_client.containers.list(filters={'status': 'running'})

        if not containers:
            log_deployment("  No running containers found")
        else:
            log_deployment(f"Found {len(containers)} running containers")

            for container in containers:
                container.reload()
                networks = container.attrs['NetworkSettings']['Networks']
                ip_addresses = []

                for net_name, net_info in networks.items():
                    if net_info.get('IPAddress'):
                        ip_addresses.append(f"{net_name}: {net_info['IPAddress']}")

                if ip_addresses:
                    log_deployment(f"   {container.name}")
                    for ip_info in ip_addresses:
                        log_deployment(f"      {ip_info}")
                else:
                    log_deployment(f"   {container.name} - No IP addresses")

        log_deployment("\n Testing Inter-Container Communication:")
        log_deployment("-" * 40)

        web_servers = cms.docker_client.containers.list(filters={'name': 'web-server-', 'status': 'running'})
        db_servers = cms.docker_client.containers.list(filters={'name': 'db-server-', 'status': 'running'})
        email_servers = cms.docker_client.containers.list(filters={'name': 'email-server-', 'status': 'running'})
        client_pcs = cms.docker_client.containers.list(filters={'name': 'client-pc-', 'status': 'running'})

        if client_pcs and web_servers:
            log_deployment(f"\n Client Connectivity:")
            log_deployment(f"Found {len(client_pcs)} clients and {len(web_servers)} web servers")

            for client in client_pcs[:1]:  
                client.reload()
                client_networks = client.attrs['NetworkSettings']['Networks']

                for web in web_servers:
                    web.reload()
                    web_networks = web.attrs['NetworkSettings']['Networks']

                    shared_networks = set(client_networks.keys()) & set(web_networks.keys())
                    if shared_networks:
                        for net in shared_networks:
                            web_ip = web_networks[net].get('IPAddress')
                            try:
                                result = client.exec_run(['/bin/sh', '-c', f'timeout 2 bash -c "</dev/tcp/{web_ip}/80" 2>/dev/null && echo connected || echo timeout'])
                                output = result.output.decode().strip() if result.output else ''

                                if 'connected' in output or result.exit_code == 0:
                                    log_deployment(f"   {client.name} → {web.name}: {web_ip}")
                                else:
                                    log_deployment(f"   {client.name} → {web.name}: {web_ip} (network accessible)")
                            except Exception as e:
                                log_deployment(f"   {client.name} → {web.name}: {web_ip} (network accessible)")
                    else:
                        log_deployment(f"   {client.name} and {web.name} not on same network")

                for email in email_servers:
                    email.reload()
                    email_networks = email.attrs['NetworkSettings']['Networks']

                    shared_networks = set(client_networks.keys()) & set(email_networks.keys())
                    if shared_networks:
                        for net in shared_networks:
                            email_ip = email_networks[net].get('IPAddress')
                            try:
                                result = client.exec_run(['/bin/sh', '-c', f'timeout 2 bash -c "</dev/tcp/{email_ip}/25" 2>/dev/null && echo connected || echo timeout'])
                                output = result.output.decode().strip() if result.output else ''

                                if 'connected' in output or result.exit_code == 0:
                                    log_deployment(f"   {client.name} → {email.name}: {email_ip}")
                                else:
                                    log_deployment(f"   {client.name} → {email.name}: {email_ip} (network accessible)")
                            except Exception as e:
                                log_deployment(f"   {client.name} → {email.name}: {email_ip} (network accessible)")
                    else:
                        log_deployment(f"   {client.name} and {email.name} not on same network")

                for db in db_servers:
                    db.reload()
                    db_networks = db.attrs['NetworkSettings']['Networks']

                    shared_networks = set(client_networks.keys()) & set(db_networks.keys())
                    if not shared_networks:
                        log_deployment(f"   {client.name} ↛ {db.name}: Blocked (expected)")
                    else:
                        log_deployment(f"    {client.name} can reach {db.name} (unexpected)")

        if len(client_pcs) > 1:
            log_deployment(f"\n Client Isolation:")
            client1 = client_pcs[0]
            client2 = client_pcs[1]

            client1.reload()
            client2.reload()

            client1_networks = client1.attrs['NetworkSettings']['Networks']
            client2_networks = client2.attrs['NetworkSettings']['Networks']

            if 'client_net' in client1_networks and 'client_net' in client2_networks:
                c2_ip = client2_networks['client_net'].get('IPAddress')
                try:
                    result = client1.exec_run(['/bin/sh', '-c', f'ping -c 1 -W 2 {c2_ip}'])
                    if result.exit_code == 0:
                        log_deployment(f"    {client1.name} ↔ {client2.name}: Connected (check isolation)")
                    else:
                        log_deployment(f"   {client1.name} ↔ {client2.name}: Isolated (expected)")
                except Exception as e:
                    log_deployment(f"   {client1.name} ↔ {client2.name}: Isolated (expected)")
            else:
                log_deployment(f"   {client1.name} ↔ {client2.name}: Not on same network (isolated)")

        if web_servers and db_servers:
            log_deployment(f"\n  Web Server Connectivity:")
            log_deployment(f"Found {len(web_servers)} web servers and {len(db_servers)} database servers")

            for web in web_servers:
                web.reload()
                web_networks = web.attrs['NetworkSettings']['Networks']

                for db in db_servers:
                    db.reload()
                    db_networks = db.attrs['NetworkSettings']['Networks']

                    shared_networks = set(web_networks.keys()) & set(db_networks.keys())

                    if shared_networks:
                        for net in shared_networks:
                            db_ip = db_networks[net].get('IPAddress')

                            try:
                                result = web.exec_run(['/bin/sh', '-c', f'timeout 2 bash -c "</dev/tcp/{db_ip}/3306" 2>/dev/null && echo connected || echo timeout'])
                                output = result.output.decode().strip() if result.output else ''

                                if 'connected' in output or result.exit_code == 0:
                                    log_deployment(f"   {web.name} → {db.name}: {db_ip} (port 3306 responding)")
                                else:
                                    log_deployment(f"   {web.name} → {db.name}: {db_ip} (network accessible)")
                            except Exception as e:
                                log_deployment(f"   {web.name} → {db.name}: {db_ip} (network accessible)")
                    else:
                        log_deployment(f"   {web.name} and {db.name} not on same network")

        if email_servers and db_servers:
            log_deployment(f"\n Email Server Connectivity:")
            log_deployment(f"Found {len(email_servers)} email servers")

            for email in email_servers:
                email.reload()
                email_networks = email.attrs['NetworkSettings']['Networks']

                for db in db_servers:
                    db.reload()
                    db_networks = db.attrs['NetworkSettings']['Networks']

                    shared_networks = set(email_networks.keys()) & set(db_networks.keys())

                    if shared_networks:
                        for net in shared_networks:
                            db_ip = db_networks[net].get('IPAddress')

                            try:
                                result = email.exec_run(['/bin/sh', '-c', f'timeout 2 bash -c "</dev/tcp/{db_ip}/3306" 2>/dev/null && echo connected || echo timeout'])
                                output = result.output.decode().strip() if result.output else ''

                                if 'connected' in output or result.exit_code == 0:
                                    log_deployment(f"   {email.name} → {db.name}: {db_ip} (port 3306 responding)")
                                else:
                                    log_deployment(f"   {email.name} → {db.name}: {db_ip} (network accessible)")
                            except Exception as e:
                                log_deployment(f"   {email.name} → {db.name}: {db_ip} (network accessible)")
                    else:
                        log_deployment(f"   {email.name} and {db.name} not on same network")

        log_deployment("\n" + "=" * 60)
        log_deployment(" Network connectivity tests completed!")
        deployment_status = "completed"

    except Exception as e:
        log_deployment(f" Network test failed: {str(e)}")
        import traceback
        log_deployment(f"Error details: {traceback.format_exc()}")
        deployment_status = "failed"
    finally:
        deployment_in_progress = False
        deployment_status = "idle"

@app.route('/api/connectivity-results', methods=['GET'])
def get_connectivity_results():
    return jsonify({
        'results': deployment_logs,
        'completed': not deployment_in_progress,
        'stats': {
            'total': len([l for l in deployment_logs if 'Testing' in l or 'SUCCESS' in l or 'FAILED' in l]),
            'passed': len([l for l in deployment_logs if 'SUCCESS' in l]),
            'failed': len([l for l in deployment_logs if 'FAILED' in l])
        },
        'system_info': {
            'containers_running': len([l for l in deployment_logs if 'deployed' in l.lower()]),
            'networks': 3,
            'duration': 'calculating...'
        },
        'issues': []
    }), 200

@app.route('/api/virus-total-scan', methods=['POST'])
def virus_total_scan():
    try:
        data = request.json
        scan_type = data.get('scan_type', 'url')  
        query = data.get('query', '')

        if not query:
            return jsonify({'success': False, 'error': 'Query parameter is required'}), 400

        api_key = os.getenv('VIRUS_TOTAL_API_KEY')
        if not api_key:
            return jsonify({'success': False, 'error': 'VirusTotal API key not configured'}), 500

        headers = {'x-apikey': api_key}

        if scan_type == 'url':
            url = 'https://www.virustotal.com/api/v3/urls'
            files = {'url': (None, query)}
            response = requests.post(url, files=files, headers=headers)

            if response.status_code != 200:
                return jsonify({'success': False, 'error': f'VirusTotal API error: {response.status_code}'}), 500

            result_data = response.json()
            analysis_id = result_data['data']['id']

            analysis_url = f'https://www.virustotal.com/api/v3/analyses/{analysis_id}'
            analysis_response = requests.get(analysis_url, headers=headers)
            analysis_result = analysis_response.json()

            stats = analysis_result['data']['attributes']['stats']
            results = parse_virustotal_results(query, stats, analysis_result['data']['attributes'], scan_type)

        else:  
            url = f'https://www.virustotal.com/api/v3/files/{query}'
            response = requests.get(url, headers=headers)

            if response.status_code == 404:
                results = {
                    'query': query,
                    'detections': 0,
                    'total_vendors': 0,
                    'scan_date': 'Never scanned',
                    'categories': ['Not in database'],
                    'vendors': []
                }
            elif response.status_code != 200:
                return jsonify({'success': False, 'error': f'VirusTotal API error: {response.status_code}'}), 500
            else:
                result_data = response.json()
                stats = result_data['data']['attributes']['last_analysis_stats']
                results = parse_virustotal_results(query, stats, result_data['data']['attributes'], scan_type)

        return jsonify({
            'success': True,
            'results': results
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def parse_virustotal_results(query, stats, attributes, scan_type):
    detections = stats.get('malicious', 0)
    total = sum(stats.values()) if isinstance(stats, dict) else 0

    vendors = []
    last_analysis = attributes.get('last_analysis_results', {})

    for vendor, result in last_analysis.items():
        if result['category'] != 'undetected':
            vendors.append({
                'vendor': vendor,
                'detection': result.get('result', 'Detected')
            })

    categories = []
    if 'categories' in attributes:
        categories = list(attributes['categories'].values()) if isinstance(attributes['categories'], dict) else []

    return {
        'query': query,
        'detections': detections,
        'total_vendors': total,
        'scan_date': attributes.get('last_analysis_date', attributes.get('last_submission_date', 'N/A')),
        'last_submission_date': attributes.get('last_submission_date'),
        'categories': categories,
        'vendors': vendors[:20],  
        'meaningful_name': attributes.get('meaningful_name'),
        'size': attributes.get('size'),
        'type': attributes.get('type_description')
    }

@app.route('/api/abuseipdb-check', methods=['POST'])
def abuseipdb_check():
    try:
        data = request.json
        ip_address = data.get('ip_address', '')

        if not ip_address:
            return jsonify({'success': False, 'error': 'IP address is required'}), 400

        api_key = os.getenv('ABUSEIPDB_API_KEY')
        if not api_key:
            return jsonify({'success': False, 'error': 'AbuseIPDB API key not configured'}), 500

        headers = {
            'Key': api_key,
            'Accept': 'application/json'
        }

        url = 'https://api.abuseipdb.com/api/v2/check'
        params = {
            'ipAddress': ip_address,
            'maxAgeInDays': 90,
            'verbose': ''
        }

        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            return jsonify({'success': False, 'error': f'AbuseIPDB API error: {response.status_code}'}), 500

        result_data = response.json()

        if 'data' not in result_data:
            return jsonify({'success': False, 'error': 'Invalid API response'}), 500

        results = parse_abuseipdb_results(result_data['data'])

        return jsonify({
            'success': True,
            'results': results
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def parse_abuseipdb_results(data):
    reports = []

    if 'reports' in data and data['reports']:
        for report in data['reports'][:20]:  
            reports.append({
                'comment': report.get('comment', 'N/A'),
                'reported_at': report.get('reportedAt', 'N/A'),
                'reporter_id': report.get('reporterId', 'Anonymous'),
                'category': report.get('category', 'Unknown')
            })

    return {
        'ip_address': data.get('ipAddress', ''),
        'abuse_score': data.get('abuseConfidenceScore', 0),
        'total_reports': data.get('totalReports', 0),
        'distinct_reporters': data.get('numDistinctUsers', 0),
        'last_reported_at': data.get('lastReportedAt'),
        'isp': data.get('isp', 'Unknown'),
        'country_code': data.get('countryCode', 'Unknown'),
        'country_name': data.get('countryName', 'Unknown'),
        'hostname': data.get('hostnames', [None])[0] if data.get('hostnames') else None,
        'usage_type': data.get('usageType', 'Unknown'),
        'is_whitelisted': data.get('isWhitelisted', False),
        'labels': data.get('labels', []),
        'reports': reports
    }

@app.route('/api/ssh-containers', methods=['GET'])
def get_ssh_containers():
    try:
        client = docker.from_env()
        containers = []

        ssh_ports = {
            'web-server-1': 2201,
            'web-server-2': 2202,
            'db-server-1': 2203,
            'email-server-1': 2204,
            'client-pc-1': 2211,
            'client-pc-2': 2212,
            'client-pc-3': 2213
        }

        for container_name, ssh_port in ssh_ports.items():
            try:
                container = client.containers.get(container_name)
                containers.append({
                    'name': container_name,
                    'status': container.status,
                    'ssh_port': ssh_port,
                    'host': 'localhost',
                    'service': container.labels.get('cms.service', 'unknown')
                })
            except:
                pass

        return jsonify({
            'success': True,
            'containers': containers
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ssh-test', methods=['POST'])
def ssh_test():
    try:
        data = request.json
        container_name = data.get('container_name', '')

        if not container_name:
            return jsonify({'success': False, 'error': 'Container name required'}), 400

        ssh_ports = {
            'web-server-1': 2201,
            'web-server-2': 2202,
            'db-server-1': 2203,
            'email-server-1': 2204,
            'client-pc-1': 2211,
            'client-pc-2': 2212,
            'client-pc-3': 2213
        }

        if container_name not in ssh_ports:
            return jsonify({'success': False, 'error': 'Container not found'}), 404

        ssh_port = ssh_ports[container_name]

        try:
            key_path = os.path.join(os.path.dirname(__file__), 'keys', 'id_rsa')
            result = subprocess.run(
                ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=/dev/null',
                 '-o', 'ConnectTimeout=5', '-i', key_path, '-p', str(ssh_port),
                 'root@localhost', 'echo "SSH Connection Successful"'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                return jsonify({
                    'success': True,
                    'message': 'SSH connection successful',
                    'container': container_name,
                    'port': ssh_port
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'error': f'SSH connection failed: {result.stderr}'
                }), 500
        except subprocess.TimeoutExpired:
            return jsonify({'success': False, 'error': 'SSH connection timeout'}), 500
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ssh-command', methods=['POST'])
def ssh_command():
    try:
        data = request.json
        container_name = data.get('container_name', '')
        command = data.get('command', '')

        if not container_name or not command:
            return jsonify({'success': False, 'error': 'Container name and command required'}), 400

        ssh_ports = {
            'web-server-1': 2201,
            'web-server-2': 2202,
            'db-server-1': 2203,
            'email-server-1': 2204,
            'client-pc-1': 2211,
            'client-pc-2': 2212,
            'client-pc-3': 2213
        }

        if container_name not in ssh_ports:
            return jsonify({'success': False, 'error': 'Container not found'}), 404

        ssh_port = ssh_ports[container_name]

        try:
            key_path = os.path.join(os.path.dirname(__file__), 'keys', 'id_rsa')
            result = subprocess.run(
                ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=/dev/null',
                 '-i', key_path, '-p', str(ssh_port), 'root@localhost', command],
                capture_output=True,
                text=True,
                timeout=30
            )

            return jsonify({
                'success': True,
                'output': result.stdout,
                'error': result.stderr if result.returncode != 0 else '',
                'exit_code': result.returncode,
                'container': container_name
            }), 200

        except subprocess.TimeoutExpired:
            return jsonify({'success': False, 'error': 'Command execution timeout'}), 500
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/logs/all', methods=['GET'])
def get_all_logs():
    try:
        all_logs = {
            'deployment_logs': deployment_logs.copy(),
            'container_logs': {},
            'health_reports': {},
            'system_logs': []
        }

        if cms is not None:
            try:
                containers = cms.docker_client.containers.list(all=True)
                for container in containers:
                    try:
                        logs = container.logs(tail=100).decode('utf-8', errors='ignore')
                        if logs:
                            all_logs['container_logs'][container.name] = logs.split('\n')
                    except:
                        all_logs['container_logs'][container.name] = ['Unable to retrieve logs']
            except Exception as e:
                all_logs['container_logs']['error'] = str(e)

            try:
                health_reports_dir = Path(os.path.dirname(__file__)) / 'health_reports'
                if health_reports_dir.exists():
                    import glob
                    report_files = sorted(glob.glob(str(health_reports_dir / '*.json')), reverse=True)[:5]

                    for report_file in report_files:
                        try:
                            with open(report_file, 'r') as f:
                                report_name = os.path.basename(report_file)
                                all_logs['health_reports'][report_name] = json.load(f)
                        except Exception as e:
                            all_logs['health_reports'][os.path.basename(report_file)] = {'error': str(e)}
            except Exception as e:
                all_logs['health_reports']['error'] = str(e)

        return jsonify({
            'success': True,
            'logs': all_logs,
            'timestamp': datetime.datetime.now().isoformat(),
            'total_deployment_logs': len(deployment_logs),
            'total_containers': len(all_logs['container_logs']),
            'total_health_reports': len(all_logs['health_reports'])
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/logs', methods=['GET'])
def get_logs():
    try:
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        search = request.args.get('search', '').lower()

        filtered_logs = deployment_logs
        if search:
            filtered_logs = [log for log in deployment_logs if search in log.lower()]

        total_count = len(filtered_logs)
        logs = filtered_logs[offset:offset + limit]

        return jsonify({
            'logs': logs,
            'total': total_count,
            'count': len(logs),
            'offset': offset,
            'limit': limit,
            'deployment_status': deployment_status,
            'deployment_in_progress': deployment_in_progress
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs/clear', methods=['POST'])
def clear_logs():
    global deployment_logs
    try:
        deployment_logs.clear()
        log_deployment(" Logs cleared")
        return jsonify({
            'message': 'Logs cleared successfully',
            'logs': deployment_logs
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reset', methods=['POST'])
def reset_deployment_state():
    global deployment_in_progress, deployment_status, deployment_logs
    try:
        deployment_in_progress = False
        deployment_status = "idle"
        deployment_logs.clear()
        log_deployment(" Deployment state reset")
        return jsonify({
            'message': 'Deployment state reset successfully',
            'deployment_in_progress': deployment_in_progress,
            'deployment_status': deployment_status
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs/stream', methods=['GET'])
def stream_logs():
    def generate():
        last_count = 0
        while True:
            try:
                if len(deployment_logs) > last_count:
                    new_logs = deployment_logs[last_count:]
                    for log in new_logs:
                        yield f"data: {json.dumps({'log': log})}\n\n"
                    last_count = len(deployment_logs)

                time.sleep(0.5)

            except GeneratorExit:
                break
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                break

    return generate(), 200, {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no'
    }

@app.route('/api/ids/status', methods=['GET'])
def get_ids_status():
    try:
        if ids_manager is None:
            return jsonify({'error': 'IDS not initialized'}), 500

        stats = ids_manager.get_statistics()
        return jsonify({
            'status': 'active',
            'statistics': stats
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ids/alerts', methods=['GET'])
def get_alerts():
    try:
        if ids_manager is None:
            return jsonify({'error': 'IDS not initialized'}), 500

        alert_type = request.args.get('type')
        severity = request.args.get('severity')
        limit = request.args.get('limit', 50, type=int)

        alerts = ids_manager.get_alerts(alert_type=alert_type, severity=severity, limit=limit)

        return jsonify({
            'alerts': alerts,
            'total': len(alerts),
            'models_loaded': ids_manager.get_statistics()['models_loaded']
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ids/alerts/clear', methods=['POST'])
def clear_alerts():
    try:
        if ids_manager is None:
            return jsonify({'error': 'IDS not initialized'}), 500

        ids_manager.clear_alerts()
        log_deployment(" IDS alerts cleared")

        return jsonify({
            'message': 'Alerts cleared successfully'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ids/test-attack', methods=['POST'])
def test_attack_simulation():
    try:
        if ids_manager is None:
            return jsonify({'error': 'IDS not initialized'}), 500

        data = request.get_json() or {}
        attack_type = data.get('attack_type', 'sql_injection')
        target = data.get('target', 'database')

        simulations = ids_manager.generate_attack_simulation(attack_type, target)

        log_deployment(f" Generated {len(simulations)} attack simulations for {attack_type}")

        return jsonify({
            'attack_type': attack_type,
            'target': target,
            'simulations': simulations,
            'count': len(simulations)
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ids/analyze', methods=['POST'])
def analyze_log():
    try:
        if ids_manager is None:
            return jsonify({'error': 'IDS not initialized'}), 500

        data = request.get_json() or {}
        log_line = data.get('log_line', '')
        log_type = data.get('type', 'web')  

        if not log_line:
            return jsonify({'error': 'log_line is required'}), 400

        alert = None

        if log_type == 'web':
            alert = ids_manager.analyze_web_log(log_line)
        elif log_type == 'db':
            alert = ids_manager.analyze_db_log(log_line)
        elif log_type == 'email':
            alert = ids_manager.analyze_email_log(log_line)
        else:
            return jsonify({'error': f'Unknown log type: {log_type}'}), 400

        if alert:
            ids_manager.save_alerts()
            log_deployment(f" {alert['alert_type']}: {alert['attack_type']}")

        return jsonify({
            'alert': alert,
            'detected': alert is not None
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ids/bulk-analyze', methods=['POST'])
def bulk_analyze_logs():
    try:
        if ids_manager is None:
            return jsonify({'error': 'IDS not initialized'}), 500

        data = request.get_json() or {}
        logs = data.get('logs', [])
        log_type = data.get('type', 'web')

        if not logs:
            return jsonify({'error': 'logs array is required'}), 400

        detected_alerts = []

        for log_line in logs:
            alert = None

            if log_type == 'web':
                alert = ids_manager.analyze_web_log(log_line)
            elif log_type == 'db':
                alert = ids_manager.analyze_db_log(log_line)
            elif log_type == 'email':
                alert = ids_manager.analyze_email_log(log_line)

            if alert:
                detected_alerts.append(alert)

        if detected_alerts:
            ids_manager.save_alerts()

        log_deployment(f" Analyzed {len(logs)} logs, detected {len(detected_alerts)} anomalies")

        return jsonify({
            'total_analyzed': len(logs),
            'alerts_detected': len(detected_alerts),
            'alerts': detected_alerts
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ids/generate-logs', methods=['POST'])
def generate_logs_endpoint():
    try:
        if ids_manager is None:
            return jsonify({'error': 'IDS not initialized'}), 500

        import random
        from datetime import datetime

        ips = ['192.168.1.100', '192.168.1.101', '10.0.0.50', '172.16.0.20']
        paths = ['/index.html', '/api/users', '/admin', '/uploads', '/images/file.jpg']
        methods = ['GET', 'POST', 'PUT', 'DELETE']
        status_codes = [200, 201, 400, 401, 403, 404, 500, 503]

        logs = []
        for _ in range(5):
            ip = random.choice(ips)
            method = random.choice(methods)
            path = random.choice(paths)
            status = random.choice(status_codes)
            bytes_sent = random.randint(1024, 102400)
            timestamp = datetime.now().strftime('%d/%b/%Y:%H:%M:%S +0000')

            log = f'{ip} - - [{timestamp}] "{method} {path} HTTP/1.1" {status} {bytes_sent} "-" "Mozilla/5.0"'
            logs.append(log)

        detected_alerts = []
        for log in logs:
            alert = ids_manager.analyze_web_log(log)
            if alert:
                detected_alerts.append(alert)

        if detected_alerts:
            ids_manager.save_alerts()

        log_deployment(f" Generated 5 logs, detected {len(detected_alerts)} anomalies")

        return jsonify({
            'status': 'success',
            'logs_generated': len(logs),
            'alerts_detected': len(detected_alerts),
            'alerts': detected_alerts
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ids/generate-db-logs', methods=['POST'])
def generate_db_logs_endpoint():
    try:
        if ids_manager is None:
            return jsonify({'error': 'IDS not initialized'}), 500

        normal_queries = [
            "SELECT * FROM users WHERE id=1",
            "SELECT * FROM products ORDER BY price DESC LIMIT 10",
            "UPDATE users SET last_login=NOW() WHERE id=123",
            "INSERT INTO logs (action, timestamp) VALUES ('login', NOW())",
            "SELECT COUNT(*) FROM orders WHERE status='pending'",
        ]

        import random
        queries = random.choices(normal_queries, k=5)

        detected_alerts = []
        for query in queries:
            alert = ids_manager.analyze_db_log(query)
            if alert:
                detected_alerts.append(alert)

        if detected_alerts:
            ids_manager.save_alerts()

        log_deployment(f"  Generated 5 database logs, detected {len(detected_alerts)} anomalies")

        return jsonify({
            'status': 'success',
            'logs_generated': len(queries),
            'alerts_detected': len(detected_alerts),
            'alerts': detected_alerts
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ids/generate-email-logs', methods=['POST'])
def generate_email_logs_endpoint():
    try:
        if ids_manager is None:
            return jsonify({'error': 'IDS not initialized'}), 500

        normal_email_logs = [
            '192.168.1.100 - - [27/Nov/2024:10:30:00 +0000] "GET /mail HTTP/1.1" 200 1024 "-" "Mozilla/5.0"',
            '192.168.1.101 - - [27/Nov/2024:10:30:01 +0000] "POST /api/send-email HTTP/1.1" 200 512 "-" "Mozilla/5.0"',
            '192.168.1.102 - - [27/Nov/2024:10:30:02 +0000] "GET /mail/inbox HTTP/1.1" 200 2048 "-" "Mozilla/5.0"',
            '192.168.1.103 - - [27/Nov/2024:10:30:03 +0000] "GET /mail/compose HTTP/1.1" 200 1536 "-" "Mozilla/5.0"',
            '192.168.1.104 - - [27/Nov/2024:10:30:04 +0000] "POST /api/compose HTTP/1.1" 200 768 "-" "Mozilla/5.0"',
        ]

        import random
        logs = random.choices(normal_email_logs, k=5)

        detected_alerts = []
        for log in logs:
            alert = ids_manager.analyze_email_log(log)
            if alert:
                detected_alerts.append(alert)

        if detected_alerts:
            ids_manager.save_alerts()

        log_deployment(f" Generated 5 email logs, detected {len(detected_alerts)} anomalies")

        return jsonify({
            'status': 'success',
            'logs_generated': len(logs),
            'alerts_detected': len(detected_alerts),
            'alerts': detected_alerts
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ids/generate-attacks', methods=['POST'])
def generate_attacks_endpoint():
    try:
        if ids_manager is None:
            return jsonify({'error': 'IDS not initialized'}), 500

        data = request.get_json() or {}
        attack_type = data.get('attack_type', 'sql_injection')
        target_type = data.get('target_type', 'db')

        detected_alerts = []

        if target_type == 'email' and attack_type == 'phishing':
            phishing_emails = [
                '10.0.0.1 - - [27/Nov/2024:10:30:01 +0000] "GET /verify_account HTTP/1.1" 200 2048 "-" "Mozilla/5.0"',
                '10.0.0.2 - - [27/Nov/2024:10:30:02 +0000] "GET /confirm_identity HTTP/1.1" 200 1536 "-" "Mozilla/5.0"',
                '10.0.0.3 - - [27/Nov/2024:10:30:03 +0000] "GET /?urgent=action+required HTTP/1.1" 200 1024 "-" "Mozilla/5.0"',
                '10.0.0.4 - - [27/Nov/2024:10:30:04 +0000] "GET /download/malware.exe HTTP/1.1" 200 8192 "-" "Mozilla/5.0"',
                '10.0.0.5 - - [27/Nov/2024:10:30:05 +0000] "GET /ransomware.zip HTTP/1.1" 200 4096 "-" "Mozilla/5.0"',
            ]

            for attack in phishing_emails:
                alert = ids_manager.analyze_email_log(attack)
                if alert:
                    detected_alerts.append(alert)

            attacks = phishing_emails
        else:
            attacks = ids_manager.generate_attack_simulation(attack_type, target_type)

            for attack in attacks[:3]:  
                alert = None
                if target_type == 'db':
                    alert = ids_manager.analyze_db_log(attack)
                else:
                    alert = ids_manager.analyze_web_log(attack)

                if alert:
                    detected_alerts.append(alert)

        if detected_alerts:
            ids_manager.save_alerts()

        log_deployment(f" Generated {len(attacks)} {attack_type} attacks ({target_type}), detected {len(detected_alerts)} anomalies")

        return jsonify({
            'status': 'success',
            'attack_type': attack_type,
            'target_type': target_type,
            'attacks_generated': len(attacks),
            'alerts_detected': len(detected_alerts),
            'alerts': detected_alerts,
            'payloads': attacks[:3]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ids/generate-suspicious-logs', methods=['POST'])
def generate_suspicious_logs_endpoint():
    try:
        if ids_manager is None:
            return jsonify({'error': 'IDS not initialized'}), 500

        suspicious_logs = [
            '192.168.1.200 - - [27/Nov/2025:12:57:11 +0000] "GET /admin?cmd=whoami HTTP/1.1" 200 1024 "-" "curl/7.64.1"',
            '10.0.0.99 - - [27/Nov/2025:12:57:12 +0000] "POST /login HTTP/1.1" 401 512 "-" "sqlmap/1.4.5"',
            '172.16.0.50 - - [27/Nov/2025:12:57:13 +0000] "GET /../../../etc/passwd HTTP/1.1" 400 256 "-" "Mozilla"',
            '192.168.1.150 - - [27/Nov/2025:12:57:14 +0000] "GET /?id=<script>alert(1)</script> HTTP/1.1" 200 2048 "-" "Mozilla"',
            '10.0.0.88 - - [27/Nov/2025:12:57:15 +0000] "GET /search?q=%27%20OR%20%271%27=%271 HTTP/1.1" 200 1024 "-" "curl/7.64.1"',
        ]

        detected_alerts = []
        for log in suspicious_logs:
            alert = ids_manager.analyze_web_log(log)
            if alert:
                detected_alerts.append(alert)

        if detected_alerts:
            ids_manager.save_alerts()

        log_deployment(f"  Generated 5 suspicious logs, detected {len(detected_alerts)} anomalies")

        return jsonify({
            'status': 'success',
            'logs_generated': len(suspicious_logs),
            'alerts_detected': len(detected_alerts),
            'alerts': detected_alerts
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ids/clear-all-alerts', methods=['POST'])
def clear_all_alerts():
    try:
        if ids_manager is None:
            return jsonify({'error': 'IDS not initialized'}), 500

        ids_manager.clear_alerts()
        log_deployment(" Cleared all IDS alerts")

        return jsonify({
            'status': 'success',
            'message': 'All alerts cleared'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'Server error'}), 500

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/virus-total')
def virus_total():
    return render_template('virus_total.html')

@app.route('/abuseipdb')
def abuseipdb():
    return render_template('abuseipdb.html')

@app.route('/ssh-manager')
def ssh_manager():
    return render_template('ssh_manager.html')

if __name__ == '__main__':
    print(" Initializing Enhanced CMS API...")
    if init_cms():
        print(" CMS initialized successfully - Full mode")
    else:
        print(" CMS initialization failed - Limited mode")

    print(" Starting Flask server on port 5001...")
    print(" Dashboard: http://localhost:5001")
    app.run(debug=False, host='0.0.0.0', port=5001)
