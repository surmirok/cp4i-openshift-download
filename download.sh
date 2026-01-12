#!/bin/bash

# ========================================
# CP4I Component Downloader - Enhanced
# ========================================
# Features:
# - GitHub/OCI registry auto-detection
# - Prerequisite validation
# - Disk space checking
# - Retry logic with exponential backoff
# - Progress tracking
# - Configuration file support
# - Enhanced logging and reporting
# - Notification support
# - Performance optimizations
# ========================================

set -o pipefail

# ========= CONFIGURATION =========
readonly SCRIPT_VERSION="2.0.0"

# These will be passed as parameters or environment variables
HOME_DIR="${HOME_DIR:-/opt/cp4i}"
FINAL_REGISTRY="${FINAL_REGISTRY:-registry.example.com:5000}"
REGISTRY_AUTH_FILE="${REGISTRY_AUTH_FILE:-/root/.docker/config.json}"
ENTITLEMENT_KEY="${ENTITLEMENT_KEY:-${CP4I_ENTITLEMENT_KEY:-}}"

# Debug: Log received configuration
echo "[DEBUG] Received HOME_DIR: ${HOME_DIR}" >&2
echo "[DEBUG] Received FINAL_REGISTRY: ${FINAL_REGISTRY}" >&2
echo "[DEBUG] Received REGISTRY_AUTH_FILE: ${REGISTRY_AUTH_FILE}" >&2

readonly CONFIG_FILE="${HOME_DIR}/.cp4i-downloader.conf"
readonly MIN_DISK_SPACE_GB=100
readonly MAX_RETRIES=3
readonly RETRY_BASE_DELAY=5
readonly MAX_PARALLEL_DOWNLOADS=2

# Additional environment variable support
WEBHOOK_URL="${CP4I_WEBHOOK_URL:-}"
NOTIFICATION_EMAIL="${CP4I_NOTIFICATION_EMAIL:-}"

# ========= GLOBAL VARIABLES =========
COMPONENT="" VERSION="" NAME="" FILTER=""
DRYRUN=false RETRY=false FORCE_RETRY=false
VERBOSE=false CONFIG_MODE=false
START_TIME=$(date +%s)
DOWNLOAD_START_TIME=0
TOTAL_IMAGES=0
FAILED_IMAGES=()
SUCCESS_COUNT=0

# ========= UTILITIES =========
timestamp() { date '+%Y-%m-%d %H:%M:%S'; }

log() {
  local level="${1:-INFO}"
  shift
  local msg="$*"
  local log_file="${LOCAL_DIR:-/tmp}/${NAME:-cp4i}-download.log"
  echo "[$(timestamp)] [$level] $msg" | tee -a "$log_file"
}

log_info()    { log "INFO" "$@"; }
log_warn()    { log "WARN" "$@"; }
log_error()   { log "ERROR" "$@"; }
log_success() { log "SUCCESS" "$@"; }
log_debug()   { $VERBOSE && log "DEBUG" "$@"; }

abort() {
  log_error "$@"
  send_notification "FAILED" "$*"
  generate_summary_report "FAILED"
  exit 1
}

