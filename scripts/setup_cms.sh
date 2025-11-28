#!/bin/bash

echo "Setting up Secure IaC CMS..."


# Install Docker
sudo apt-get install -y docker.io docker-compose
sudo systemctl enable docker
sudo systemctl start docker

# Add current user to docker group
sudo usermod -aG docker $USER
unset DOCKER_HOST

# Install Python and required packages
sudo apt-get install -y python3 python3-pip
pip3 install docker pyyaml requests


echo "CMS setup completed. Please log out and log back in for group changes to take effect."