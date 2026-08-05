#!/bin/bash

# ai-factory-growth-engine - Development Environment Setup Script
# This script sets up the development environment for the ai-factory-growth-engine project.
# It installs necessary dependencies, configures the environment, and prepares the project for development.
#
# Usage:
# ./scripts/setup.sh
# make setup

set -e # Exit on any error

# ===========================================
# Configuration
# ===========================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ===========================================
# Print Functions
# ===========================================

print_header() {
  echo ""
  echo -e "${CYAN}========================================${NC}"
  echo -e "${CYAN}  $1${NC}"
  echo -e "${CYAN}========================================${NC}"
  echo ""
}

print_step() {
  echo -e "${BLUE}[STEP]${NC} $1"
}

print_info() {
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

# ===========================================
# Utility Functions
# ===========================================

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# ===========================================
# Validation
# ===========================================

check_requirements() {
  print_step "Checking system requirements..."

  local has_errors=false

  # Check UV
  if command_exists uv; then
    print_success "UV package manager available"
  else
    print_warning "UV not installed"
    print_info "Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    has_errors=true
  fi

  # Check Make (optional)
  if command_exists make; then
    print_success "Make available"
  else
    print_warning "Make not installed (optional)"
  fi

  if [ "$has_errors" = true ]; then
    print_error "Please fix the above issues and try again"
    exit 1
  fi

  print_success "All required tools are available"
}

# ===========================================
# Pre-commit Hooks
# ===========================================

setup_pre_commit() {
  print_step "Setting up pre-commit hooks..."

  if command_exists uv && [ -d .git ]; then
    if [ -f .pre-commit-config.yaml ]; then
      uv run pre-commit install
      print_success "Pre-commit hooks installed"
    else
      print_warning "No .pre-commit-config.yaml found, skipping hooks"
    fi
  else
    print_warning "uv or git not available, skipping pre-commit hooks"
    print_info "Install manually with: make pre-commit-install"
  fi
}

# ===========================================
# Final Summary
# ===========================================

show_summary() {
  print_header "Setup Complete!"

  echo "Your development environment is ready."

  echo -e "${GREEN}Happy coding!${NC}"
  echo ""
}

# ===========================================
# Main Execution
# ===========================================

main() {
  print_header "ai-factory-growth-engine - Setup"

  check_requirements
  setup_pre_commit
  show_summary
}

# Run main function
main
