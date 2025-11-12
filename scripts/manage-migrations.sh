#!/bin/bash

###############################################################################
# Database Migration Management Script
#
# Manages Alembic database migrations for AP2 Expense Agent
# Handles migration creation, application, and rollback
###############################################################################

set -euo pipefail

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Get backend pod for Kubernetes
get_backend_pod() {
    if kubectl get namespace ap2-expense &>/dev/null; then
        kubectl get pods -n ap2-expense -l app.kubernetes.io/component=backend -o jsonpath='{.items[0].metadata.name}'
    else
        echo ""
    fi
}

# Execute Alembic command in Kubernetes
exec_alembic_k8s() {
    local pod=$(get_backend_pod)

    if [ -z "$pod" ]; then
        log_error "No backend pod found in Kubernetes"
        exit 1
    fi

    log_info "Executing in pod: $pod"
    kubectl exec -it "$pod" -n ap2-expense -- alembic "$@"
}

# Execute Alembic command locally
exec_alembic_local() {
    cd backend
    alembic "$@"
    cd ..
}

# Determine execution environment
exec_alembic() {
    local env="${EXECUTION_ENV:-auto}"

    case "$env" in
        kubernetes|k8s)
            exec_alembic_k8s "$@"
            ;;
        local)
            exec_alembic_local "$@"
            ;;
        auto)
            if kubectl get namespace ap2-expense &>/dev/null; then
                log_info "Using Kubernetes environment"
                exec_alembic_k8s "$@"
            else
                log_info "Using local environment"
                exec_alembic_local "$@"
            fi
            ;;
        *)
            log_error "Unknown environment: $env"
            exit 1
            ;;
    esac
}

# Show current migration status
show_current() {
    log_info "Current migration status:"
    exec_alembic current -v
}

# Show migration history
show_history() {
    log_info "Migration history:"
    exec_alembic history -v
}

# List pending migrations
show_heads() {
    log_info "Head revisions:"
    exec_alembic heads -v
}

# Upgrade to latest
upgrade_latest() {
    log_warning "Upgrading database to latest version..."

    read -p "Continue? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        log_info "Upgrade cancelled"
        return 0
    fi

    exec_alembic upgrade head

    log_success "Database upgraded to latest version"
    show_current
}

# Upgrade to specific revision
upgrade_to() {
    local revision=$1

    log_warning "Upgrading database to revision: $revision"

    read -p "Continue? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        log_info "Upgrade cancelled"
        return 0
    fi

    exec_alembic upgrade "$revision"

    log_success "Database upgraded to $revision"
    show_current
}

# Downgrade by N revisions
downgrade() {
    local steps="${1:--1}"

    log_warning "========================================="
    log_warning "DOWNGRADING DATABASE"
    log_warning "========================================="
    log_warning "This will rollback $steps migrations"
    log_warning "DATA MAY BE LOST!"
    echo ""

    read -p "Type 'DOWNGRADE' to confirm: " confirm
    if [ "$confirm" != "DOWNGRADE" ]; then
        log_info "Downgrade cancelled"
        return 0
    fi

    exec_alembic downgrade "$steps"

    log_success "Database downgraded by $steps revisions"
    show_current
}

# Downgrade to specific revision
downgrade_to() {
    local revision=$1

    log_warning "========================================="
    log_warning "DOWNGRADING TO REVISION"
    log_warning "========================================="
    log_warning "Target revision: $revision"
    log_warning "DATA MAY BE LOST!"
    echo ""

    read -p "Type 'DOWNGRADE' to confirm: " confirm
    if [ "$confirm" != "DOWNGRADE" ]; then
        log_info "Downgrade cancelled"
        return 0
    fi

    exec_alembic downgrade "$revision"

    log_success "Database downgraded to $revision"
    show_current
}

# Create new migration
create_migration() {
    local message=$1

    if [ -z "$message" ]; then
        log_error "Migration message required"
        echo "Usage: $0 create-migration 'migration description'"
        exit 1
    fi

    log_info "Creating new migration: $message"

    # Must be done locally
    cd backend
    alembic revision --autogenerate -m "$message"
    cd ..

    log_success "Migration created"
    log_info "Review the generated migration file in backend/alembic/versions/"
    log_warning "Remember to commit the migration file to version control"
}

# Stamp database at revision
stamp_revision() {
    local revision=$1

    log_warning "Stamping database at revision: $revision"
    log_warning "This marks the database as being at this revision WITHOUT running migrations"

    read -p "Continue? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        log_info "Stamp cancelled"
        return 0
    fi

    exec_alembic stamp "$revision"

    log_success "Database stamped at $revision"
}

# Verify migration consistency
verify_migrations() {
    log_info "Verifying migration consistency..."

    # Check for branches
    log_info "Checking for migration branches..."
    local heads_count=$(exec_alembic heads --resolve-dependencies 2>&1 | grep -c "^[a-f0-9]" || echo "1")

    if [ "$heads_count" -gt 1 ]; then
        log_error "Multiple heads detected! Migration tree is branched."
        log_error "Run: alembic merge to create a merge migration"
        return 1
    fi

    log_success "No migration branches detected"

    # Show current state
    show_current
    show_heads

    log_success "Migration verification complete"
}

