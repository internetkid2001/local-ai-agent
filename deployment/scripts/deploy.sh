#!/bin/bash

# Local AI Agent Deployment Script
# Usage: ./deploy.sh [local|staging|production]

set -euo pipefail

ENVIRONMENT=${1:-local}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

check_dependencies() {
    log "Checking dependencies..."
    
    if [ "$ENVIRONMENT" = "local" ]; then
        command -v docker >/dev/null 2>&1 || error "Docker is required for local deployment"
        command -v docker-compose >/dev/null 2>&1 || error "Docker Compose is required for local deployment"
    else
        command -v kubectl >/dev/null 2>&1 || error "kubectl is required for $ENVIRONMENT deployment"
        command -v helm >/dev/null 2>&1 || warn "Helm is recommended for $ENVIRONMENT deployment"
    fi
    
    log "Dependencies check passed"
}

deploy_local() {
    log "Deploying to local environment..."
    
    cd "$PROJECT_DIR/deployment/compose"
    
    # Check if .env exists
    if [ ! -f ".env" ]; then
        log "Creating .env file from example..."
        cp .env.example .env
        warn "Please review and update .env file with your configuration"
    fi
    
    # Build and start services
    docker-compose down -v 2>/dev/null || true
    docker-compose build
    docker-compose up -d
    
    # Wait for services to be ready
    log "Waiting for services to be ready..."
    sleep 30
    
    # Health checks
    check_health_local
    
    log "Local deployment completed successfully!"
    info "Access the application at: http://localhost:8000"
    info "API Documentation: http://localhost:8000/docs"
    info "Grafana Dashboard: http://localhost:3000 (admin/admin123)"
    info "Prometheus: http://localhost:9090"
}

deploy_staging() {
    log "Deploying to staging environment..."
    
    cd "$PROJECT_DIR"
    
    # Verify kubectl context
    kubectl config current-context || error "kubectl context not set"
    
    # Apply Kubernetes manifests
    kubectl apply -f deployment/kubernetes/namespace.yaml
    kubectl apply -f deployment/kubernetes/configmap.yaml
    kubectl apply -f deployment/kubernetes/secrets.yaml
    kubectl apply -f deployment/kubernetes/redis.yaml
    kubectl apply -f deployment/kubernetes/postgres.yaml
    kubectl apply -f deployment/kubernetes/api-gateway.yaml
    kubectl apply -f deployment/kubernetes/ingress.yaml
    
    # Wait for deployments
    log "Waiting for deployments to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/ai-agent-api -n local-ai-agent
    kubectl wait --for=condition=available --timeout=300s deployment/redis -n local-ai-agent
    kubectl wait --for=condition=available --timeout=300s deployment/postgres -n local-ai-agent
    
    # Health checks
    check_health_k8s
    
    log "Staging deployment completed successfully!"
}

deploy_production() {
    log "Deploying to production environment..."
    
    cd "$PROJECT_DIR"
    
    # Additional safety checks for production
    if [ -z "${PRODUCTION_CONFIRMED:-}" ]; then
        read -p "Are you sure you want to deploy to PRODUCTION? (yes/no): " confirm
        if [ "$confirm" != "yes" ]; then
            error "Production deployment cancelled"
        fi
    fi
    
    # Verify kubectl context
    kubectl config current-context || error "kubectl context not set"
    
    # Apply Kubernetes manifests with monitoring
    kubectl apply -f deployment/kubernetes/namespace.yaml
    kubectl apply -f deployment/kubernetes/configmap.yaml
    kubectl apply -f deployment/kubernetes/secrets.yaml
    kubectl apply -f deployment/kubernetes/redis.yaml
    kubectl apply -f deployment/kubernetes/postgres.yaml
    kubectl apply -f deployment/kubernetes/api-gateway.yaml
    kubectl apply -f deployment/kubernetes/ingress.yaml
    kubectl apply -f deployment/kubernetes/monitoring.yaml
    
    # Rolling update
    kubectl rollout restart deployment/ai-agent-api -n local-ai-agent
    kubectl rollout status deployment/ai-agent-api -n local-ai-agent --timeout=600s
    
    # Health checks
    check_health_k8s
    
    log "Production deployment completed successfully!"
}

check_health_local() {
    log "Running health checks..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost:8000/health >/dev/null 2>&1; then
            log "Health check passed"
            return 0
        fi
        
        info "Health check attempt $attempt/$max_attempts failed, retrying in 10s..."
        sleep 10
        ((attempt++))
    done
    
    error "Health check failed after $max_attempts attempts"
}

check_health_k8s() {
    log "Running Kubernetes health checks..."
    
    # Check pod status
    kubectl get pods -n local-ai-agent
    
    # Check if all pods are running
    local pending_pods
    pending_pods=$(kubectl get pods -n local-ai-agent --field-selector=status.phase!=Running --no-headers 2>/dev/null | wc -l)
    
    if [ "$pending_pods" -gt 0 ]; then
        warn "Some pods are not in Running state"
        kubectl get pods -n local-ai-agent --field-selector=status.phase!=Running
    else
        log "All pods are running"
    fi
    
    # Check services
    kubectl get services -n local-ai-agent
}

cleanup() {
    log "Cleaning up..."
    
    if [ "$ENVIRONMENT" = "local" ]; then
        cd "$PROJECT_DIR/deployment/compose"
        docker-compose down -v
        docker system prune -f
    fi
}

show_logs() {
    if [ "$ENVIRONMENT" = "local" ]; then
        cd "$PROJECT_DIR/deployment/compose"
        docker-compose logs -f
    else
        kubectl logs -f deployment/ai-agent-api -n local-ai-agent
    fi
}

main() {
    log "Starting deployment for environment: $ENVIRONMENT"
    
    check_dependencies
    
    case "$ENVIRONMENT" in
        local)
            deploy_local
            ;;
        staging)
            deploy_staging
            ;;
        production)
            deploy_production
            ;;
        *)
            error "Invalid environment: $ENVIRONMENT. Use: local|staging|production"
            ;;
    esac
    
    log "Deployment completed successfully!"
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [local|staging|production] [options]"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --logs         Show application logs after deployment"
        echo "  --cleanup      Cleanup deployment"
        echo ""
        echo "Examples:"
        echo "  $0 local              # Deploy locally with Docker Compose"
        echo "  $0 staging            # Deploy to staging Kubernetes cluster"
        echo "  $0 production         # Deploy to production Kubernetes cluster"
        echo "  $0 local --logs       # Deploy locally and show logs"
        echo "  $0 local --cleanup    # Cleanup local deployment"
        exit 0
        ;;
    --logs)
        show_logs
        exit 0
        ;;
    --cleanup)
        cleanup
        exit 0
        ;;
esac

# Run main deployment
main

# Show logs if requested
if [[ "${2:-}" == "--logs" ]]; then
    show_logs
fi