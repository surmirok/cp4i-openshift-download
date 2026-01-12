#!/usr/bin/env python3
"""
CP4I Component Downloader - Enhanced Python Implementation
Matches all features from the bash script version
"""

import os
import sys
import json
import subprocess
import logging
import time
import signal
import threading
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import argparse
import re

# Script version
SCRIPT_VERSION = "2.0.0"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class CP4IDownloader:
    """Enhanced Python implementation of CP4I component downloader"""
    
    def __init__(self, home_dir: str = "/opt/cp4i", verbose: bool = False):
        self.home_dir = home_dir
        self.ibmpak_home = home_dir
        self.verbose = verbose
        self.config_file = os.path.join(home_dir, ".cp4i-downloader.conf")
        
        # Configuration defaults
        self.min_disk_space_gb = 100
        self.max_retries = 3
        self.retry_base_delay = 5
        self.max_parallel_downloads = 2
        
        # Runtime tracking
        self.start_time = datetime.now()
        self.download_start_time = None
        self.total_images = 0
        self.failed_images = []
        self.success_count = 0
        self.progress_monitor_thread = None
        self.stop_monitoring = False
        
        # Notification settings
        self.webhook_url = os.environ.get('CP4I_WEBHOOK_URL', '')
        self.notification_email = os.environ.get('CP4I_NOTIFICATION_EMAIL', '')
        
        # Ensure home directory exists
        Path(home_dir).mkdir(parents=True, exist_ok=True)
        
        # Load configuration file if exists
        self.load_config_file()
        
        # Setup signal handlers for cleanup
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle cleanup on signal"""
        logger.info("Received signal, cleaning up...")
        self.stop_progress_monitor()
        sys.exit(1)
    
    def log_debug(self, msg: str):
        """Log debug message if verbose mode is enabled"""
        if self.verbose:
            logger.debug(msg)
    
    def load_config_file(self):
        """Load configuration from file"""
        if os.path.exists(self.config_file):
            logger.info(f"Loading configuration from {self.config_file}")
            try:
                with open(self.config_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if '=' in line:
                                key, value = line.split('=', 1)
                                key = key.strip()
                                value = value.strip().strip('"').strip("'")
                                
                                # Set configuration values
                                if key == 'MIN_DISK_SPACE_GB':
                                    self.min_disk_space_gb = int(value)
                                elif key == 'MAX_RETRIES':
                                    self.max_retries = int(value)
                                elif key == 'RETRY_BASE_DELAY':
                                    self.retry_base_delay = int(value)
                                elif key == 'MAX_PARALLEL_DOWNLOADS':
                                    self.max_parallel_downloads = int(value)
                                elif key == 'CP4I_WEBHOOK_URL':
                                    self.webhook_url = value
                                elif key == 'CP4I_NOTIFICATION_EMAIL':
                                    self.notification_email = value
                
                logger.info("Configuration loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load configuration: {e}")
        else:
            self.log_debug(f"No configuration file found at {self.config_file}")
    
    def create_sample_config(self):
        """Create a sample configuration file"""
        config_content = """# CP4I Downloader Configuration File
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
"""
        try:
            with open(self.config_file, 'w') as f:
                f.write(config_content)
            logger.info(f"Sample configuration created at {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to create configuration file: {e}")
            return False
    
    def check_prerequisites(self) -> Tuple[bool, List[str]]:
        """Check if all required tools are installed"""
        logger.info("Validating prerequisites...")
        required_tools = ['oc', 'podman', 'curl', 'jq']
        missing = []
        
        for tool in required_tools:
            result = subprocess.run(
                ['which', tool],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                missing.append(tool)
        
        # Check oc ibm-pak plugin
        result = subprocess.run(
            ['oc', 'ibm-pak', '--version'],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            missing.append('oc-ibm-pak')
        
        if len(missing) == 0:
            logger.info("✓ All prerequisites validated")
            return (True, [])
        else:
            logger.error(f"Missing required commands: {', '.join(missing)}")
            return (False, missing)
    
    def check_disk_space(self, path: str) -> Tuple[bool, int]:
        """Check available disk space"""
        logger.info("Checking available disk space...")
        try:
            stat = os.statvfs(path)
            available_gb = (stat.f_bavail * stat.f_frsize) // (1024**3)
            
            self.log_debug(f"Available space: {available_gb}GB, Required: {self.min_disk_space_gb}GB")
            
            if available_gb >= self.min_disk_space_gb:
                logger.info(f"✓ Disk space check passed ({available_gb}GB available)")
                return (True, available_gb)
            else:
                logger.error(f"Insufficient disk space. Available: {available_gb}GB, Required: {self.min_disk_space_gb}GB")
                return (False, available_gb)
        except Exception as e:
            logger.error(f"Failed to check disk space: {e}")
            return (False, 0)
    
    def check_github_access(self) -> bool:
        """Check GitHub connectivity"""
        logger.info("Checking GitHub connectivity...")
        
        endpoints = [
            "https://github.com",
            "https://api.github.com",
            "https://raw.githubusercontent.com"
        ]
        
        for endpoint in endpoints:
            try:
                response = requests.head(endpoint, timeout=5)
                if response.status_code < 500:
                    logger.info(f"✓ GitHub is accessible via {endpoint}")
                    return True
            except:
                continue
        
        logger.warning("GitHub is not accessible")
        return False
    
    def configure_ibmpak_repo(self) -> bool:
        """Configure oc ibm-pak to use appropriate repository"""
        if self.check_github_access():
            logger.info("Using default GitHub repository for ibm-pak")
            return True
        else:
            logger.info("Configuring ibm-pak to use OCI registry (cp.icr.io)")
            try:
                result = subprocess.run(
                    [
                        'oc', 'ibm-pak', 'config', 'repo',
                        'IBM Cloud-Pak OCI registry',
                        '-r', 'oci:cp.icr.io/cpopen',
                        '--enable'
                    ],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    logger.info("✓ OCI registry configured successfully")
                    return True
                else:
                    logger.warning(f"Failed to configure OCI registry: {result.stderr}")
                    logger.warning("Attempting to continue...")
                    return False
            except Exception as e:
                logger.error(f"Repository configuration error: {e}")
                return False
    
    def retry_with_backoff(self, command: List[str], max_attempts: int = None) -> bool:
        """Execute command with retry logic and exponential backoff"""
        if max_attempts is None:
            max_attempts = self.max_retries
        
        delay = self.retry_base_delay
        
        for attempt in range(1, max_attempts + 1):
            logger.info(f"Attempt {attempt}/{max_attempts}: {' '.join(command)}")
            
            try:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    env={**os.environ, 'IBMPAK_HOME': self.ibmpak_home}
                )
                
                if result.returncode == 0:
                    logger.info(f"✓ Command succeeded on attempt {attempt}")
                    return True
                
                if attempt < max_attempts:
                    logger.warning(f"Command failed. Retrying in {delay}s...")
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
            
            except Exception as e:
                logger.error(f"Command execution error: {e}")
                if attempt < max_attempts:
                    time.sleep(delay)
                    delay *= 2
        
        logger.error(f"Command failed after {max_attempts} attempts")
        return False
    
    def authenticate_registry(self, entitlement_key: Optional[str] = None, registry_auth_file: Optional[str] = None) -> bool:
        """Authenticate to IBM Container Registry with retry logic"""
        logger.info("Authenticating to IBM registry...")
        
        # Get auth file path
        if not registry_auth_file:
            registry_auth_file = os.environ.get('REGISTRY_AUTH_FILE', '/root/.docker/config.json')
        
        # First, check if already authenticated via podman
        check_cmd = ['podman', 'login', '--get-login', 'cp.icr.io']
        try:
            result = subprocess.run(check_cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                logger.info(f"✓ Already authenticated to cp.icr.io as {result.stdout.strip()}")
                return True
        except Exception as e:
            self.log_debug(f"Podman auth check failed: {e}")
        
        # Check if auth file exists and has cp.icr.io credentials
        if os.path.exists(registry_auth_file):
            try:
                with open(registry_auth_file, 'r') as f:
                    auth_data = json.load(f)
                    auths = auth_data.get('auths', {})
                    if 'cp.icr.io' in auths or 'https://cp.icr.io' in auths:
                        logger.info(f"✓ Found existing credentials in {registry_auth_file}")
                        logger.info("✓ Registry authentication successful (using existing credentials)")
                        return True
            except Exception as e:
                self.log_debug(f"Failed to read auth file: {e}")
        
        # If entitlement key provided, use it to authenticate
        if entitlement_key:
            cmd = ['podman', 'login', 'cp.icr.io', '-u', 'cp', '-p', entitlement_key]
            if self.retry_with_backoff(cmd, 3):
                logger.info("✓ Registry authentication successful")
                return True
            else:
                logger.error("Registry authentication failed with entitlement key")
                return False
        
        # No entitlement key and no existing credentials
        logger.warning("No entitlement key provided and no existing credentials found")
        logger.info("Attempting to proceed - authentication may be required during image pull")
        logger.info("If download fails, please provide entitlement key via:")
        logger.info("  1. --entitlement-key argument")
        logger.info("  2. CP4I_ENTITLEMENT_KEY environment variable")
        logger.info("  3. Or authenticate manually: podman login cp.icr.io -u cp")
        
        # Return True to allow the process to continue - oc image mirror will handle auth
        return True
    
    def send_notification(self, status: str, message: str, component: str = "", version: str = ""):
        """Send notification via webhook or email"""
        timestamp = datetime.now().isoformat()
        
        # Webhook notification
        if self.webhook_url:
            try:
                payload = {
                    'status': status,
                    'component': component,
                    'version': version,
                    'message': message,
                    'timestamp': timestamp
                }
                requests.post(self.webhook_url, json=payload, timeout=5)
                self.log_debug("Webhook notification sent")
            except Exception as e:
                logger.warning(f"Failed to send webhook notification: {e}")
        
        # Email notification (requires mail command)
        if self.notification_email:
            try:
                subject = f"CP4I Download {status}: {component} v{version}"
                subprocess.run(
                    ['mail', '-s', subject, self.notification_email],
                    input=message.encode(),
                    timeout=10
                )
                self.log_debug("Email notification sent")
            except Exception as e:
                logger.warning(f"Failed to send email notification: {e}")
    
    def track_progress(self, mapping_file: str, log_file: str):
        """Start background progress monitoring"""
        if not os.path.exists(mapping_file):
            logger.warning("Mapping file not found for progress tracking")
            return
        
        try:
            with open(mapping_file, 'r') as f:
                content = f.read()
                # Count lines that look like image references
                # Format: file://... or cp.icr.io/...
                lines = content.strip().split('\n')
                self.total_images = 0
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Count non-empty, non-comment lines
                        self.total_images += 1
                
            logger.info(f"Total images to download: {self.total_images}")
            
            # Log first few lines for debugging
            if self.total_images == 0:
                logger.warning("Mapping file appears to be empty or has no valid entries")
                logger.info(f"Mapping file location: {mapping_file}")
                try:
                    with open(mapping_file, 'r') as f:
                        first_lines = f.readlines()[:5]
                        if first_lines:
                            logger.info("First 5 lines of mapping file:")
                            for line in first_lines:
                                logger.info(f"  {line.rstrip()}")
                        else:
                            logger.warning("Mapping file is completely empty")
                except:
                    pass
        except Exception as e:
            logger.warning(f"Failed to count images: {e}")
            return
        
        # Start progress monitor thread only if there are images
        if self.total_images > 0:
            self.stop_monitoring = False
            self.progress_monitor_thread = threading.Thread(
                target=self._progress_monitor,
                args=(log_file,),
                daemon=True
            )
            self.progress_monitor_thread.start()
    
    def _progress_monitor(self, log_file: str):
        """Background thread to monitor progress"""
        while not self.stop_monitoring:
            try:
                if os.path.exists(log_file):
                    with open(log_file, 'r') as f:
                        content = f.read()
                        completed = content.count('Copying blob')
                        if self.total_images > 0:
                            percent = (completed * 100) // self.total_images
                            self.log_debug(f"Progress: {completed}/{self.total_images} images ({percent}%)")
            except Exception as e:
                self.log_debug(f"Progress monitor error: {e}")
            
            time.sleep(30)
    
    def stop_progress_monitor(self):
        """Stop the progress monitoring thread"""
        if self.progress_monitor_thread and self.progress_monitor_thread.is_alive():
            self.stop_monitoring = True
            self.progress_monitor_thread.join(timeout=2)
    
    def generate_summary_report(
        self,
        status: str,
        component: str,
        version: str,
        name: str,
        local_dir: str,
        mapping_file: str
    ) -> str:
        """Generate comprehensive summary report"""
        end_time = datetime.now()
        duration = end_time - self.start_time
        hours = duration.seconds // 3600
        minutes = (duration.seconds % 3600) // 60
        seconds = duration.seconds % 60
        
        report_file = os.path.join(local_dir, f"{name}-summary-report.txt")
        
        report_content = f"""========================================
