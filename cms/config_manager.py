#!/usr/bin/env python3
"""
Configuration Manager for Infrastructure as Code
Handles configuration versioning, validation, and change detection
"""

import yaml
import json
import hashlib
import os
import time
from datetime import datetime
from pathlib import Path

class ConfigManager:
    def __init__(self, config_path=None):
        if config_path is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(script_dir, "config.yaml")
        
        self.config_path = config_path
        self.versions_dir = os.path.join(os.path.dirname(config_path), "config_versions")
        self.current_config = None
        self.config_hash = None
        
        # Create versions directory if it doesn't exist
        Path(self.versions_dir).mkdir(parents=True, exist_ok=True)
        
        # Load initial configuration
        self.load_config()
    
    def load_config(self):
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as file:
                self.current_config = yaml.safe_load(file)
            
            # Calculate hash for change detection
            config_str = json.dumps(self.current_config, sort_keys=True)
            self.config_hash = hashlib.sha256(config_str.encode()).hexdigest()
            
            print(f"✅ Configuration loaded from {self.config_path}")
            return self.current_config
        except FileNotFoundError:
            print(f"❌ Config file not found: {self.config_path}")
            raise
        except yaml.YAMLError as e:
            print(f"❌ Error parsing YAML: {e}")
            raise
    
    def save_config(self, config_dict):
        """Save configuration to file"""
        try:
            with open(self.config_path, 'w') as file:
                yaml.dump(config_dict, file, default_flow_style=False)
            
            print(f"✅ Configuration saved to {self.config_path}")
            self.load_config()  # Reload to update hash
            return True
        except Exception as e:
            print(f"❌ Error saving config: {e}")
            return False
    
    def validate_config(self, config_dict=None):
        """Validate configuration schema"""
        config = config_dict or self.current_config
        
        required_sections = ['infrastructure', 'networks']
        errors = []
        
        # Check required sections
        for section in required_sections:
            if section not in config:
                errors.append(f"Missing required section: {section}")
        
        # Validate infrastructure
        if 'infrastructure' in config:
            infra = config['infrastructure']
            required_services = ['web_servers', 'db_servers', 'email_servers', 'client_pcs']
            for service in required_services:
                if service not in infra:
                    errors.append(f"Missing service: {service}")
                elif not isinstance(infra[service], dict):
                    errors.append(f"Invalid {service} configuration")
                elif 'count' not in infra[service]:
                    errors.append(f"Missing count for {service}")
                elif 'image' not in infra[service]:
                    errors.append(f"Missing image for {service}")
        
        # Validate networks
        if 'networks' in config:
            for net_name, net_config in config['networks'].items():
                if 'subnet' not in net_config:
                    errors.append(f"Missing subnet for network {net_name}")
        
        if errors:
            print("❌ Configuration validation failed:")
            for error in errors:
                print(f"  - {error}")
            return False
        
        print("✅ Configuration validation passed")
        return True
    
    def has_changed(self):
        """Check if configuration has changed since last load"""
        try:
            with open(self.config_path, 'r') as file:
                config = yaml.safe_load(file)
            
            config_str = json.dumps(config, sort_keys=True)
            new_hash = hashlib.sha256(config_str.encode()).hexdigest()
            
            if new_hash != self.config_hash:
                print(f"⚠️  Configuration has changed (hash: {self.config_hash[:8]} -> {new_hash[:8]})")
                return True
            return False
        except Exception as e:
            print(f"❌ Error checking config changes: {e}")
            return False
    
    def create_version(self, description=""):
        """Create a versioned copy of current configuration"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        version_id = f"v_{timestamp}"
        
        version_file = os.path.join(self.versions_dir, f"{version_id}.json")
        version_info = {
            'version_id': version_id,
            'timestamp': datetime.now().isoformat(),
            'description': description,
            'config_hash': self.config_hash,
            'config': self.current_config
        }
        
        try:
            with open(version_file, 'w') as f:
                json.dump(version_info, f, indent=2)
            
            print(f"✅ Configuration version created: {version_id}")
            return version_id
        except Exception as e:
            print(f"❌ Error creating version: {e}")
            return None
    
    def list_versions(self):
        """List all configuration versions"""
        versions = []
        try:
            for filename in sorted(os.listdir(self.versions_dir), reverse=True):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.versions_dir, filename)
                    with open(filepath, 'r') as f:
                        version_info = json.load(f)
                    versions.append(version_info)
        except Exception as e:
            print(f"❌ Error listing versions: {e}")
        
        return versions
    
    def get_version(self, version_id):
        """Get a specific configuration version"""
        version_file = os.path.join(self.versions_dir, f"{version_id}.json")
        
        try:
            with open(version_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"❌ Version not found: {version_id}")
            return None
        except Exception as e:
            print(f"❌ Error loading version: {e}")
            return None
    
    def rollback_to_version(self, version_id):
        """Rollback configuration to a specific version"""
        version_info = self.get_version(version_id)
        if not version_info:
            return False
        
        config = version_info.get('config')
        if not config:
            print(f"❌ No configuration found in version {version_id}")
            return False
        
        # Validate before rollback
        if not self.validate_config(config):
            print(f"❌ Cannot rollback: configuration validation failed")
            return False
        
        # Save current as backup
        backup_id = self.create_version(f"Backup before rollback to {version_id}")
        
        # Restore configuration
        if self.save_config(config):
            print(f"✅ Configuration rolled back to {version_id}")
            return True
        
        return False
    
    def get_infrastructure_config(self, service_type):
        """Get configuration for a specific service type"""
        if not self.current_config or 'infrastructure' not in self.current_config:
            return None
        
        return self.current_config['infrastructure'].get(service_type)
    
    def get_network_config(self, network_name):
        """Get configuration for a specific network"""
        if not self.current_config or 'networks' not in self.current_config:
            return None
        
        return self.current_config['networks'].get(network_name)
    
    def get_service_count(self, service_type):
        """Get the configured count for a service"""
        service_config = self.get_infrastructure_config(service_type)
        return service_config.get('count', 1) if service_config else 1
    
    def get_service_image(self, service_type):
        """Get the configured image for a service"""
        service_config = self.get_infrastructure_config(service_type)
        return service_config.get('image', '') if service_config else ''
    
    def get_firewall_rules(self, service_type):
        """Get firewall rules for a service"""
        service_config = self.get_infrastructure_config(service_type)
        if service_config and 'security' in service_config:
            return service_config['security'].get('firewall_rules', [])
        return []
    
    def export_config(self, format='yaml'):
        """Export current configuration"""
        try:
            if format == 'json':
                return json.dumps(self.current_config, indent=2)
            else:  # yaml
                return yaml.dump(self.current_config, default_flow_style=False)
        except Exception as e:
            print(f"❌ Error exporting config: {e}")
            return None
    
    def update_service_config(self, service_type, updates):
        """Update specific service configuration"""
        if 'infrastructure' not in self.current_config:
            self.current_config['infrastructure'] = {}
        
        if service_type not in self.current_config['infrastructure']:
            self.current_config['infrastructure'][service_type] = {}
        
        # Merge updates
        self.current_config['infrastructure'][service_type].update(updates)
        
        # Validate
        if self.validate_config():
            print(f"✅ Updated {service_type} configuration")
            return True
        else:
            print(f"❌ Configuration update validation failed")
            return False
    
    def get_all_config_diffs(self, version_id1, version_id2):
        """Get differences between two configuration versions"""
        v1 = self.get_version(version_id1)
        v2 = self.get_version(version_id2)
        
        if not v1 or not v2:
            print("❌ One or both versions not found")
            return None
        
        config1 = v1.get('config', {})
        config2 = v2.get('config', {})
        
        return {
            'version1': version_id1,
            'version2': version_id2,
            'config1': config1,
            'config2': config2,
            'timestamp1': v1.get('timestamp'),
            'timestamp2': v2.get('timestamp')
        }

if __name__ == "__main__":
    # Test the config manager
    cm = ConfigManager()
    
    print("\n📊 Configuration Summary:")
    print(f"Web Servers: {cm.get_service_count('web_servers')} x {cm.get_service_image('web_servers')}")
    print(f"DB Servers: {cm.get_service_count('db_servers')} x {cm.get_service_image('db_servers')}")
    print(f"Email Servers: {cm.get_service_count('email_servers')} x {cm.get_service_image('email_servers')}")
    print(f"Client PCs: {cm.get_service_count('client_pcs')} x {cm.get_service_image('client_pcs')}")
    
    print("\n📋 Firewall Rules:")
    for service in ['web_servers', 'db_servers', 'email_servers', 'client_pcs']:
        rules = cm.get_firewall_rules(service)
        if rules:
            print(f"\n{service}:")
            for rule in rules:
                print(f"  - {rule}")
    
    print("\n✅ Configuration manager ready!")