# ========= PREREQUISITE VALIDATION =========
check_prerequisites() {
  log_info "Validating prerequisites..."
  local missing=()
  
  for cmd in oc podman curl jq timeout; do
    if ! command -v "$cmd" &> /dev/null; then
      missing+=("$cmd")
    fi
  done
  
  if [[ ${#missing[@]} -gt 0 ]]; then
    abort "Missing required commands: ${missing[*]}
    
Install instructions:
  - oc: https://docs.openshift.com/container-platform/latest/cli_reference/openshift_cli/getting-started-cli.html
  - podman: https://podman.io/getting-started/installation
  - curl: Use your package manager (yum/apt/dnf)
  - jq: Use your package manager (yum/apt/dnf)
  - timeout: Usually part of coreutils package"
  fi
  
  # Check oc ibm-pak plugin
  if ! oc ibm-pak --version &> /dev/null; then
    abort "oc ibm-pak plugin not found. Install from: https://github.com/IBM/ibm-pak"
  fi
  
  log_success "All prerequisites validated"
}

# ========= DISK SPACE CHECK =========
check_disk_space() {
  log_info "Checking available disk space..."
  local target_dir="$1"
  local available_gb=$(df -BG "$target_dir" | awk 'NR==2 {print $4}' | sed 's/G//')
  
  log_debug "Available space: ${available_gb}GB, Required: ${MIN_DISK_SPACE_GB}GB"
  
  if [[ $available_gb -lt $MIN_DISK_SPACE_GB ]]; then
    abort "Insufficient disk space. Available: ${available_gb}GB, Required: ${MIN_DISK_SPACE_GB}GB"
  fi
  
  log_success "Disk space check passed (${available_gb}GB available)"
}

# ========= GITHUB CONNECTIVITY CHECK =========
check_github_access() {
  log_info "Checking GitHub connectivity..."
  
  # Try multiple GitHub endpoints
  local endpoints=("https://github.com" "https://api.github.com" "https://raw.githubusercontent.com")
  
  for endpoint in "${endpoints[@]}"; do
    if timeout 5 curl -s --head "$endpoint" > /dev/null 2>&1; then
      log_success "GitHub is accessible via $endpoint"
      return 0
    fi
  done
  
  log_warn "GitHub is not accessible"
  return 1
}

# ========= CONFIGURE IBM-PAK REPOSITORY =========
configure_ibmpak_repo() {
  if check_github_access; then
    log_info "Using default GitHub repository for ibm-pak"
    return 0
  else
    log_info "Configuring ibm-pak to use OCI registry (cp.icr.io)"
    # Always configure OCI registry, even in dry-run mode (needed for manifest generation)
    if oc ibm-pak config repo 'IBM Cloud-Pak OCI registry' -r oci:cp.icr.io/cpopen --enable; then
      log_success "OCI registry configured successfully"
    else
      log_warn "Failed to configure OCI registry, attempting to continue..."
    fi
  fi
}

# ========= RETRY LOGIC WITH EXPONENTIAL BACKOFF =========
retry_with_backoff() {
  local max_attempts="$1"
  shift
  local command=("$@")
  local attempt=1
  local delay=$RETRY_BASE_DELAY
  
  while [[ $attempt -le $max_attempts ]]; do
    log_info "Attempt $attempt/$max_attempts: ${command[*]}"
    
    if "${command[@]}"; then
      log_success "Command succeeded on attempt $attempt"
      return 0
    fi
    
    if [[ $attempt -lt $max_attempts ]]; then
      log_warn "Command failed. Retrying in ${delay}s..."
      sleep "$delay"
      delay=$((delay * 2))  # Exponential backoff
    fi
    
    ((attempt++))
  done
  
  log_error "Command failed after $max_attempts attempts"
  return 1
}

# ========= AUTHENTICATION =========
authenticate_registry() {
  log_info "Authenticating to IBM registry..."
  
  # Always authenticate, even in dry-run mode (needed for manifest generation)
  
  if [[ -n "$ENTITLEMENT_KEY" ]]; then
    retry_with_backoff 3 podman login cp.icr.io -u cp -p "$ENTITLEMENT_KEY" || \
      abort "Registry authentication failed with entitlement key"
  else
    retry_with_backoff 3 podman login cp.icr.io || \
      abort "Registry authentication failed (interactive mode)"
  fi
  
  log_success "Registry authentication successful"
}

# ========= PROGRESS TRACKING =========
track_progress() {
  local mapping_file="$1"
  local log_file="$2"
  
  if [[ ! -f "$mapping_file" ]]; then
    log_warn "Mapping file not found for progress tracking"
    return
  fi
  
  TOTAL_IMAGES=$(grep -c "^file://" "$mapping_file" || echo "0")
  log_info "Total images to download: $TOTAL_IMAGES"
  
  # Background progress monitor
  (
    while true; do
      if [[ -f "$log_file" ]]; then
        local completed=$(grep -c "Copying blob" "$log_file" 2>/dev/null || echo "0")
        local percent=$((completed * 100 / TOTAL_IMAGES))
        log_debug "Progress: $completed/$TOTAL_IMAGES images ($percent%)"
      fi
      sleep 30
    done
  ) &
  
  echo $! > "${LOCAL_DIR}/.progress_monitor.pid"
}

stop_progress_monitor() {
  if [[ -f "${LOCAL_DIR}/.progress_monitor.pid" ]]; then
    local pid=$(cat "${LOCAL_DIR}/.progress_monitor.pid")
    kill "$pid" 2>/dev/null || true
    rm -f "${LOCAL_DIR}/.progress_monitor.pid"
  fi
}

# ========= NOTIFICATION SUPPORT =========
send_notification() {
  local status="$1"
  local message="$2"
  
  # Webhook notification
  if [[ -n "$WEBHOOK_URL" ]]; then
    local payload=$(jq -n \
      --arg status "$status" \
      --arg component "$COMPONENT" \
      --arg version "$VERSION" \
      --arg message "$message" \
      --arg timestamp "$(timestamp)" \
      '{status: $status, component: $component, version: $version, message: $message, timestamp: $timestamp}')
    
    curl -s -X POST "$WEBHOOK_URL" \
      -H "Content-Type: application/json" \
      -d "$payload" &> /dev/null || log_warn "Failed to send webhook notification"
  fi
  
  # Email notification (requires mailx or sendmail)
  if [[ -n "$NOTIFICATION_EMAIL" ]] && command -v mail &> /dev/null; then
    echo "$message" | mail -s "CP4I Download $status: $COMPONENT v$VERSION" "$NOTIFICATION_EMAIL" &> /dev/null || \
      log_warn "Failed to send email notification"
  fi
}

# ========= SUMMARY REPORT =========
generate_summary_report() {
  local status="$1"
  local end_time=$(date +%s)
  local duration=$((end_time - START_TIME))
  local hours=$((duration / 3600))
  local minutes=$(((duration % 3600) / 60))
  local seconds=$((duration % 60))
  
  local report_file="${LOCAL_DIR}/${NAME}-summary-report.txt"
  
  cat > "$report_file" <<EOF
========================================
CP4I Download Summary Report
========================================
Status: $status
Component: $COMPONENT
Version: $VERSION
Start Time: $(date -d "@$START_TIME" '+%Y-%m-%d %H:%M:%S')
End Time: $(date -d "@$end_time" '+%Y-%m-%d %H:%M:%S')
Duration: ${hours}h ${minutes}m ${seconds}s
Total Images: $TOTAL_IMAGES
Successful: $SUCCESS_COUNT
Failed: ${#FAILED_IMAGES[@]}
========================================

Working Directory: $LOCAL_DIR
Mapping File: $MAPPING_FILE
Log File: ${LOCAL_DIR}/${NAME}-download.log

EOF

  if [[ ${#FAILED_IMAGES[@]} -gt 0 ]]; then
    cat >> "$report_file" <<EOF
Failed Images:
$(printf '%s\n' "${FAILED_IMAGES[@]}")

EOF
  fi
  
  cat >> "$report_file" <<EOF
========================================
Generated by CP4I Downloader v$SCRIPT_VERSION
========================================
EOF
  
  log_info "Summary report generated: $report_file"
  cat "$report_file"
}

# ========= CONFIGURATION FILE SUPPORT =========
load_config_file() {
  if [[ -f "$CONFIG_FILE" ]]; then
    log_info "Loading configuration from $CONFIG_FILE"
    # shellcheck source=/dev/null
    source "$CONFIG_FILE"
    log_success "Configuration loaded"
  else
    log_debug "No configuration file found at $CONFIG_FILE"
  fi
}

create_sample_config() {
  cat > "$CONFIG_FILE" <<'EOF'
# CP4I Downloader Configuration File
# Uncomment and set values as needed

# IBM Entitlement Key
#CP4I_ENTITLEMENT_KEY="your_entitlement_key_here"

# Notification Settings
#CP4I_WEBHOOK_URL="https://your-webhook-url.com/notify"
#CP4I_NOTIFICATION_EMAIL="admin@example.com"

# Performance Settings
#MAX_PARALLEL_DOWNLOADS=2

# Disk Space Requirements (GB)
#MIN_DISK_SPACE_GB=100

# Retry Settings
#MAX_RETRIES=3
#RETRY_BASE_DELAY=5
EOF
  
  log_success "Sample configuration created at $CONFIG_FILE"
}

# ========= ARGUMENT PARSING =========
parse_arguments() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --component)     COMPONENT="$2"; shift 2 ;;
      --version)       VERSION="$2"; shift 2 ;;
      --name)          NAME="$2"; shift 2 ;;
      --filter)        FILTER="$2"; shift 2 ;;
      --dry-run)       DRYRUN=true; shift ;;
      --retry)         RETRY=true; shift ;;
      --force-retry)   FORCE_RETRY=true; shift ;;
      --verbose)       VERBOSE=true; shift ;;
      --create-config) create_sample_config; exit 0 ;;
      --help)
        cat <<EOF

