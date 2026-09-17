#!/bin/bash

# AgriPredictX Deployment Script
# Usage: ./deploy.sh [dev|prod|stop|restart]

set -e

PROJECT_NAME="crop-prediction-system"
COMPOSE_FILE="docker-compose.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
}

# Create necessary directories
create_directories() {
    log_info "Creating necessary directories..."
    mkdir -p models
    mkdir -p data
    mkdir -p logs
    log_success "Directories created"
}

# Build the application
build_app() {
    log_info "Building Docker images..."
    docker-compose -f $COMPOSE_FILE build --no-cache
    log_success "Docker images built"
}

# Start the application
start_app() {
    local profile=""
    if [ "$1" = "prod" ]; then
        profile="--profile production"
    fi

    log_info "Starting $PROJECT_NAME..."
    docker-compose -f $COMPOSE_FILE $profile up -d
    log_success "$PROJECT_NAME started"

    # Wait for health check
    log_info "Waiting for application to be healthy..."
    sleep 10

    # Check health
    if curl -f http://localhost:5000/health &> /dev/null; then
        log_success "Application is healthy!"
        echo ""
        echo "🌾 AgriPredictX is running!"
        echo "📡 API: http://localhost:5000"
        if [ "$1" = "prod" ]; then
            echo "🌐 Web: http://localhost"
        fi
        echo ""
        echo "📚 API Documentation:"
        echo "  GET  /health          - Health check"
        echo "  POST /predict         - Single prediction"
        echo "  POST /predict-batch   - Batch predictions"
        echo "  GET  /model-info      - Model information"
    else
        log_error "Application failed health check"
        show_logs
        exit 1
    fi
}

# Stop the application
stop_app() {
    log_info "Stopping $PROJECT_NAME..."
    docker-compose -f $COMPOSE_FILE down
    log_success "$PROJECT_NAME stopped"
}

# Restart the application
restart_app() {
    log_info "Restarting $PROJECT_NAME..."
    stop_app
    start_app $1
}

# Show logs
show_logs() {
    log_info "Showing application logs..."
    docker-compose -f $COMPOSE_FILE logs -f
}

# Clean up
cleanup() {
    log_warning "Cleaning up Docker resources..."
    docker-compose -f $COMPOSE_FILE down -v --rmi all
    docker system prune -f
    log_success "Cleanup completed"
}

# Show usage
show_usage() {
    echo "AgriPredictX Deployment Script"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  dev      - Deploy in development mode (API only)"
    echo "  prod     - Deploy in production mode (with nginx)"
    echo "  stop     - Stop the application"
    echo "  restart  - Restart the application"
    echo "  logs     - Show application logs"
    echo "  cleanup  - Remove all Docker resources"
    echo "  build    - Build Docker images only"
    echo ""
    echo "Examples:"
    echo "  $0 dev      # Start development deployment"
    echo "  $0 prod     # Start production deployment"
    echo "  $0 stop     # Stop all services"
    echo "  $0 logs     # View logs"
}

# Main script
main() {
    check_docker

    case "${1:-dev}" in
        "dev")
            create_directories
            build_app
            start_app "dev"
            ;;
        "prod")
            create_directories
            build_app
            start_app "prod"
            ;;
        "stop")
            stop_app
            ;;
        "restart")
            restart_app "${2:-dev}"
            ;;
        "logs")
            show_logs
            ;;
        "cleanup")
            cleanup
            ;;
        "build")
            build_app
            ;;
        *)
            show_usage
            exit 1
            ;;
    esac
}

main "$@"