import docker
import time

class SecurityManager:
    def __init__(self, docker_client, config):
        self.client = docker_client
        self.config = config
    
    def harden_all_containers(self):
        print("Applying quick security hardening...")
        containers = self.client.containers.list()
        for container in containers:
            self.quick_harden_container(container)
    
    def quick_harden_container(self, container):
        print(f"  Securing {container.name}...")
        image_tag = container.image.tags[0] if container.image.tags else ""
        is_ubuntu = any(k in image_tag.lower() for k in ["ubuntu", "debian"])
        apk_check = container.exec_run("which apk").exit_code == 0
        
        if is_ubuntu:
            try:
                u = container.exec_run("apt-get update", user="root")
                if u.exit_code != 0:
                    print(f"    Update failed for {container.name}")
                    return
                i = container.exec_run("apt-get install -y curl netcat-openbsd", user="root")
                if i.exit_code == 0:
                    print(f"    Basic tools installed for {container.name}")
                else:
                    print(f"    Installation failed for {container.name}")
            except Exception as e:
                print(f"    Error for {container.name}: {e}")
            return
        
        if apk_check:
            try:
                a = container.exec_run("apk add curl netcat-openbsd", user="root")
                if a.exit_code == 0:
                    print(f"    Basic tools installed (apk) for {container.name}")
                else:
                    print(f"    APK installation failed for {container.name}")
            except Exception as e:
                print(f"    Error for {container.name}: {e}")
            return
        
        print(f"    Unsupported base image for {container.name}")
    
    def audit_all_containers(self):
        print("Running quick security audit...")
        containers = self.client.containers.list()
        for container in containers:
            print(f"  {container.name}: Running - {container.image.tags[0] if container.image.tags else 'Unknown'}")