# Create backup before migration
create_pre_migration_backup() {
    log_info "Creating pre-migration backup..."

    if [ -f "./scripts/backup-database.sh" ]; then
        ./scripts/backup-database.sh create
        log_success "Backup created"
    else
        log_warning "Backup script not found, skipping backup"
    fi
}

# Safe upgrade with backup
safe_upgrade() {
    log_info "========================================="
    log_info "SAFE UPGRADE (with backup)"
    log_info "========================================="

    # Create backup
    create_pre_migration_backup

    # Show what will be upgraded
    log_info "Current version:"
    show_current

    log_info "Target version: head (latest)"

    read -p "Proceed with upgrade? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        log_info "Upgrade cancelled"
        return 0
    fi

    # Perform upgrade
    if exec_alembic upgrade head; then
        log_success "Upgrade completed successfully"
        show_current
    else
        log_error "Upgrade failed!"
        log_warning "You can restore from backup using:"
        echo "  ./scripts/disaster-recovery.sh restore-db <backup-id>"
        return 1
    fi
}

# Generate SQL for migration (doesn't execute)
generate_sql() {
    local from_rev="${1:-current}"
    local to_rev="${2:-head}"

    log_info "Generating SQL for migration: $from_rev → $to_rev"

    exec_alembic upgrade "$from_rev:$to_rev" --sql

    log_info "SQL generation complete (not executed)"
}

# Test migration (up then down)
test_migration() {
    local revision="${1:-+1}"

    log_warning "Testing migration: upgrade then downgrade"
    log_warning "This will modify the database temporarily"

    read -p "Continue? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        log_info "Test cancelled"
        return 0
    fi

    # Backup current revision
    local current_rev=$(exec_alembic current | grep -oP '^[a-f0-9]+' || echo "")

    log_info "Current revision: $current_rev"

    # Upgrade
    log_info "Upgrading..."
    if ! exec_alembic upgrade "$revision"; then
        log_error "Upgrade failed!"
        return 1
    fi

    # Downgrade
    log_info "Downgrading..."
    if ! exec_alembic downgrade "$current_rev"; then
        log_error "Downgrade failed!"
        log_warning "Database may be in inconsistent state!"
        return 1
    fi

    log_success "Migration test passed"
}

# Print usage
print_usage() {
    echo "Database Migration Management Script"
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  current              - Show current migration version"
    echo "  history              - Show migration history"
    echo "  heads                - Show head revisions"
    echo "  upgrade              - Upgrade to latest (head)"
    echo "  upgrade-to <rev>     - Upgrade to specific revision"
    echo "  downgrade [steps]    - Downgrade N steps (default: -1)"
    echo "  downgrade-to <rev>   - Downgrade to specific revision"
    echo "  create <message>     - Create new migration (local only)"
    echo "  stamp <rev>          - Mark database at revision (no migration)"
    echo "  verify               - Verify migration consistency"
    echo "  safe-upgrade         - Upgrade with pre-backup"
    echo "  generate-sql [from] [to] - Generate SQL for migration"
    echo "  test [rev]           - Test migration (up then down)"
    echo ""
    echo "Environment:"
    echo "  EXECUTION_ENV=kubernetes  - Run in Kubernetes pod"
    echo "  EXECUTION_ENV=local       - Run locally"
    echo "  EXECUTION_ENV=auto        - Auto-detect (default)"
    echo ""
    echo "Examples:"
    echo "  $0 current"
    echo "  $0 upgrade"
    echo "  $0 downgrade -1"
    echo "  $0 create-migration 'add user preferences'"
    echo "  EXECUTION_ENV=local $0 safe-upgrade"
    echo ""
}

# Main execution
main() {
    local command="${1:-help}"

    case "$command" in
        current)
            show_current
            ;;
        history)
            show_history
            ;;
        heads)
            show_heads
            ;;
        upgrade)
            upgrade_latest
            ;;
        upgrade-to)
            if [ -z "${2:-}" ]; then
                log_error "Revision required"
                echo "Usage: $0 upgrade-to <revision>"
                exit 1
            fi
            upgrade_to "$2"
            ;;
        downgrade)
            downgrade "${2:--1}"
            ;;
        downgrade-to)
            if [ -z "${2:-}" ]; then
                log_error "Revision required"
                echo "Usage: $0 downgrade-to <revision>"
                exit 1
            fi
            downgrade_to "$2"
            ;;
        create|create-migration)
            if [ -z "${2:-}" ]; then
                log_error "Migration message required"
                echo "Usage: $0 create-migration 'migration description'"
                exit 1
            fi
            create_migration "$2"
            ;;
        stamp)
            if [ -z "${2:-}" ]; then
                log_error "Revision required"
                echo "Usage: $0 stamp <revision>"
                exit 1
            fi
            stamp_revision "$2"
            ;;
        verify)
            verify_migrations
            ;;
        safe-upgrade)
            safe_upgrade
            ;;
        generate-sql)
            generate_sql "${2:-current}" "${3:-head}"
            ;;
        test)
            test_migration "${2:-+1}"
            ;;
        help|--help|-h)
            print_usage
            ;;
        *)
            log_error "Unknown command: $command"
            print_usage
            exit 1
            ;;
    esac
}

main "$@"
