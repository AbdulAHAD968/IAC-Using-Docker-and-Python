#!/bin/bash

echo "🧹 Cleaning up existing containers and networks..."

# Stop and remove all project containers
docker ps -a --filter "name=web-server-" --format "{{.Names}}" | xargs -r docker rm -f
docker ps -a --filter "name=db-server-" --format "{{.Names}}" | xargs -r docker rm -f
docker ps -a --filter "name=email-server-" --format "{{.Names}}" | xargs -r docker rm -f
docker ps -a --filter "name=client-pc-" --format "{{.Names}}" | xargs -r docker rm -f

# Remove project networks
docker network ls --filter "name=frontend_net" --format "{{.Name}}" | xargs -r docker network rm
docker network ls --filter "name=backend_net" --format "{{.Name}}" | xargs -r docker network rm
docker network ls --filter "name=management_net" --format "{{.Name}}" | xargs -r docker network rm

echo "✅ Cleanup completed!"