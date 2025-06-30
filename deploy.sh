#!/bin/bash

# AI SEC Filing Analyzer - Deployment Script
# This script simplifies the deployment process for both development and production

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker Desktop or Docker Engine."
        exit 1
    fi
    print_success "Docker is running"
}

# Function to check if required environment variables are set
check_env_vars() {
    if [ -z "$GOOGLE_API_KEY" ]; then
        print_error "GOOGLE_API_KEY environment variable is not set."
        print_status "Please set it with: export GOOGLE_API_KEY='your-api-key'"
        print_status "Or create a .env file from env.example"
        exit 1
    fi
    print_success "Environment variables are configured"
}

# Function to build and start development environment
start_dev() {
    print_status "Starting development environment..."
    check_docker
    check_env_vars
    
    # Create logs directory if it doesn't exist
    mkdir -p logs
    
    # Start development environment
    docker-compose up --build -d
    
    print_success "Development environment started!"
    print_status "Frontend: http://localhost:3000"
    print_status "Backend API: http://localhost:8000"
    print_status "API Docs: http://localhost:8000/docs"
    print_status "View logs: docker-compose logs -f"
}

# Function to start production environment
start_prod() {
    print_status "Starting production environment..."
    check_docker
    check_env_vars
    
    # Check if ALLOWED_ORIGINS is set for production
    if [ -z "$ALLOWED_ORIGINS" ]; then
        print_warning "ALLOWED_ORIGINS not set. Using default localhost origins."
        export ALLOWED_ORIGINS="http://localhost:3000,http://127.0.0.1:3000"
    fi
    
    # Create logs directory if it doesn't exist
    mkdir -p logs
    
    # Start production environment
    docker-compose -f docker-compose.prod.yml up --build -d
    
    print_success "Production environment started!"
    print_status "Application: http://localhost (with Nginx)"
    print_status "Direct API: http://localhost:8000"
    print_status "View logs: docker-compose -f docker-compose.prod.yml logs -f"
}

# Function to stop development environment
stop_dev() {
    print_status "Stopping development environment..."
    docker-compose down
    print_success "Development environment stopped"
}

# Function to stop production environment
stop_prod() {
    print_status "Stopping production environment..."
    docker-compose -f docker-compose.prod.yml down
    print_success "Production environment stopped"
}

# Function to show status
show_status() {
    print_status "Development containers:"
    docker-compose ps
    
    echo ""
    print_status "Production containers:"
    docker-compose -f docker-compose.prod.yml ps
}

# Function to show logs
show_logs() {
    if [ "$1" = "prod" ]; then
        docker-compose -f docker-compose.prod.yml logs -f
    else
        docker-compose logs -f
    fi
}

# Function to clean up
cleanup() {
    print_status "Cleaning up Docker resources..."
    docker-compose down -v 2>/dev/null || true
    docker-compose -f docker-compose.prod.yml down -v 2>/dev/null || true
    docker system prune -f
    print_success "Cleanup completed"
}

# Function to show help
show_help() {
    echo "AI SEC Filing Analyzer - Deployment Script"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  dev     Start development environment"
    echo "  prod    Start production environment"
    echo "  stop    Stop development environment"
    echo "  stop-prod Stop production environment"
    echo "  status  Show container status"
    echo "  logs    Show development logs"
    echo "  logs-prod Show production logs"
    echo "  cleanup Clean up Docker resources"
    echo "  help    Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  GOOGLE_API_KEY    Required: Your Google AI Studio API key"
    echo "  ALLOWED_ORIGINS   Optional: CORS allowed origins (for production)"
    echo ""
    echo "Examples:"
    echo "  export GOOGLE_API_KEY='your-api-key'"
    echo "  $0 dev"
    echo "  $0 prod"
}

# Main script logic
case "${1:-help}" in
    "dev")
        start_dev
        ;;
    "prod")
        start_prod
        ;;
    "stop")
        stop_dev
        ;;
    "stop-prod")
        stop_prod
        ;;
    "status")
        show_status
        ;;
    "logs")
        show_logs "dev"
        ;;
    "logs-prod")
        show_logs "prod"
        ;;
    "cleanup")
        cleanup
        ;;
    "help"|*)
        show_help
        ;;
esac 