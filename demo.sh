#!/bin/bash

# AI SEC Filing Analyzer - Interview Demo Script
# Quick and lightweight deployment for interviews

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker Desktop or Docker Engine."
    exit 1
fi

# Load .env file from backend folder if it exists
if [ -f "backend/.env" ]; then
    print_status "Loading environment from backend/.env"
    export $(grep -v '^#' backend/.env | xargs)
fi

# Check for API key
if [ -z "$GOOGLE_API_KEY" ]; then
    print_error "GOOGLE_API_KEY not found in environment or backend/.env"
    print_status "Please create backend/.env file with: GOOGLE_API_KEY=your-api-key"
    print_status "Get a free API key at: https://aistudio.google.com/"
    exit 1
fi

print_status "API key found and loaded successfully"

print_status "Starting AI SEC Filing Analyzer Demo..."

# Clean up any existing containers and images to prevent disk bloat
print_status "Cleaning up existing containers and images..."
docker-compose -f docker-compose.demo.yml down --volumes --remove-orphans 2>/dev/null || true
docker system prune -f 2>/dev/null || true

# Build and start the demo
print_status "Building and starting containers..."
docker-compose -f docker-compose.demo.yml up --build -d

# Wait for services to be ready
print_status "Waiting for services to start..."
sleep 15

# Check if services are running
if docker-compose -f docker-compose.demo.yml ps | grep -q "Up"; then
    print_status "✅ Demo is ready!"
    echo ""
    echo "🌐 Access the application:"
    echo "   Frontend: http://localhost"
    echo "   Backend API: http://localhost:8000"
    echo "   API Docs: http://localhost:8000/docs"
    echo ""
    echo "🔧 To stop the demo:"
    echo "   docker-compose -f docker-compose.demo.yml down"
    echo ""
    echo "📊 To view logs:"
    echo "   docker-compose -f docker-compose.demo.yml logs -f"
    echo ""
    echo "🧹 To clean up disk space:"
    echo "   docker system prune -af --volumes"
else
    print_error "Failed to start services. Check logs with:"
    echo "docker-compose -f docker-compose.demo.yml logs"
    exit 1
fi 