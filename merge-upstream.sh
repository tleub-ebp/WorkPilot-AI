#!/bin/bash

#
# Merge upstream changes from Auto-Claude into your fork
#
# This script syncs your fork with the official Auto-Claude repository.
# It handles multiple branches and includes safety checks.
#
# Usage:
#   ./merge-upstream.sh
#   ./merge-upstream.sh develop
#   ./merge-upstream.sh --skip-push
#   ./merge-upstream.sh develop --skip-push
#
# Note: Make this script executable: chmod +x merge-upstream.sh

set -e

# Colors
GREEN='\033[32m'
RED='\033[31m'
YELLOW='\033[33m'
CYAN='\033[36m'
RESET='\033[0m'

# Variables
BRANCH="main"
SKIP_PUSH=false
HAS_ERRORS=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-push)
            SKIP_PUSH=true
            shift
            ;;
        --branch)
            BRANCH="$2"
            shift 2
            ;;
        *)
            # First positional argument is the branch
            if [[ -z "$BRANCH" ]] || [[ "$BRANCH" == "main" ]]; then
                BRANCH="$1"
            fi
            shift
            ;;
    esac
done

# Logging functions
log_info() {
    echo -e "${CYAN}•${RESET} $1"
}

log_success() {
    echo -e "${GREEN}✓${RESET} $1"
}

log_error() {
    echo -e "${RED}✗${RESET} $1"
    HAS_ERRORS=true
}

log_warning() {
    echo -e "${YELLOW}⚠${RESET} $1"
}

# Helper functions
git_available() {
    if ! command -v git &> /dev/null; then
        log_error "Git is not installed or not in PATH"
        return 1
    fi
    return 0
}

get_current_branch() {
    git rev-parse --abbrev-ref HEAD 2>/dev/null || echo ""
}

test_remote_exists() {
    git remote -v | grep -q "^$1"
    return $?
}

invoke_git() {
    local cmd="$1"
    local desc="$2"
    
    if [[ -n "$desc" ]]; then
        log_info "$desc"
    fi
    
    if ! output=$(git $cmd 2>&1); then
        log_error "Failed: git $cmd"
        echo "$output"
        return 1
    fi
    return 0
}

# Main execution
echo ""
echo -e "${CYAN}════════════════════════════════════════${RESET}"
echo -e "${CYAN}  Auto-Claude Upstream Merge Tool${RESET}"
echo -e "${CYAN}════════════════════════════════════════${RESET}"
echo ""

# Pre-flight checks
log_info "Performing pre-flight checks..."
echo ""

if ! git_available; then
    exit 1
fi
log_success "Git is available"

CURRENT_BRANCH=$(get_current_branch)
if [[ -z "$CURRENT_BRANCH" ]]; then
    log_error "Could not determine current branch"
    exit 1
fi
log_success "Current branch: $CURRENT_BRANCH"

if ! test_remote_exists "upstream"; then
    log_warning "Upstream remote not found. Configuring..."
    if ! invoke_git "remote add upstream https://github.com/AndyMik90/Auto-Claude.git" "Adding upstream remote"; then
        log_error "Could not configure upstream remote"
        exit 1
    fi
    log_success "Upstream remote configured"
else
    log_success "Upstream remote exists"
fi

# Check for uncommitted changes
echo ""
if [[ -n $(git status --porcelain) ]]; then
    log_warning "Working directory has uncommitted changes:"
    git status --short
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Merge cancelled"
        exit 0
    fi
fi

echo ""

# Fetch upstream
log_info "Fetching latest changes from upstream..."
if ! invoke_git "fetch upstream" ""; then
    exit 1
fi
log_success "Fetch complete"
echo ""

# Switch to target branch if needed
if [[ "$CURRENT_BRANCH" != "$BRANCH" ]]; then
    log_info "Switching to branch: $BRANCH"
    if ! invoke_git "checkout $BRANCH" ""; then
        log_error "Could not switch to branch: $BRANCH"
        exit 1
    fi
    log_success "Switched to $BRANCH"
fi

# Merge upstream
log_info "Merging upstream/$BRANCH into local $BRANCH..."
if ! invoke_git "merge upstream/$BRANCH" ""; then
    log_error "Merge failed. Resolve conflicts and try again."
    exit 1
fi
log_success "Merge successful"
echo ""

# Push to origin if not skipped
if [[ "$SKIP_PUSH" == false ]]; then
    log_info "Pushing changes to origin/$BRANCH..."
    if ! invoke_git "push origin $BRANCH" ""; then
        log_error "Push failed. Check your network and permissions."
        exit 1
    fi
    log_success "Push successful"
else
    log_warning "Skipped pushing changes. Review your merge and push manually:"
    echo "  git push origin $BRANCH"
fi

echo ""
echo -e "${GREEN}════════════════════════════════════════${RESET}"
log_success "Upstream merge complete!"
echo -e "${GREEN}════════════════════════════════════════${RESET}"
echo ""

exit 0
