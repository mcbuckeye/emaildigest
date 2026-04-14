#!/bin/bash
# EmailDigest Deployment Script for Dokploy
# This script helps deploy and verify EmailDigest on Dokploy

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
REPO="mcbuckeye/emaildigest"
BRANCH="main"
DOMAIN="emaildigest.machomelab.com"

# Dokploy CLI commands (adjust based on your Dokploy setup)
DOKPLOY_API_URL="${DOKPLOY_API_URL:-http://localhost:3000}"
DOKPLOY_TOKEN="${DOKPLOY_TOKEN:-}"

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    
    if ! command -v git &> /dev/null; then
        log_error "Git is not installed"
        exit 1
    fi
    
    log_info "✓ All prerequisites met"
}

# Build and deploy to local Docker
deploy_locally() {
    log_info "Building and deploying locally..."
    
    docker-compose up -d --build
    
    log_info "Waiting for services to start..."
    sleep 10
    
    # Check backend health
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        log_info "✓ Backend is running"
    else
        log_error "Backend is not responding"
        exit 1
    fi
    
    # Check frontend health
    if curl -sf http://localhost:3000 > /dev/null 2>&1; then
        log_info "✓ Frontend is running"
    else
        log_warn "Frontend is not responding"
    fi
    
    # Check database
    if curl -sf http://localhost:8000/health/db > /dev/null 2>&1; then
        log_info "✓ Database is connected"
    else
        log_error "Database connection failed"
        exit 1
    fi
}

# Deploy to Dokploy (requires Dokploy CLI or API access)
deploy_to_dokploy() {
    log_info "Deploying to Dokploy..."
    
    # This is a placeholder - adjust based on your Dokploy setup
    # Option 1: Using Dokploy CLI
    # dokploy deploy --repo $REPO --branch $BRANCH --domain $DOMAIN
    
    # Option 2: Using Dokploy API
    # curl -X POST "$DOKPLOY_API_URL/api/deployments" \
    #   -H "Authorization: Bearer $DOKPLOY_TOKEN" \
    #   -H "Content-Type: application/json" \
    #   -d '{"repo": "'"$REPO"'", "branch": "'"$BRANCH"'", "domain": "'"$DOMAIN"'"}'
    
    log_info "Please deploy using your Dokploy dashboard or CLI:"
    log_info "  - Repository: $REPO"
    log_info "  - Branch: $BRANCH"
    log_info "  - Domain: $DOMAIN"
}

# Setup Cloudflare DNS and Workers
setup_cloudflare() {
    log_info "Setting up Cloudflare configuration..."
    
    log_info "You'll need to configure the following in Cloudflare:"
    log_info ""
    log_info "1. DNS Configuration:"
    log_info "   - Add CNAME record:"
    log_info "     Host: emaildigest"
    log_info "     Target: <your-dokploy-domain>"
    log_info "     Proxy status: Proxied (orange cloud)"
    log_info ""
    log_info "2. Worker Configuration (optional):"
    log_info "   - Upload cloudflare-workers/index.js as a Worker"
    log_info "   - Bind variables: BACKEND_URL, FRONTEND_URL"
    log_info ""
    log_info "3. SSL Configuration:"
    log_info "   - Enable SSL in Cloudflare"
    log_info "   - Set SSL mode to Full or Full (Strict)"
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."
    
    # Check all endpoints
    local checks=(
        "http://localhost:8000/health:Backend health"
        "http://localhost:8000/health/db:Database health"
        "http://localhost:3000:Frontend"
    )
    
    local all_passed=true
    
    for check in "${checks[@]}"; do
        local url="${check%%:*}"
        local name="${check##*:}"
        
        if curl -sf "$url" > /dev/null 2>&1; then
            log_info "✓ $name"
        else
            log_warn "✗ $name"
            all_passed=false
        fi
    done
    
    if [ "$all_passed" = true ]; then
        log_info ""
        log_info "========================================"
        log_info "Deployment successful!"
        log_info "========================================"
        log_info ""
        log_info "Backend API:  http://localhost:8000"
        log_info "Frontend:     http://localhost:3000"
        log_info "Health API:   http://localhost:8000/health"
        log_info "DB Health:    http://localhost:8000/health/db"
        log_info ""
        log_info "To access the application:"
        log_info "  1. Open http://localhost:3000 in your browser"
        log_info "  2. Sign up for a new account"
        log_info "  3. Create your first digest!"
        log_info ""
    else
        log_error "Some checks failed. Review the errors above."
        exit 1
    fi
}

# Show usage
show_usage() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  local     Deploy locally with Docker Compose"
    echo "  dokploy   Deploy to Dokploy cloud"
    echo "  cloudflare Setup Cloudflare configuration"
    echo "  verify    Verify all services are running"
    echo "  all       Deploy everything (local + verify)"
    echo ""
}

# Main execution
case "${1:-all}" in
    local)
        check_prerequisites
        deploy_locally
        verify_deployment
        ;;
    dokploy)
        check_prerequisites
        deploy_to_dokploy
        ;;
    cloudflare)
        setup_cloudflare
        ;;
    verify)
        verify_deployment
        ;;
    all)
        check_prerequisites
        deploy_locally
        verify_deployment
        setup_cloudflare
        ;;
    *)
        show_usage
        exit 1
        ;;
esac