CP4I Download Summary Report
========================================
Status: {status}
Component: {component}
Version: {version}
Start Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}
End Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}
Duration: {hours}h {minutes}m {seconds}s
Total Images: {self.total_images}
Successful: {self.success_count}
Failed: {len(self.failed_images)}
========================================

Working Directory: {local_dir}
Mapping File: {mapping_file}
Log File: {os.path.join(local_dir, f'{name}-download.log')}

"""
        
        if self.failed_images:
            report_content += "Failed Images:\n"
            for img in self.failed_images:
                report_content += f"  {img}\n"
            report_content += "\n"
        
        report_content += f"""========================================
Generated by CP4I Downloader v{SCRIPT_VERSION}
========================================
"""
        
        try:
            with open(report_file, 'w') as f:
                f.write(report_content)
            logger.info(f"Summary report generated: {report_file}")
            print(report_content)
            return report_file
        except Exception as e:
            logger.error(f"Failed to generate summary report: {e}")
            return ""
    
    def fetch_operator(self, component: str, version: str, skip_dependencies: bool = True) -> bool:
        """Fetch operator CASE bundle with retry logic"""
        logger.info(f"Fetching operator: {component} v{version}")
        
        cmd = ['oc', 'ibm-pak', 'get', component, '--version', version]
        if skip_dependencies:
            cmd.append('--skip-dependencies')
        
        if self.retry_with_backoff(cmd):
            logger.info("✓ Operator fetched successfully")
            return True
        else:
            # Check if operator exists locally
            local_path = os.path.join(
                self.ibmpak_home,
                '.ibm-pak', 'data', 'mirror',
                component, version
            )
            if os.path.exists(local_path):
                logger.warning("Operator fetch failed but found locally. Continuing...")
                return True
            else:
                logger.error("Operator fetch failed and not available locally")
                return False
    
    def generate_manifests(
        self,
        component: str,
        version: str,
        final_registry: str,
        filter_pattern: Optional[str] = None,
        direct_to_registry: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """Generate mirror manifests with retry logic
        
        Args:
            component: Component name
            version: Component version
            final_registry: Target registry URL
            filter_pattern: Optional filter pattern
            direct_to_registry: If True, generate manifests for direct registry-to-registry mirroring
                               If False, generate manifests for filesystem mirroring
        """
        logger.info("Generating mirror manifests...")
        
        # For direct-to-registry: use TARGET_REGISTRY with --install-method OLM
        # For filesystem: use file://integration with --final-registry
        if direct_to_registry:
            target = final_registry
            logger.info(f"Generating manifests for direct-to-registry mirroring to {final_registry}")
            logger.info("Using --install-method OLM for direct registry-to-registry transfer")
        else:
            target = 'file://integration'
            logger.info(f"Generating manifests for filesystem mirroring")
        
        cmd = [
            'oc', 'ibm-pak', 'generate', 'mirror-manifests',
            component
        ]
        
        # Add --version first
        cmd.extend(['--version', version])
        
        # Add target registry
        cmd.append(target)
        
        # Add --install-method OLM for direct-to-registry mode
        if direct_to_registry:
            cmd.extend(['--install-method', 'OLM'])
        else:
            # Add --final-registry for filesystem mode
            cmd.extend(['--final-registry', final_registry])
        
        if filter_pattern:
            cmd.extend(['--filter', filter_pattern])
        
        if self.retry_with_backoff(cmd):
            logger.info("✓ Manifests generated successfully")
            
            # Get mapping file path
            # For direct-to-registry, the mapping file is images-mapping.txt
            # For filesystem, it's images-mapping-to-filesystem.txt
            if direct_to_registry:
                mapping_filename = 'images-mapping.txt'
            else:
                mapping_filename = 'images-mapping-to-filesystem.txt'
            
            mapping_file = os.path.join(
                self.ibmpak_home,
                '.ibm-pak', 'data', 'mirror',
                component, version,
                mapping_filename
            )
            
            return (True, mapping_file)
        else:
            logger.error("Manifest generation failed")
            return (False, None)
    
    def mirror_images(
        self,
        mapping_file: str,
        target_dir: str,
        registry_auth_file: str,
        max_per_registry: int = None,
        dry_run: bool = False,
        log_file: str = None,
        direct_to_registry: bool = False
    ) -> bool:
        """Mirror images using oc image mirror
        
        Args:
            mapping_file: Path to images-mapping.txt file
            target_dir: Target directory for filesystem mirroring (ignored if direct_to_registry=True)
            registry_auth_file: Path to registry authentication file
            max_per_registry: Maximum parallel downloads per registry
            dry_run: If True, simulate the mirroring process
            log_file: Path to log file
            direct_to_registry: If True, mirror directly from source to target registry (no local storage)
                               If False, mirror to filesystem using --dir flag
        """
        if max_per_registry is None:
            max_per_registry = self.max_parallel_downloads
        
        if dry_run:
            logger.info("[Dry Run Mode] Simulating image mirror process...")
        else:
            if direct_to_registry:
                logger.info(f"Starting direct registry-to-registry mirror process...")
                logger.info(f"Images will be mirrored directly from source to target registry")
                logger.info(f"No local disk space required (except temporary)")
            else:
                logger.info(f"Starting filesystem mirror process...")
                logger.info(f"Images will be downloaded to: {target_dir}")
        
        self.download_start_time = datetime.now()
        
        # Build command based on mirror mode
        cmd = [
            'oc', 'image', 'mirror',
            '-f', mapping_file,
            '--filter-by-os', '.*',
            '-a', registry_auth_file,
            '--insecure',
            '--skip-multiple-scopes',
            f'--max-per-registry={max_per_registry}'
        ]
        
        # Add --dir flag ONLY for filesystem mirroring
        # For direct-to-registry, do NOT add --dir flag
        if not direct_to_registry:
            cmd.extend(['--dir', target_dir])
        
        if dry_run:
            cmd.append('--dry-run')
            logger.info(f"[Dry Run] Executing: {' '.join(cmd)}")
        else:
            # Determine mirror log file path
            mirror_log_file = log_file.replace('-download.log', '-mirror.log') if log_file else None
            if mirror_log_file:
                logger.info(f"Monitor mirror progress: tail -f {mirror_log_file}")
        
        try:
            # Log the full command for debugging
            logger.info(f"Executing: {' '.join(cmd)}")
            
            # Determine mirror log file path
            mirror_log_file = log_file.replace('-download.log', '-mirror.log') if log_file else None
            
            if mirror_log_file:
                logger.info(f"Mirror output will be written to: {mirror_log_file}")
                
                # Open mirror log file for writing
                with open(mirror_log_file, 'w') as mirror_log:
                    # Run the command and redirect output to mirror log file
                    process = subprocess.Popen(
                        cmd,
                        stdout=mirror_log,
                        stderr=subprocess.STDOUT,
                        text=True
                    )
                    
                    # Log the PID for monitoring
                    logger.info(f"Image mirroring started in background (PID: {process.pid})")
                    
                    # Wait for process to complete
                    return_code = process.wait()
            else:
                # Fallback: run without separate log file
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                )
                
                # Stream output to main logger
                for line in iter(process.stdout.readline, ''):
                    if line:
                        logger.info(line.rstrip())
                
                process.stdout.close()
                return_code = process.wait()
            
            if return_code == 0:
                if dry_run:
                    logger.info("✓ [Dry Run] Image mirror simulation completed successfully")
                else:
                    logger.info("✓ info: Mirroring completed")
                return True
            else:
                logger.error(f"Image mirroring failed with code {return_code}")
                return False
        
        except Exception as e:
            logger.error(f"Mirror error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def download_component(
        self,
        component: str,
        version: str,
        name: str,
        final_registry: str = "registry.example.com:5000",
        registry_auth_file: str = None,
        entitlement_key: str = None,
        filter_pattern: str = None,
        dry_run: bool = False,
        retry: bool = False,
        force_retry: bool = False,
        max_per_registry: int = None,
        direct_to_registry: bool = False
    ) -> Dict:
        """
        Main method to download a CP4I component
        
        Args:
            component: Component name
            version: Component version
            name: Download directory name
            final_registry: Target registry URL
            registry_auth_file: Path to registry auth file
            entitlement_key: IBM entitlement key
            filter_pattern: Optional filter pattern
            dry_run: If True, simulate the download
            retry: If True, retry from existing mapping file
            force_retry: If True, force retry with fresh auth
            max_per_registry: Maximum parallel downloads
            direct_to_registry: If True, mirror directly to target registry without local storage
                               If False, download to filesystem first
        
        Returns:
            Dict with status, message, and details
        """
        result = {
            'success': False,
            'component': component,
            'version': version,
            'name': name,
            'start_time': self.start_time.isoformat(),
            'messages': []
        }
        
        # Set default registry auth file
        if not registry_auth_file:
            registry_auth_file = os.path.expanduser('~/.docker/config.json')
            if not os.path.exists(registry_auth_file):
                registry_auth_file = '/root/.docker/config.json'
        
        # Create working directory
        local_dir = os.path.join(self.home_dir, name)
        Path(local_dir).mkdir(parents=True, exist_ok=True)
        result['work_dir'] = local_dir
        
        # Setup logging to file
        log_file = os.path.join(local_dir, f'{name}-download.log')
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s'))
        logger.addHandler(file_handler)
        
        # Set environment variables
        os.environ['IBMPAK_HOME'] = self.ibmpak_home
        os.environ['REGISTRY_AUTH_FILE'] = registry_auth_file
        
        try:
            logger.info("=" * 60)
            logger.info(f"CP4I Component Downloader v{SCRIPT_VERSION}")
            logger.info("=" * 60)
            logger.info(f"Working directory: {local_dir}")
            
            # Define mapping file path based on mirror mode
            # For direct-to-registry: use images-mapping.txt
            # For filesystem: use images-mapping-to-filesystem.txt
            if direct_to_registry:
                mapping_filename = 'images-mapping.txt'
            else:
                mapping_filename = 'images-mapping-to-filesystem.txt'
            
            mapping_file = os.path.join(
                self.ibmpak_home,
                '.ibm-pak', 'data', 'mirror',
                component, version,
                mapping_filename
            )
            
            # ========= RETRY MODES =========
            if force_retry or retry:
                if os.path.exists(mapping_file):
                    logger.info(f"Resuming mirror from: {mapping_file}")
                    
                    if dry_run:
                        logger.info("[Dry Run] Would resume image mirror")
                        result['success'] = True
                        result['messages'].append("[Dry Run] Resume simulation")
                    else:
                        self.track_progress(mapping_file, log_file)
                        logger.info(f"Mirror re-initiated for {component} v{version}")
                        self.send_notification("RESUMED", f"Download resumed for {component} v{version}", component, version)
                        
                        if self.mirror_images(mapping_file, local_dir, registry_auth_file, max_per_registry, dry_run, log_file, direct_to_registry):
                            result['success'] = True
                            result['messages'].append("Mirror resumed and completed successfully")
                            self.send_notification("COMPLETED", f"Download completed for {component} v{version}", component, version)
                        else:
                            result['messages'].append("Mirror resume failed")
                            self.send_notification("FAILED", f"Download failed for {component} v{version}", component, version)
                    
                    self.stop_progress_monitor()
                    result['end_time'] = datetime.now().isoformat()
                    self.generate_summary_report(
                        "COMPLETED" if result['success'] else "FAILED",
                        component, version, name, local_dir, mapping_file
                    )
                    return result
                else:
                    result['messages'].append(f"Mapping file not found for retry: {mapping_file}")
                    logger.error(result['messages'][-1])
                    return result
            
            # ========= NORMAL DOWNLOAD FLOW =========
            
            # Step 1: Check prerequisites
            prereqs_ok, missing = self.check_prerequisites()
            if not prereqs_ok:
                result['messages'].append(f"Missing prerequisites: {', '.join(missing)}")
                return result
            result['messages'].append("Prerequisites check passed")
            
            # Step 2: Check disk space (skip for direct-to-registry mode)
            if not direct_to_registry:
                space_ok, available_gb = self.check_disk_space(local_dir)
                if not space_ok:
                    result['messages'].append(f"Insufficient disk space: {available_gb}GB available")
                    return result
                result['messages'].append(f"Disk space check passed: {available_gb}GB available")
            else:
                logger.info("Skipping disk space check for direct-to-registry mode")
                result['messages'].append("Direct-to-registry mode: No local disk space required")
            
            # Step 3: Authenticate
            if not self.authenticate_registry(entitlement_key, registry_auth_file):
                result['messages'].append("Registry authentication failed")
                return result
            result['messages'].append("Registry authentication successful")
            
            # Step 4: Configure repository
            self.configure_ibmpak_repo()
            result['messages'].append("Repository configured")
            
            # Step 5: Fetch operator
            if not self.fetch_operator(component, version):
                result['messages'].append("Operator fetch failed")
                return result
            result['messages'].append("Operator fetched successfully")
            
            # Step 6: Generate manifests
            success, mapping_file = self.generate_manifests(
                component, version, final_registry, filter_pattern, direct_to_registry
            )
            if not success or not mapping_file:
                result['messages'].append("Manifest generation failed")
                return result
            result['messages'].append("Manifests generated successfully")
            result['mapping_file'] = mapping_file
            
            # Step 7: Mirror images
            if not dry_run:
                self.track_progress(mapping_file, log_file)
                self.send_notification("STARTED", f"Download started for {component} v{version}", component, version)
            
            if self.mirror_images(mapping_file, local_dir, registry_auth_file, max_per_registry, dry_run, log_file, direct_to_registry):
                if dry_run:
                    result['messages'].append("[Dry Run] Image mirror simulation completed")
                else:
                    result['messages'].append("Image mirroring completed successfully")
                    self.send_notification("COMPLETED", f"Download completed for {component} v{version}", component, version)
                result['success'] = True
            else:
                result['messages'].append("Image mirroring failed")
                self.send_notification("FAILED", f"Download failed for {component} v{version}", component, version)
            
            # Stop progress monitoring
            self.stop_progress_monitor()
            
            # Generate summary report
            result['end_time'] = datetime.now().isoformat()
            result['duration'] = str(datetime.now() - self.start_time)
            
            report_file = self.generate_summary_report(
                "COMPLETED" if result['success'] else "FAILED",
                component, version, name, local_dir, mapping_file
            )
            result['report_file'] = report_file
            
            # Log retry command
            if result['success']:
                logger.info(f"✓ Setup complete. Download running.")
            logger.info(f"To retry if needed: {sys.argv[0]} --component {component} --version {version} --name {name} --retry")
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            result['messages'].append(f"Error: {str(e)}")
            self.stop_progress_monitor()
            self.send_notification("FAILED", f"Download error: {str(e)}", component, version)
        
        finally:
            logger.removeHandler(file_handler)
            file_handler.close()
        
        return result


# CLI interface
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=f'CP4I Component Downloader v{SCRIPT_VERSION}',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic download (to filesystem)
  %(prog)s --component ibm-integration-platform-navigator --version 7.3.2 --name pn-7.3.2

  # Direct to registry (no local storage)
  %(prog)s --component ibm-integration-platform-navigator --version 7.3.2 --name pn-7.3.2 \\
    --final-registry registry.example.com:5000 --direct-to-registry

  # With filter
  %(prog)s --component ibm-apiconnect --version 10.0.8 --name apic-10.0.8 --filter ".*management.*"

  # Dry run
  %(prog)s --component ibm-mq --version 9.3.5 --name mq-9.3.5 --dry-run

  # Retry failed download
  %(prog)s --component ibm-eventstreams --version 11.4.0 --name es-11.4.0 --retry

Environment Variables:
  CP4I_ENTITLEMENT_KEY      IBM entitlement key
  CP4I_WEBHOOK_URL          Webhook URL for notifications
  CP4I_NOTIFICATION_EMAIL   Email for notifications
        """
    )
    
    parser.add_argument('--component', help='Component name')
    parser.add_argument('--version', help='Component version')
    parser.add_argument('--name', help='Download directory name')
    parser.add_argument('--home-dir', default='/opt/cp4i', help='Home directory (default: /opt/cp4i)')
    parser.add_argument('--final-registry', default='registry.example.com:5000', help='Final registry')
    parser.add_argument('--registry-auth-file', help='Registry auth file')
    parser.add_argument('--entitlement-key', help='IBM Entitlement Key')
    parser.add_argument('--filter', help='Manifest filter pattern')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    parser.add_argument('--retry', action='store_true', help='Resume previous download')
    parser.add_argument('--force-retry', action='store_true', help='Force retry from mapping file')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--max-per-registry', type=int, default=2, help='Max parallel downloads (default: 2)')
    parser.add_argument('--direct-to-registry', action='store_true', help='Mirror directly to target registry (no local storage)')
    parser.add_argument('--create-config', action='store_true', help='Create sample configuration file')
    
    args = parser.parse_args()
    
    # Handle create-config
    if args.create_config:
        downloader = CP4IDownloader(args.home_dir)
        sys.exit(0 if downloader.create_sample_config() else 1)
    
    # Validate required arguments for download
    if not args.component or not args.version or not args.name:
        parser.error("--component, --version, and --name are required for download operations")
    
    # Set verbose logging
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    downloader = CP4IDownloader(args.home_dir, args.verbose)
    
    result = downloader.download_component(
        component=args.component,
        version=args.version,
        name=args.name,
        final_registry=args.final_registry,
        registry_auth_file=args.registry_auth_file,
        entitlement_key=args.entitlement_key,
        filter_pattern=args.filter,
        dry_run=args.dry_run,
        retry=args.retry,
        force_retry=args.force_retry,
        max_per_registry=args.max_per_registry,
        direct_to_registry=args.direct_to_registry
    )
    
    print("\n" + "=" * 60)
    print("DOWNLOAD RESULT")
    print("=" * 60)
    print(json.dumps(result, indent=2))
    print("=" * 60)
    
    sys.exit(0 if result['success'] else 1)

# Made with Bob