CP4I Component Downloader v$SCRIPT_VERSION

Usage: $0 [OPTIONS]

Required Options:
  --component <name>        Operator component name
  --version <version>       Operator version
  --name <directory>        Local directory name

Optional Options:
  --filter <pattern>        Manifest filter pattern
  --dry-run                 Show what would be done without executing
  --retry                   Resume previous download
  --force-retry             Force retry from mapping file
  --verbose                 Enable verbose logging
  --create-config           Create sample configuration file
  --help                    Show this help message

Environment Variables:
  CP4I_ENTITLEMENT_KEY      IBM entitlement key
  CP4I_WEBHOOK_URL          Webhook URL for notifications
  CP4I_NOTIFICATION_EMAIL   Email for notifications

Configuration File:
  $CONFIG_FILE

Examples:
  # Basic download
  $0 --component ibm-integration-platform-navigator --version 7.3.2 --name pn-7.3.2

  # With filter
  $0 --component ibm-apiconnect --version 10.0.8 --name apic-10.0.8 --filter ".*management.*"

  # Dry run
  $0 --component ibm-mq --version 9.3.5 --name mq-9.3.5 --dry-run

  # Retry failed download
  $0 --component ibm-eventstreams --version 11.4.0 --name es-11.4.0 --retry

EOF
        exit 0 ;;
      *) log_error "Unknown option: $1"; exit 1 ;;
    esac
  done
}

# ========= MAIN EXECUTION =========
main() {
  echo "========================================="
  echo "CP4I Component Downloader v$SCRIPT_VERSION"
  echo "========================================="
  
  # Load configuration file
  load_config_file
  
  # Parse arguments
  parse_arguments "$@"
  
  # Validation
  [[ -z "$COMPONENT" || -z "$VERSION" || -z "$NAME" ]] && {
    log_error "Missing required arguments. Use --help for syntax."
    exit 1
  }
  
  # Setup working directory
  LOCAL_DIR="$HOME_DIR/$NAME"
  mkdir -p "$LOCAL_DIR" || abort "Failed to create working directory: $LOCAL_DIR"
  cd "$LOCAL_DIR" || abort "Cannot access working directory: $LOCAL_DIR"
  export IBMPAK_HOME="$HOME_DIR"
  export REGISTRY_AUTH_FILE="$REGISTRY_AUTH_FILE"
  
  log_info "Working directory: $LOCAL_DIR"
  
  # Run prerequisite checks
  check_prerequisites
  check_disk_space "$LOCAL_DIR"
  
  # Authentication
  authenticate_registry
  
  # Configure repository
  configure_ibmpak_repo
  
  # Define mapping file path
  MAPPING_FILE="$IBMPAK_HOME/.ibm-pak/data/mirror/$COMPONENT/$VERSION/images-mapping-to-filesystem.txt"
  
  # ========= RETRY MODES =========
  if $FORCE_RETRY || $RETRY; then
    if [[ -f "$MAPPING_FILE" ]]; then
      log_info "Resuming mirror from: $MAPPING_FILE"
      DOWNLOAD_START_TIME=$(date +%s)
      
      if $DRYRUN; then
        log_info "[Dry Run] Would resume image mirror"
      else
        track_progress "$MAPPING_FILE" "${LOCAL_DIR}/${NAME}-download.log"
        
        log_info "Mirror re-initiated for $COMPONENT v$VERSION"
        send_notification "RESUMED" "Download resumed for $COMPONENT v$VERSION"
        
        # Run in foreground
        oc image mirror -f "$MAPPING_FILE" \
          --filter-by-os '.*' -a "$REGISTRY_AUTH_FILE" \
          --insecure --skip-multiple-scopes --max-per-registry="$MAX_PARALLEL_DOWNLOADS" \
          --dir "$LOCAL_DIR" >> "${LOCAL_DIR}/${NAME}-download.log" 2>&1
        
        log_info "info: Mirroring completed"
        send_notification "COMPLETED" "Download completed for $COMPONENT v$VERSION"
      fi
      exit 0
    else
      abort "Mapping file not found for retry: $MAPPING_FILE"
    fi
  fi
  
  # ========= OPERATOR FETCH =========
  log_info "Fetching operator: $COMPONENT v$VERSION"
  
  # Always fetch operator, even in dry-run mode (to generate manifests)
  if ! retry_with_backoff "$MAX_RETRIES" oc ibm-pak get "$COMPONENT" --version "$VERSION" --skip-dependencies; then
    if [[ -d "$IBMPAK_HOME/.ibm-pak/data/mirror/$COMPONENT/$VERSION" ]]; then
      log_warn "Operator fetch failed but found locally. Continuing..."
    else
      abort "Operator fetch failed and not available locally"
    fi
  else
    log_success "Operator fetched successfully"
  fi
  
  # ========= MANIFEST GENERATION =========
  log_info "Generating mirror manifests..."
  
  GEN_CMD="oc ibm-pak generate mirror-manifests $COMPONENT file://integration --version $VERSION --final-registry $FINAL_REGISTRY"
  [[ -n "$FILTER" ]] && GEN_CMD+=" --filter $FILTER"
  
  # Always generate manifests, even in dry-run mode
  if retry_with_backoff "$MAX_RETRIES" eval "$GEN_CMD"; then
    log_success "Manifests generated successfully"
  else
    abort "Manifest generation failed"
  fi
  
  # ========= IMAGE MIRROR =========
  if $DRYRUN; then
    log_info "[Dry Run Mode] Simulating image mirror process..."
  else
    log_info "Starting image mirror process..."
  fi
  DOWNLOAD_START_TIME=$(date +%s)
  
  if $DRYRUN; then
    # In dry-run mode, execute oc image mirror with --dry-run flag
    log_info "[Dry Run] Executing: oc image mirror -f $MAPPING_FILE --dry-run ..."
    
    if oc image mirror -f "$MAPPING_FILE" \
      --registry-config="$REGISTRY_AUTH_FILE" \
      --continue-on-error=true \
      --skip-multiple-scopes \
      --max-per-registry=1 \
      --dry-run 2>&1 | tee -a "${LOCAL_DIR}/${NAME}-download.log"; then
      log_success "[Dry Run] Image mirror simulation completed successfully"
    else
      log_warn "[Dry Run] Image mirror simulation completed with warnings"
    fi
  else
    track_progress "$MAPPING_FILE" "${LOCAL_DIR}/${NAME}-download.log"
    
    log_info "Image mirroring started for $COMPONENT v$VERSION"
    log_info "Monitor progress: tail -f ${LOCAL_DIR}/${NAME}-download.log"
    
    send_notification "STARTED" "Download started for $COMPONENT v$VERSION"
    
    # Run in foreground so we can monitor properly
    oc image mirror -f "$MAPPING_FILE" \
      --filter-by-os '.*' -a "$REGISTRY_AUTH_FILE" \
      --insecure --skip-multiple-scopes --max-per-registry="$MAX_PARALLEL_DOWNLOADS" \
      --dir "$LOCAL_DIR" >> "${LOCAL_DIR}/${NAME}-download.log" 2>&1
    
    log_info "info: Mirroring completed"
    send_notification "COMPLETED" "Download completed for $COMPONENT v$VERSION"
  fi
  
  log_success "Setup complete. Download running."
  log_info "To retry if needed: $0 --component $COMPONENT --version $VERSION --name $NAME --retry"
}

# Trap to cleanup on exit
trap 'stop_progress_monitor' EXIT

# Run main function
main "$@"

# Made with Bob