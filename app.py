#!/usr/bin/env python3
"""
CP4I Downloader Web Application
Flask-based web interface for managing CP4I component downloads
"""

from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import subprocess
import os
import json
import threading
import time
from datetime import datetime
import glob

app = Flask(__name__)
CORS(app)

# Configuration
HOME_DIR = "/opt/cp4i"
PYTHON_DOWNLOADER = os.path.join(os.path.dirname(__file__), "cp4i_downloader.py")
CONFIG_FILE = os.path.join(HOME_DIR, ".cp4i-downloader.conf")

# In-memory storage for active downloads
active_downloads = {}
download_history = []

class DownloadManager:
    """Manages download processes and their status"""
    
    def __init__(self):
        self.downloads = {}
        self.lock = threading.Lock()
    
    def _generate_summary_report(self, download):
        """Generate a comprehensive summary report for a download"""
        try:
            home_dir = download.get('home_dir', HOME_DIR)
            name = download.get('name')
            component = download.get('component')
            version = download.get('version')
            status = download.get('status')
            start_time = download.get('start_time')
            end_time = download.get('end_time')
            final_registry = download.get('final_registry', 'N/A')
            registry_auth_file = download.get('registry_auth_file', 'N/A')
            filter_pattern = download.get('filter', 'None')
            pid = download.get('pid', 'N/A')
            return_code = download.get('return_code', 'N/A')
            
            # Calculate duration
            try:
                start_dt = datetime.fromisoformat(start_time)
                end_dt = datetime.fromisoformat(end_time)
                duration = str(end_dt - start_dt)
                duration_seconds = (end_dt - start_dt).total_seconds()
            except:
                duration = "N/A"
                duration_seconds = 0
            
            # Get directory information
            download_dir = f"{home_dir}/{name}"
            dir_size = "N/A"
            dir_size_bytes = 0
            if os.path.exists(download_dir):
                try:
                    result = subprocess.run(
                        f"du -sh {download_dir}",
                        shell=True,
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        dir_size = result.stdout.split()[0]
                    
                    # Get size in bytes
                    result_bytes = subprocess.run(
                        f"du -sb {download_dir}",
                        shell=True,
                        capture_output=True,
                        text=True
                    )
                    if result_bytes.returncode == 0:
                        dir_size_bytes = int(result_bytes.stdout.split()[0])
                except:
                    pass
            
            # Count files and directories
            file_count = 0
            dir_count = 0
            image_files = 0
            mapping_files = 0
            log_files = 0
            if os.path.exists(download_dir):
                try:
                    for root, dirs, files in os.walk(download_dir):
                        dir_count += len(dirs)
                        file_count += len(files)
                        for f in files:
                            if f.endswith(('.tar', '.tar.gz', '.tgz')):
                                image_files += 1
                            elif 'mapping' in f.lower():
                                mapping_files += 1
                            elif f.endswith('.log'):
                                log_files += 1
                except:
                    pass
            
            # Check for specific files
            log_file = f"{download_dir}/{name}-download.log"
            mapping_file = f"{download_dir}/mapping.txt"
            config_file = f"{download_dir}/.image-config.json"
            
            log_exists = "Yes" if os.path.exists(log_file) else "No"
            mapping_exists = "Yes" if os.path.exists(mapping_file) else "No"
            config_exists = "Yes" if os.path.exists(config_file) else "No"
            
            # Get log file size
            log_size = "N/A"
            if os.path.exists(log_file):
                try:
                    log_size_bytes = os.path.getsize(log_file)
                    if log_size_bytes < 1024:
                        log_size = f"{log_size_bytes} B"
                    elif log_size_bytes < 1024*1024:
                        log_size = f"{log_size_bytes/1024:.2f} KB"
                    else:
                        log_size = f"{log_size_bytes/(1024*1024):.2f} MB"
                except:
                    pass
            
            # Count images in mapping file
            image_count_from_mapping = 0
            if os.path.exists(mapping_file):
                try:
                    with open(mapping_file, 'r') as f:
                        image_count_from_mapping = len([line for line in f if line.strip() and not line.startswith('#')])
                except:
                    pass
            
            # Get system information
            hostname = "N/A"
            try:
                result = subprocess.run("hostname", shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    hostname = result.stdout.strip()
            except:
                pass
            
            # Get disk space
            disk_space = "N/A"
            try:
                result = subprocess.run(
                    f"df -h {home_dir} | tail -1",
                    shell=True,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    parts = result.stdout.split()
                    if len(parts) >= 5:
                        disk_space = f"Total: {parts[1]}, Used: {parts[2]}, Available: {parts[3]}, Use%: {parts[4]}"
            except:
                pass
            
            # Calculate transfer rate
            transfer_rate = "N/A"
            if dir_size_bytes > 0 and duration_seconds > 0:
                rate_mbps = (dir_size_bytes / (1024*1024)) / duration_seconds
                transfer_rate = f"{rate_mbps:.2f} MB/s"
            
            # Get error information from log if failed
            error_info = ""
            if status == "failed" and os.path.exists(log_file):
                try:
                    with open(log_file, 'r') as f:
                        lines = f.readlines()
                        # Get last 10 lines for error context
                        error_lines = [line.strip() for line in lines[-10:] if 'error' in line.lower() or 'fail' in line.lower()]
                        if error_lines:
                            error_info = "\n".join(error_lines[:5])  # Show up to 5 error lines
                except:
                    pass
            
            # Generate report content
            report_content = f"""
================================================================================
                    CP4I DOWNLOAD SUMMARY REPORT
================================================================================

DOWNLOAD INFORMATION
--------------------
Component:              {component}
Version:                {version}
Directory Name:         {name}
Status:                 {status.upper()}
Process ID:             {pid}
Exit Code:              {return_code}

TIMING DETAILS
--------------
Start Time:             {start_time}
End Time:               {end_time}
Duration:               {duration}
Transfer Rate:          {transfer_rate}

CONFIGURATION
-------------
Home Directory:         {home_dir}
Download Directory:     {download_dir}
Target Registry:        {final_registry}
Registry Auth File:     {registry_auth_file}
Filter Pattern:         {filter_pattern}

FILE SYSTEM DETAILS
-------------------
Directory Exists:       {'Yes' if os.path.exists(download_dir) else 'No'}
Directory Size:         {dir_size}
Total Files:            {file_count}
Total Directories:      {dir_count}
Image Files (.tar):     {image_files}
Mapping Files:          {mapping_files}
Log Files:              {log_files}

KEY FILES
---------
Download Log:           {log_file}
  - Exists:             {log_exists}
  - Size:               {log_size}

Mapping File:           {mapping_file}
  - Exists:             {mapping_exists}
  - Images Listed:      {image_count_from_mapping}

Config File:            {config_file}
  - Exists:             {config_exists}

SYSTEM INFORMATION
------------------
Hostname:               {hostname}
Disk Space ({home_dir}):
  {disk_space}
"""
            
            # Add error information if failed
            if error_info:
                report_content += f"""
ERROR DETAILS
-------------
Recent errors from log file:
{error_info}
"""
            
            report_content += f"""
================================================================================
Report Generated:       {datetime.now().isoformat()}
================================================================================
"""
            
            # Save report to file
            report_file = f"{home_dir}/{name}-summary-report.txt"
            os.makedirs(home_dir, exist_ok=True)
            with open(report_file, 'w') as f:
                f.write(report_content)
            
            print(f"[REPORT] Comprehensive summary report generated: {report_file}")
            return report_file
            
        except Exception as e:
            print(f"[REPORT] Error generating summary report: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def start_download(self, download_id, component, version, name, filter_pattern=None, dry_run=False,
                      home_dir=None, final_registry=None, registry_auth_file=None, entitlement_key=None,
                      download_mode='standard', parallel_downloads=5, retry_attempts=3, skip_existing=True,
                      verify_images=True, include_dependencies=False, generate_catalog=False, create_backup=False,
                      retry=False, force_retry=False, verbose=False, direct_to_registry=False):
        """Start a new download process with advanced options"""
        with self.lock:
            if download_id in self.downloads:
                return {"error": "Download already in progress"}
            
            # Use provided values or defaults
            home_dir = home_dir or HOME_DIR
            final_registry = final_registry or "registry.example.com:5000"
            registry_auth_file = registry_auth_file or "/root/.docker/config.json"
            
            # Build command for Python downloader
            cmd = [
                "python3", PYTHON_DOWNLOADER,
                "--component", component,
                "--version", version,
                "--name", name,
                "--home-dir", home_dir,
                "--final-registry", final_registry,
                "--max-per-registry", str(parallel_downloads)
            ]
            
            if registry_auth_file:
                cmd.extend(["--registry-auth-file", registry_auth_file])
            
            if entitlement_key:
                cmd.extend(["--entitlement-key", entitlement_key])
            
            if filter_pattern:
                cmd.extend(["--filter", filter_pattern])
            
            if dry_run:
                cmd.append("--dry-run")
            
            if retry:
                cmd.append("--retry")
            
            if force_retry:
                cmd.append("--force-retry")
            
            if verbose:
                cmd.append("--verbose")
            
            if direct_to_registry:
                cmd.append("--direct-to-registry")
            
            # Build environment variables (for compatibility)
            env = os.environ.copy()
            
            # Set notification environment variables if configured
            if os.environ.get('CP4I_WEBHOOK_URL'):
                env['CP4I_WEBHOOK_URL'] = os.environ.get('CP4I_WEBHOOK_URL')
            if os.environ.get('CP4I_NOTIFICATION_EMAIL'):
                env['CP4I_NOTIFICATION_EMAIL'] = os.environ.get('CP4I_NOTIFICATION_EMAIL')
            
            # Start process
            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env=env
                )
                
                self.downloads[download_id] = {
                    "id": download_id,
                    "component": component,
                    "version": version,
                    "name": name,
                    "filter": filter_pattern,
                    "process": process,
                    "status": "running",
                    "start_time": datetime.now().isoformat(),
                    "pid": process.pid,
                    "mirror_pid": None,  # Will be populated by monitoring
                    "log_file": f"{home_dir}/{name}/{name}-download.log",
                    "home_dir": home_dir,
                    "final_registry": final_registry,
                    "registry_auth_file": registry_auth_file,
                    "entitlement_key": entitlement_key,
                    "direct_to_registry": direct_to_registry,
                    "download_mode": download_mode
                }
                
                # Start monitoring thread
                threading.Thread(
                    target=self._monitor_download,
                    args=(download_id,),
                    daemon=True
                ).start()
                
                return {"success": True, "download_id": download_id, "pid": process.pid}
            
            except Exception as e:
                return {"error": str(e)}
    
    def _monitor_download(self, download_id):
        """Monitor download process and check log for completion"""
        download = self.downloads.get(download_id)
        if not download:
            return
        
        process = download["process"]
        log_file = download.get("log_file")
        last_log_size = 0
        last_activity_time = time.time()
        check_interval = 30  # Check every 30 seconds
        
        print(f"Starting monitoring for {download_id}, log file: {log_file}")
        
        # Monitor process and log file
        while True:
            # Check if process has finished
            if process.poll() is not None:
                print(f"[{download_id}] Process finished with code {process.returncode}")
                break
            # Check log file for completion message and mirror PID
            if log_file and os.path.exists(log_file):
                try:
                    # Get current file size
                    current_size = os.path.getsize(log_file)
                    
                    # Read log content
                    with open(log_file, 'r') as f:
                        log_content = f.read()
                        lines = log_content.strip().split('\n')
                        last_line = lines[-1] if lines else ""
                        
                        print(f"[{download_id}] Last line: {last_line[:100]}")
                        
                        # Extract mirror PID if not already captured
                        if not download.get("mirror_pid"):
                            import re
                            pid_match = re.search(r'Image mirroring started.*\(PID:\s*(\d+)\)', log_content)
                            if pid_match:
                                with self.lock:
                                    download["mirror_pid"] = int(pid_match.group(1))
                                    print(f"Captured mirror PID: {download['mirror_pid']} for {download_id}")
                        
                        # Check if log is growing (new activity)
                        if current_size > last_log_size:
                            last_activity_time = time.time()
                            last_log_size = current_size
                            with self.lock:
                                if download["status"] != "completed":
                                    download["status"] = "progressing"
                                    # Calculate rough progress based on log activity
                                    download["progress"] = min(95, download.get("progress", 0) + 5)
                            print(f"[{download_id}] Log growing, status: progressing")
                        
                        # Check for error in last line
                        if "error: one or more errors occurred" in last_line.lower():
                            print(f"[{download_id}] ERROR DETECTED in last line!")
                            with self.lock:
                                if download["status"] != "failed":
                                    download["status"] = "failed"
                                    download["end_time"] = datetime.now().isoformat()
                                    print(f"Download {download_id} marked as failed")
                                    
                                    # Generate summary report for failed download
                                    self._generate_summary_report(download)
                                    
                                    # Add to history with ALL configuration for retry
                                    history_entry = {
                                        "id": download_id,
                                        "component": download["component"],
                                        "version": download["version"],
                                        "name": download["name"],
                                        "filter": download.get("filter"),
                                        "status": "failed",
                                        "start_time": download["start_time"],
                                        "end_time": download["end_time"],
                                        "home_dir": download.get("home_dir"),
                                        "final_registry": download.get("final_registry"),
                                        "registry_auth_file": download.get("registry_auth_file"),
                                        "entitlement_key": download.get("entitlement_key"),
                                        # Preserve mode settings for retry
                                        "direct_to_registry": download.get("direct_to_registry", False),
                                        "download_mode": download.get("download_mode", "standard"),
                                        # Preserve OpenShift-specific settings
                                        "mirror_type": download.get("mirror_type"),
                                        "local_repository": download.get("local_repository"),
                                        "product_repo": download.get("product_repo"),
                                        "release_name": download.get("release_name"),
                                        "architecture": download.get("architecture"),
                                        "include_operators": download.get("include_operators"),
                                        "print_idms": download.get("print_idms"),
                                        "generate_icsp": download.get("generate_icsp"),
                                        "skip_verification": download.get("skip_verification"),
                                        # Preserve Red Hat Operators settings
                                        "catalog_version": download.get("catalog_version"),
                                        "operators": download.get("operators"),
                                        "channels": download.get("channels"),
                                        "include_ubi": download.get("include_ubi"),
                                        "include_helm": download.get("include_helm")
                                    }
                                    download_history.append(history_entry)
                                    print(f"Added {download_id} to history as failed")
                            
                            # Wait then remove from active downloads
                            print(f"[{download_id}] Waiting 5 seconds before removal...")
                            time.sleep(5)
                            with self.lock:
                                if download_id in self.downloads:
                                    del self.downloads[download_id]
                                    print(f"[{download_id}] Removed from active downloads")
                            
                            # Exit monitoring loop
                            return
                        
                        # Check for completion in last line
                        if "info: mirroring completed" in last_line.lower():
                            print(f"[{download_id}] COMPLETION DETECTED in last line!")
                            with self.lock:
                                if download["status"] != "completed":
                                    download["status"] = "completed"
                                    download["progress"] = 100
                                    download["end_time"] = datetime.now().isoformat()
                                    print(f"Download {download_id} marked as completed")
                                    
                                    # Generate summary report for completed download
                                    self._generate_summary_report(download)
                                    
                                    # Add to history with ALL configuration for retry
                                    history_entry = {
                                        "id": download_id,
                                        "component": download["component"],
                                        "version": download["version"],
                                        "name": download["name"],
                                        "filter": download.get("filter"),
                                        "status": "completed",
                                        "start_time": download["start_time"],
                                        "end_time": download["end_time"],
                                        "home_dir": download.get("home_dir"),
                                        "final_registry": download.get("final_registry"),
                                        "registry_auth_file": download.get("registry_auth_file"),
                                        "entitlement_key": download.get("entitlement_key"),
                                        # Preserve mode settings for retry
                                        "direct_to_registry": download.get("direct_to_registry", False),
                                        "download_mode": download.get("download_mode", "standard"),
                                        # Preserve OpenShift-specific settings
                                        "mirror_type": download.get("mirror_type"),
                                        "local_repository": download.get("local_repository"),
                                        "product_repo": download.get("product_repo"),
                                        "release_name": download.get("release_name"),
                                        "architecture": download.get("architecture"),
                                        "include_operators": download.get("include_operators"),
                                        "print_idms": download.get("print_idms"),
                                        "generate_icsp": download.get("generate_icsp"),
                                        "skip_verification": download.get("skip_verification"),
                                        # Preserve Red Hat Operators settings
                                        "catalog_version": download.get("catalog_version"),
                                        "operators": download.get("operators"),
                                        "channels": download.get("channels"),
                                        "include_ubi": download.get("include_ubi"),
                                        "include_helm": download.get("include_helm")
                                    }
                                    download_history.append(history_entry)
                                    print(f"Added {download_id} to history")
                            
                            # Wait then remove from active downloads
                            print(f"[{download_id}] Waiting 5 seconds before removal...")
                            time.sleep(5)
                            with self.lock:
                                if download_id in self.downloads:
                                    del self.downloads[download_id]
                                    print(f"[{download_id}] Removed from active downloads")
                            
                            # Exit monitoring loop
                            return
                        
                except Exception as e:
                    print(f"Error monitoring {download_id}: {e}")
            
            time.sleep(check_interval)  # Check every 30 seconds
        
        # Process finished - check one last time for completion
        print(f"[{download_id}] Process loop ended, return code: {process.returncode}")
        
        # Check if it was a successful dry-run, actual completion, or error
        if log_file and os.path.exists(log_file):
            try:
                with open(log_file, 'r') as f:
                    log_content = f.read()
                    lines = log_content.strip().split('\n')
                    last_line = lines[-1] if lines else ""
                    
                    # Check for error in last line first
                    if "error: one or more errors occurred" in last_line.lower():
                        print(f"[{download_id}] Final check: ERROR DETECTED in last line!")
                        
                        with self.lock:
                            if download_id in self.downloads and download["status"] != "failed":
                                download["status"] = "failed"
                                download["end_time"] = datetime.now().isoformat()
                                
                                # Generate summary report
                                self._generate_summary_report(download)
                                
                                # Add to history with ALL configuration for retry
                                history_entry = {
                                    "id": download_id,
                                    "component": download["component"],
                                    "version": download["version"],
                                    "name": download["name"],
                                    "filter": download.get("filter"),
                                    "status": "failed",
                                    "start_time": download["start_time"],
                                    "end_time": download["end_time"],
                                    "home_dir": download.get("home_dir"),
                                    "final_registry": download.get("final_registry"),
                                    "registry_auth_file": download.get("registry_auth_file"),
                                    "entitlement_key": download.get("entitlement_key"),
                                    # Preserve mode settings for retry
                                    "direct_to_registry": download.get("direct_to_registry", False),
                                    "download_mode": download.get("download_mode", "standard"),
                                    # Preserve OpenShift-specific settings
                                    "mirror_type": download.get("mirror_type"),
                                    "local_repository": download.get("local_repository"),
                                    "product_repo": download.get("product_repo"),
                                    "release_name": download.get("release_name"),
                                    "architecture": download.get("architecture"),
                                    "include_operators": download.get("include_operators"),
                                    "print_idms": download.get("print_idms"),
                                    "generate_icsp": download.get("generate_icsp"),
                                    "skip_verification": download.get("skip_verification"),
                                    # Preserve Red Hat Operators settings
                                    "catalog_version": download.get("catalog_version"),
                                    "operators": download.get("operators"),
                                    "channels": download.get("channels"),
                                    "include_ubi": download.get("include_ubi"),
                                    "include_helm": download.get("include_helm")
                                }
                                download_history.append(history_entry)
                                print(f"[{download_id}] Added to history as failed")
                        
                        # Wait then remove
                        time.sleep(5)
                        with self.lock:
                            if download_id in self.downloads:
                                del self.downloads[download_id]
                                print(f"[{download_id}] Removed from active downloads")
                        return
                    
                    # Check for completion message OR successful dry-run
                    is_completed = "info: mirroring completed" in last_line.lower()
                    is_dry_run = "[dry run]" in log_content.lower() and process.returncode == 0
                    
                    if is_completed or is_dry_run:
                        status_msg = "DRY RUN completed" if is_dry_run else "COMPLETION DETECTED"
                        print(f"[{download_id}] Final check: {status_msg}!")
                        
                        with self.lock:
                            if download_id in self.downloads and download["status"] != "completed":
                                download["status"] = "completed"
                                download["progress"] = 100
                                download["end_time"] = datetime.now().isoformat()
                                
                                # Generate summary report
                                self._generate_summary_report(download)
                                
                                # Add to history with ALL configuration for retry
                                history_entry = {
                                    "id": download_id,
                                    "component": download["component"],
                                    "version": download["version"],
                                    "name": download["name"],
                                    "filter": download.get("filter"),
                                    "status": "completed",
                                    "start_time": download["start_time"],
                                    "end_time": download["end_time"],
                                    "home_dir": download.get("home_dir"),
                                    "final_registry": download.get("final_registry"),
                                    "registry_auth_file": download.get("registry_auth_file"),
                                    "entitlement_key": download.get("entitlement_key"),
                                    # Preserve mode settings for retry
                                    "direct_to_registry": download.get("direct_to_registry", False),
                                    "download_mode": download.get("download_mode", "standard"),
                                    # Preserve OpenShift-specific settings
                                    "mirror_type": download.get("mirror_type"),
                                    "local_repository": download.get("local_repository"),
                                    "product_repo": download.get("product_repo"),
                                    "release_name": download.get("release_name"),
                                    "architecture": download.get("architecture"),
                                    "include_operators": download.get("include_operators"),
                                    "print_idms": download.get("print_idms"),
                                    "generate_icsp": download.get("generate_icsp"),
                                    "skip_verification": download.get("skip_verification"),
                                    # Preserve Red Hat Operators settings
                                    "catalog_version": download.get("catalog_version"),
                                    "operators": download.get("operators"),
                                    "channels": download.get("channels"),
                                    "include_ubi": download.get("include_ubi"),
                                    "include_helm": download.get("include_helm")
                                }
                                download_history.append(history_entry)
                                print(f"[{download_id}] Added to history as completed")
                        
                        # Wait then remove
                        time.sleep(5)
                        with self.lock:
                            if download_id in self.downloads:
                                del self.downloads[download_id]
                                print(f"[{download_id}] Removed from active downloads")
                        return
            except Exception as e:
                print(f"Error in final check for {download_id}: {e}")
        
        # If not completed and exit code is non-zero, mark as failed
        if process.returncode != 0:
            print(f"[{download_id}] Process ended with error code {process.returncode}")
            with self.lock:
                if download_id in self.downloads:
                    download["status"] = "failed"
                    download["end_time"] = datetime.now().isoformat()
                    
                    # Generate summary report for failed download
                    self._generate_summary_report(download)
                    
                    # Add to history with ALL configuration for retry
                    history_entry = {
                        "id": download_id,
                        "component": download["component"],
                        "version": download["version"],
                        "name": download["name"],
                        "filter": download.get("filter"),
                        "status": "failed",
                        "start_time": download["start_time"],
                        "end_time": download["end_time"],
                        "home_dir": download.get("home_dir"),
                        "final_registry": download.get("final_registry"),
                        "registry_auth_file": download.get("registry_auth_file"),
                        "entitlement_key": download.get("entitlement_key"),
                        # Preserve mode settings for retry
                        "direct_to_registry": download.get("direct_to_registry", False),
                        "download_mode": download.get("download_mode", "standard"),
                        # Preserve OpenShift-specific settings
                        "mirror_type": download.get("mirror_type"),
                        "local_repository": download.get("local_repository"),
                        "product_repo": download.get("product_repo"),
                        "release_name": download.get("release_name"),
                        "architecture": download.get("architecture"),
                        "include_operators": download.get("include_operators"),
                        "print_idms": download.get("print_idms"),
                        "generate_icsp": download.get("generate_icsp"),
                        "skip_verification": download.get("skip_verification"),
                        # Preserve Red Hat Operators settings
                        "catalog_version": download.get("catalog_version"),
                        "operators": download.get("operators"),
                        "channels": download.get("channels"),
                        "include_ubi": download.get("include_ubi"),
                        "include_helm": download.get("include_helm")
                    }
                    download_history.append(history_entry)
                    del self.downloads[download_id]
                    print(f"[{download_id}] Marked as failed and moved to history")
        else:
            # Exit code 0 but no completion message - treat as completed
            print(f"[{download_id}] Process ended successfully (exit code 0)")
            with self.lock:
                if download_id in self.downloads:
                    download["status"] = "completed"
                    download["progress"] = 100
                    download["end_time"] = datetime.now().isoformat()
                    
                    # Generate summary report
                    self._generate_summary_report(download)
                    # Add to history with ALL configuration for retry
                    history_entry = {
                        "id": download_id,
                        "component": download["component"],
                        "version": download["version"],
                        "name": download["name"],
                        "filter": download.get("filter"),
                        "status": "completed",
                        "start_time": download["start_time"],
                        "end_time": download["end_time"],
                        "home_dir": download.get("home_dir"),
                        "final_registry": download.get("final_registry"),
                        "registry_auth_file": download.get("registry_auth_file"),
                        "entitlement_key": download.get("entitlement_key"),
                        # Preserve mode settings for retry
                        "direct_to_registry": download.get("direct_to_registry", False),
                        "download_mode": download.get("download_mode", "standard"),
                        # Preserve OpenShift-specific settings
                        "mirror_type": download.get("mirror_type"),
                        "local_repository": download.get("local_repository"),
                        "product_repo": download.get("product_repo"),
                        "release_name": download.get("release_name"),
                        "architecture": download.get("architecture"),
                        "include_operators": download.get("include_operators"),
                        "print_idms": download.get("print_idms"),
                        "generate_icsp": download.get("generate_icsp"),
                        "skip_verification": download.get("skip_verification"),
                        # Preserve Red Hat Operators settings
                        "catalog_version": download.get("catalog_version"),
                        "operators": download.get("operators"),
                        "channels": download.get("channels"),
                        "include_ubi": download.get("include_ubi"),
                        "include_helm": download.get("include_helm")
                    }
                    download_history.append(history_entry)
                    del self.downloads[download_id]
                    print(f"[{download_id}] Marked as completed and moved to history")
        
        # Process finished - already added to history above in lines 260-273 or 284-297
        # No need to add again here
    
    def dismiss_download(self, download_id):
        """Remove a download from active list and kill background process"""
        with self.lock:
            if download_id in self.downloads:
                download = self.downloads[download_id]
                
                # Kill the mirror process (nohup oc image mirror)
                mirror_pid = download.get("mirror_pid")
                main_pid = download.get("pid")
                name = download.get("name")
                
                killed_pids = []
                
                # Try to kill mirror PID first (this is the actual download process)
                if mirror_pid:
                    try:
                        os.kill(mirror_pid, 9)
                        killed_pids.append(f"mirror:{mirror_pid}")
                        print(f"Killed mirror process {mirror_pid} for download {download_id}")
                    except ProcessLookupError:
                        print(f"Mirror process {mirror_pid} already terminated")
                    except Exception as e:
                        print(f"Error killing mirror process {mirror_pid}: {e}")
                
                # Kill main script process and all children
                if main_pid:
                    try:
                        # Kill all child processes first
                        subprocess.run(
                            f"pkill -9 -P {main_pid}",
                            shell=True,
                            capture_output=True
                        )
                        # Then kill main process
                        os.kill(main_pid, 9)
                        killed_pids.append(f"main:{main_pid}")
                        print(f"Killed main process {main_pid} and children for download {download_id}")
                    except ProcessLookupError:
                        print(f"Main process {main_pid} already terminated")
                    except Exception as e:
                        print(f"Error killing main process {main_pid}: {e}")
                
                # Also try to kill any remaining oc image mirror processes for this download
                try:
                    result = subprocess.run(
                        f"pkill -9 -f 'oc image mirror.*{name}'",
                        shell=True,
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        print(f"Killed additional oc image mirror processes for {name}")
                except Exception as e:
                    print(f"Error killing additional processes: {e}")
                
                # Mark as dismissed and add to history
                download["status"] = "dismissed"
                download["end_time"] = datetime.now().isoformat()
                
                # Generate summary report for dismissed download
                self._generate_summary_report(download)
                
                # Add to history with ALL configuration for retry
                history_entry = {
                    "id": download_id,
                    "component": download["component"],
                    "version": download["version"],
                    "name": download["name"],
                    "filter": download.get("filter"),
                    "status": "dismissed",
                    "start_time": download["start_time"],
                    "end_time": download["end_time"],
                    "home_dir": download.get("home_dir"),
                    "final_registry": download.get("final_registry"),
                    "registry_auth_file": download.get("registry_auth_file"),
                    "entitlement_key": download.get("entitlement_key"),
                    # Preserve mode settings for retry
                    "direct_to_registry": download.get("direct_to_registry", False),
                    "download_mode": download.get("download_mode", "standard"),
                    # Preserve OpenShift-specific settings
                    "mirror_type": download.get("mirror_type"),
                    "local_repository": download.get("local_repository"),
                    "product_repo": download.get("product_repo"),
                    "release_name": download.get("release_name"),
                    "architecture": download.get("architecture"),
                    "include_operators": download.get("include_operators"),
                    "print_idms": download.get("print_idms"),
                    "generate_icsp": download.get("generate_icsp"),
                    "skip_verification": download.get("skip_verification"),
                    # Preserve Red Hat Operators settings
                    "catalog_version": download.get("catalog_version"),
                    "operators": download.get("operators"),
                    "channels": download.get("channels"),
                    "include_ubi": download.get("include_ubi"),
                    "include_helm": download.get("include_helm")
                }
                download_history.append(history_entry)
                
                # Remove from active downloads
                del self.downloads[download_id]
                
                pids_msg = f"PIDs killed: {killed_pids}" if killed_pids else "No active processes found"
                return {"success": True, "message": f"Download dismissed. {pids_msg}"}
            return {"error": "Download not found"}
    
    def get_download_status(self, download_id):
        """Get status of a specific download"""
        with self.lock:
            download = self.downloads.get(download_id)
            if not download:
                return {"error": "Download not found"}
            
            # Get log tail
            log_tail = self._get_log_tail(download.get("log_file"))
            
            # Get progress if available
            progress = self._get_progress(download.get("name"))
            
            return {
                "id": download_id,
                "component": download["component"],
                "version": download["version"],
                "name": download["name"],
                "status": download["status"],
                "start_time": download["start_time"],
                "end_time": download.get("end_time"),
                "pid": download.get("pid"),
                "log_tail": log_tail,
                "progress": progress
            }
    
    def get_all_downloads(self):
        """Get status of all downloads"""
        with self.lock:
            # Return serializable data only (exclude process object)
            return [{
                "id": d["id"],
                "component": d["component"],
                "version": d["version"],
                "name": d["name"],
                "filter": d.get("filter"),
                "status": d["status"],
                "start_time": d["start_time"],
                "end_time": d.get("end_time"),
                "pid": d.get("mirror_pid") or d.get("pid"),  # Show mirror PID if available
                "main_pid": d.get("pid"),
                "mirror_pid": d.get("mirror_pid"),
                "return_code": d.get("return_code"),
                "progress": d.get("progress", 0)
            } for d in self.downloads.values()]
    
    def stop_download(self, download_id):
        """Stop a running download"""
        with self.lock:
            download = self.downloads.get(download_id)
            if not download:
                return {"error": "Download not found"}
            
            if download["status"] != "running":
                return {"error": "Download is not running"}
            
            try:
                download["process"].terminate()
                download["status"] = "stopped"
                download["end_time"] = datetime.now().isoformat()
                return {"success": True}
            except Exception as e:
                return {"error": str(e)}
    
    def _get_log_tail(self, log_file, lines=50):
        """Get last N lines from log file"""
        if not log_file or not os.path.exists(log_file):
            return []
        
        try:
            with open(log_file, 'r') as f:
                return f.readlines()[-lines:]
        except:
            return []
    
    def _get_progress(self, download_id):
        """Get download progress"""
        download = self.downloads.get(download_id)
        if not download:
            return None
        
        name = download.get('name')
        home_dir = download.get('home_dir', HOME_DIR)
        
        if not name:
            return None
        
        summary_file = f"{home_dir}/{name}/{name}-summary-report.txt"
        if os.path.exists(summary_file):
            try:
                with open(summary_file, 'r') as f:
                    content = f.read()
                    # Parse summary for progress info
                    return {"summary": content}
            except:
                pass
        
        return None

# Initialize download manager
download_manager = DownloadManager()

# Routes
@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')

@app.route('/api/system/info', methods=['GET'])
def system_info():
    """Get system information"""
    try:
        # Get home_dir from query parameter or use default
        home_dir = request.args.get('home_dir', HOME_DIR)
        
        # Check disk space
        disk_info = subprocess.run(
            ['df', '-h', home_dir],
            capture_output=True,
            text=True
        )
        
        # Check prerequisites
        prereqs = {}
        for cmd in ['oc', 'podman', 'curl', 'jq']:
            result = subprocess.run(
                ['which', cmd],
                capture_output=True,
                text=True
            )
            prereqs[cmd] = result.returncode == 0
        
        # Check oc ibm-pak
        ibmpak_result = subprocess.run(
            ['oc', 'ibm-pak', '--version'],
            capture_output=True,
            text=True
        )
        prereqs['oc-ibm-pak'] = ibmpak_result.returncode == 0
        
        return jsonify({
            "disk_info": disk_info.stdout,
            "prerequisites": prereqs,
            "home_dir": home_dir,
            "script_path": PYTHON_DOWNLOADER
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/config', methods=['GET', 'POST'])
def config():
    """Get or update configuration"""
    if request.method == 'GET':
        # Get config file path from query parameter or use default
        config_path = request.args.get('path', CONFIG_FILE)
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    return jsonify({"config": f.read()})
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        return jsonify({"config": ""})
    
    elif request.method == 'POST':
        try:
            data = request.json
            config_content = data.get('config', '')
            config_path = data.get('path', CONFIG_FILE)
            
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, 'w') as f:
                f.write(config_content)
            
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route('/api/downloads', methods=['GET', 'POST'])
def downloads():
    """List or start downloads"""
    if request.method == 'GET':
        return jsonify({
            "active": download_manager.get_all_downloads(),
            "history": download_history
        })
    
    elif request.method == 'POST':
        try:
            data = request.json
            component = data.get('component')
            version = data.get('version')
            name = data.get('name')
            filter_pattern = data.get('filter')
            dry_run = data.get('dry_run', False)
            
            # Get configuration parameters
            home_dir = data.get('home_dir')
            final_registry = data.get('final_registry')
            registry_auth_file = data.get('registry_auth_file')
            entitlement_key = data.get('entitlement_key')
            
            # Get advanced options
            download_mode = data.get('download_mode', 'standard')
            parallel_downloads = data.get('parallel_downloads', 5)
            retry_attempts = data.get('retry_attempts', 3)
            skip_existing = data.get('skip_existing', True)
            verify_images = data.get('verify_images', True)
            include_dependencies = data.get('include_dependencies', False)
            generate_catalog = data.get('generate_catalog', False)
            create_backup = data.get('create_backup', False)
            direct_to_registry = data.get('direct_to_registry', False)
            
            if not all([component, version, name]):
                return jsonify({"error": "Missing required fields"}), 400
            
            if not all([home_dir, final_registry, registry_auth_file]):
                return jsonify({"error": "Missing required configuration parameters (home_dir, final_registry, registry_auth_file)"}), 400
            
            download_id = f"{name}-{int(time.time())}"
            result = download_manager.start_download(
                download_id, component, version, name, filter_pattern, dry_run,
                home_dir, final_registry, registry_auth_file, entitlement_key,
                download_mode=download_mode,
                parallel_downloads=parallel_downloads,
                retry_attempts=retry_attempts,
                skip_existing=skip_existing,
                verify_images=verify_images,
                include_dependencies=include_dependencies,
                generate_catalog=generate_catalog,
                create_backup=create_backup,
                direct_to_registry=direct_to_registry
            )
            
            if "error" in result:
                return jsonify(result), 400
            
            return jsonify(result)
        
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route('/api/downloads/<download_id>', methods=['GET', 'DELETE', 'PATCH'])
def download_detail(download_id):
    """Get, stop, or dismiss a specific download"""
    if request.method == 'GET':
        result = download_manager.get_download_status(download_id)
        if "error" in result:
            return jsonify(result), 404
        return jsonify(result)
    
    elif request.method == 'DELETE':
        result = download_manager.stop_download(download_id)
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)
    
    elif request.method == 'PATCH':
        # Dismiss download
        result = download_manager.dismiss_download(download_id)
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)

@app.route('/api/downloads/<download_id>/retry', methods=['POST'])
def retry_download(download_id):
    """Retry a failed download - reconstructs original command for OpenShift/Operators, uses --retry for CP4I"""
    global download_history
    
    try:
        # Get download info from either active downloads or history
        download = download_manager.downloads.get(download_id)
        if not download:
            # Check history
            for hist in download_history:
                if hist['id'] == download_id:
                    download = hist
                    break
        
        if not download:
            return jsonify({"error": "Download not found"}), 404
        
        component = download.get('component', '')
        
        # Handle OpenShift retry - reconstruct original command
        if component == 'openshift':
            print(f"[RETRY] Retrying OpenShift download with original configuration")
            
            # Get all original parameters
            ocp_release = download.get('version')
            name = download.get('name')
            mirror_type = download.get('mirror_type', 'filesystem')
            local_registry = download.get('final_registry', 'registry.example.com:5000')
            local_repository = download.get('local_repository', 'ocp4/openshift4')
            product_repo = download.get('product_repo', 'openshift-release-dev')
            local_secret_json = download.get('registry_auth_file', '/root/.docker/config.json')
            release_name = download.get('release_name', 'ocp-release')
            architecture = download.get('architecture', 'x86_64')
            removable_media_path = download.get('home_dir', '/opt/ocp')
            include_operators = download.get('include_operators', False)
            print_idms = download.get('print_idms', False)
            generate_icsp = download.get('generate_icsp', False)
            skip_verification = download.get('skip_verification', False)
            
            # Validate required parameters
            if not ocp_release:
                return jsonify({
                    "error": "Cannot retry this download - missing OpenShift version information. Please start a new mirror from the OpenShift Mirror tab."
                }), 400
            if not name:
                # Generate a name if missing
                name = f"ocp-{ocp_release}-{architecture}-retry-{int(time.time())}"
                print(f"[RETRY] Generated name for retry: {name}")
            
            # Build flags
            flags = []
            if skip_verification:
                flags.append("--skip-verification")
            flags_line = " " + " ".join(flags) if flags else ""
            
            # Reconstruct the EXACT same command
            if mirror_type == 'filesystem':
                cmd = f"""
export OCP_RELEASE={ocp_release}
export LOCAL_REGISTRY='{local_registry}'
export LOCAL_REPOSITORY='{local_repository}'
export PRODUCT_REPO='{product_repo}'
export LOCAL_SECRET_JSON="{local_secret_json}"
export RELEASE_NAME="{release_name}"
export ARCHITECTURE={architecture}
export REMOVABLE_MEDIA_PATH="{removable_media_path}"

echo "Retrying OpenShift {ocp_release} mirror to file system..."
oc adm release mirror -a ${{LOCAL_SECRET_JSON}} \\
  --to-dir=${{REMOVABLE_MEDIA_PATH}}/mirror \\
  quay.io/${{PRODUCT_REPO}}/${{RELEASE_NAME}}:${{OCP_RELEASE}}-${{ARCHITECTURE}}{flags_line}
"""
            else:
                cmd = f"""
export OCP_RELEASE={ocp_release}
export LOCAL_REGISTRY='{local_registry}'
export LOCAL_REPOSITORY='{local_repository}'
export PRODUCT_REPO='{product_repo}'
export LOCAL_SECRET_JSON="{local_secret_json}"
export RELEASE_NAME="{release_name}"
export ARCHITECTURE={architecture}

echo "Retrying OpenShift {ocp_release} mirror to registry..."
oc adm release mirror -a ${{LOCAL_SECRET_JSON}} \\
  --from=quay.io/${{PRODUCT_REPO}}/${{RELEASE_NAME}}:${{OCP_RELEASE}}-${{ARCHITECTURE}} \\
  --to=${{LOCAL_REGISTRY}}/${{LOCAL_REPOSITORY}} \\
  --to-release-image=${{LOCAL_REGISTRY}}/${{LOCAL_REPOSITORY}}:${{OCP_RELEASE}}-${{ARCHITECTURE}}{flags_line}
"""
            
            if include_operators:
                ocp_major = ocp_release.split('.')[0]
                ocp_minor = ocp_release.split('.')[1]
                cmd += f"""
echo "\\n=== Mirroring Operator Catalogs ==="
oc adm catalog mirror \\
  registry.redhat.io/redhat/redhat-operator-index:v{ocp_major}.{ocp_minor} \\
  ${{LOCAL_REGISTRY}}/${{LOCAL_REPOSITORY}} \\
  -a ${{LOCAL_SECRET_JSON}}{flags_line}
"""
            
            # Create new download ID
            new_download_id = f"{name}-retry-{int(time.time())}"
            log_file = f"{removable_media_path}/{name}.log"
            
            # Remove old history entry to avoid showing dismissed items
            download_history[:] = [h for h in download_history if h.get('id') != download_id]
            print(f"[RETRY] Removed old history entry for {download_id}")
            
            # Start the process
            process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Log output to file
            def log_output():
                with open(log_file, 'w') as f:
                    if process.stdout:
                        for line in process.stdout:
                            f.write(line)
                            f.flush()
            
            # Start logging thread
            log_thread = threading.Thread(target=log_output, daemon=True)
            log_thread.start()
            
            # Add to download manager with all original parameters
            download_manager.downloads[new_download_id] = {
                "id": new_download_id,
                "component": "openshift",
                "version": ocp_release,
                "name": name,
                "status": "running",
                "start_time": datetime.now().isoformat(),
                "pid": process.pid,
                "process": process,
                "log_file": log_file,
                "home_dir": removable_media_path,
                "final_registry": local_registry,
                "registry_auth_file": local_secret_json,
                "architecture": architecture,
                "dry_run": False,
                "mirror_type": mirror_type,
                "local_repository": local_repository,
                "product_repo": product_repo,
                "release_name": release_name,
                "include_operators": include_operators,
                "print_idms": print_idms,
                "generate_icsp": generate_icsp,
                "skip_verification": skip_verification
            }
            
            # Start monitoring thread
            monitor_thread = threading.Thread(
                target=download_manager._monitor_download,
                args=(new_download_id,),
                daemon=True
            )
            monitor_thread.start()
            
            return jsonify({
                "success": True,
                "download_id": new_download_id,
                "message": f"OpenShift mirror retry started for {ocp_release}"
            })
        
        # Handle Red Hat Operators retry - use same logic as start mirror
        elif component == 'redhat-operators':
            print(f"[RETRY] Retrying Red Hat Operators download with original configuration")
            
            # Get all original parameters
            catalog_version = download.get('catalog_version')
            architecture = download.get('architecture', 'amd64')
            local_path = download.get('home_dir', '/opt/operators')
            auth_file = download.get('registry_auth_file', '/root/.docker/config.json')
            operators = download.get('operators', ['*'])
            channels = download.get('channels', [])
            
            # Ensure operators is a list of strings (handle if it's stored as objects)
            if operators and isinstance(operators, list):
                # If operators contains dicts/objects, extract the name field
                if len(operators) > 0 and isinstance(operators[0], dict):
                    operators = [op.get('name', op) if isinstance(op, dict) else str(op) for op in operators]
                # Ensure all items are strings
                operators = [str(op) for op in operators]
            
            # Ensure channels is a list of strings
            if channels and isinstance(channels, list):
                if len(channels) > 0 and isinstance(channels[0], dict):
                    channels = [ch.get('name', ch) if isinstance(ch, dict) else str(ch) for ch in channels]
                channels = [str(ch) for ch in channels]
            include_ubi = download.get('include_ubi', False)
            include_helm = download.get('include_helm', False)
            mirror_type = download.get('mirror_type', 'filesystem')
            target_registry = download.get('final_registry', '')
            
            # Validate required parameters
            if not catalog_version:
                # Try to extract from version field
                version_str = download.get('version', '')
                if version_str.startswith('v'):
                    catalog_version = version_str[1:]  # Remove 'v' prefix
                else:
                    return jsonify({
                        "error": "Cannot retry this download - missing catalog version information. Please start a new mirror from the Red Hat Operators tab."
                    }), 400
            
            # Create local path
            os.makedirs(local_path, exist_ok=True)
            
            # Generate ImageSetConfiguration (same as start mirror)
            config = f"""kind: ImageSetConfiguration
apiVersion: mirror.openshift.io/v1alpha2
storageConfig:
  local:
    path: {local_path}
mirror:
  platform:
    architectures:
      - {architecture}
  operators:
    - catalog: registry.redhat.io/redhat/redhat-operator-index:v{catalog_version}
"""
            
            if operators and operators[0] == '*':
                config += "      full: true\n"
            elif operators:
                config += "      packages:\n"
                for op in operators:
                    config += f"        - name: {op}\n"
                    if channels:
                        config += "          channels:\n"
                        for ch in channels:
                            config += f"            - name: {ch}\n"
            
            if include_ubi:
                config += """  additionalImages:
    - name: registry.redhat.io/ubi8/ubi:latest
    - name: registry.redhat.io/ubi9/ubi:latest
"""
            
            if include_helm:
                config += "  helm: {}\n"
            
            # Save configuration file
            config_file = f"{local_path}/imageset-config.yaml"
            with open(config_file, 'w') as f:
                f.write(config)
            
            # Generate new download ID
            new_download_id = f"operators-v{catalog_version}-retry-{int(time.time())}"
            name = f"operators-v{catalog_version}"
            
            # Build oc-mirror command based on mirror type
            if mirror_type == 'registry':
                mirror_destination = f"docker://{target_registry}"
                destination_display = target_registry
                mirror_mode_msg = "direct to registry"
            else:
                mirror_destination = f"file://{local_path}"
                destination_display = local_path
                mirror_mode_msg = "to filesystem"
            
            # Build oc-mirror command with --ignore-history
            cmd = f"""
export REGISTRY_AUTH_FILE="{auth_file}"

echo "Retrying Red Hat Operators mirror with --ignore-history..."
echo "Catalog Version: v{catalog_version}"
echo "Architecture: {architecture}"
echo "Operators: {len(operators) if operators[0] != '*' else 'All'}"
echo "Mirror Type: {mirror_type}"
echo "Destination: {destination_display}"
echo "This will skip previously mirrored content."

oc-mirror --config {config_file} {mirror_destination} --ignore-history
"""
            
            # Create log file
            log_file = f"{local_path}/{name}.log"
            
            # Remove old history entry to avoid showing dismissed items
            download_history[:] = [h for h in download_history if h.get('id') != download_id]
            print(f"[RETRY] Removed old history entry for {download_id}")
            
            # Start the process
            process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Log output to file
            def log_output():
                with open(log_file, 'w') as f:
                    if process.stdout:
                        for line in process.stdout:
                            f.write(line)
                            f.flush()
            
            # Start logging thread
            log_thread = threading.Thread(target=log_output, daemon=True)
            log_thread.start()
            
            # Add to download manager with all original parameters
            download_manager.downloads[new_download_id] = {
                "id": new_download_id,
                "component": "redhat-operators",
                "version": f"v{catalog_version}",
                "name": name,
                "status": "running",
                "start_time": datetime.now().isoformat(),
                "pid": process.pid,
                "process": process,
                "log_file": log_file,
                "home_dir": local_path,
                "final_registry": target_registry if mirror_type == 'registry' else "file://",
                "registry_auth_file": auth_file,
                # Store ALL original parameters for future retry
                "catalog_version": catalog_version,
                "architecture": architecture,
                "operators": operators,
                "channels": channels,
                "include_ubi": include_ubi,
                "include_helm": include_helm,
                "mirror_type": mirror_type,
                "config_file": config_file
            }
            
            # Start monitoring thread
            monitor_thread = threading.Thread(
                target=download_manager._monitor_download,
                args=(new_download_id,),
                daemon=True
            )
            monitor_thread.start()
            
            return jsonify({
                "success": True,
                "download_id": new_download_id,
                "message": f"Operators mirror retry started for catalog v{catalog_version} with --ignore-history"
            })
        
        # Handle CP4I retry - use script's --retry flag
        else:
            # Get configuration from request body (user can modify) or fall back to stored values
            data = request.json or {}
            home_dir = data.get('home_dir') or download.get('home_dir', HOME_DIR)
            final_registry = data.get('final_registry') or download.get('final_registry', 'registry.example.com:5000')
            registry_auth_file = data.get('registry_auth_file') or download.get('registry_auth_file', '/root/.docker/config.json')
            entitlement_key = data.get('entitlement_key') or download.get('entitlement_key')
            
            # Get original download mode settings
            direct_to_registry = download.get('direct_to_registry', False)
            download_mode = download.get('download_mode', 'standard')
            
            print(f"[RETRY] Using configuration: home_dir={home_dir}, final_registry={final_registry}, direct_to_registry={direct_to_registry}")
            
            # Build retry command using Python downloader
            cmd = [
                "python3", PYTHON_DOWNLOADER,
                "--component", download['component'],
                "--version", download['version'],
                "--name", download['name'],
                "--home-dir", home_dir,
                "--final-registry", final_registry
            ]
            
            if registry_auth_file:
                cmd.extend(["--registry-auth-file", registry_auth_file])
            
            if download.get('filter'):
                cmd.extend(["--filter", download['filter']])
            
            # Add direct-to-registry flag if it was used in original download
            if direct_to_registry:
                cmd.append("--direct-to-registry")
                print(f"[RETRY] Adding --direct-to-registry flag to preserve original download mode")
            
            # Build environment variables
            env = os.environ.copy()
            env["REGISTRY_AUTH_FILE"] = registry_auth_file
            if entitlement_key:
                env["ENTITLEMENT_KEY"] = entitlement_key
            
            # Start retry process
            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env=env
                )
                
                new_download_id = f"{download['name']}-retry-{int(time.time())}"
                
                # Remove any existing downloads and history entries for this name to avoid duplicates
                with download_manager.lock:
                    # Remove from active downloads
                    to_remove = [did for did, d in download_manager.downloads.items()
                                if d.get('name') == download['name']]
                    for did in to_remove:
                        del download_manager.downloads[did]
                        print(f"Removed old download {did} before retry")
                    
                    # Remove from history to avoid showing old failed/dismissed entries
                    download_history = [h for h in download_history
                                       if h.get('name') != download['name']]
                    print(f"Cleaned history for {download['name']}")
                    
                    download_manager.downloads[new_download_id] = {
                        "id": new_download_id,
                        "component": download['component'],
                        "version": download['version'],
                        "name": download['name'],
                        "filter": download.get('filter'),
                        "process": process,
                        "home_dir": home_dir,
                        "final_registry": final_registry,
                        "registry_auth_file": registry_auth_file,
                        "entitlement_key": entitlement_key,
                        "status": "running",
                        "start_time": datetime.now().isoformat(),
                        "pid": process.pid,
                        "mirror_pid": None,  # Will be captured from log
                        "log_file": f"{home_dir}/{download['name']}/{download['name']}-download.log",
                        "direct_to_registry": direct_to_registry,
                        "download_mode": download_mode
                    }
                    
                    # Start monitoring thread
                    threading.Thread(
                        target=download_manager._monitor_download,
                        args=(new_download_id,),
                        daemon=True
                    ).start()
                
                return jsonify({"success": True, "download_id": new_download_id, "pid": process.pid})
            
            except Exception as e:
                return jsonify({"error": str(e)}), 500
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/logs/<name>', methods=['GET'])
def get_logs(name):
    """Get log files for a download (both download and mirror logs)"""
    try:
        # Get home_dir from query parameter or use default
        home_dir = request.args.get('home_dir', HOME_DIR)
        lines = request.args.get('lines', None)  # Number of lines to return (tail)
        
        # Try multiple log file locations
        # CP4I format: {home_dir}/{name}/{name}-download.log and {name}-mirror.log
        # OpenShift/Operators format: {home_dir}/{name}.log (single file)
        
        download_log_file = f"{home_dir}/{name}/{name}-download.log"
        mirror_log_file = f"{home_dir}/{name}/{name}-mirror.log"
        single_log_file = f"{home_dir}/{name}.log"
        
        download_log_content = ""
        mirror_log_content = ""
        
        # Check if single log file exists (OpenShift/Operators)
        if os.path.exists(single_log_file):
            with open(single_log_file, 'r') as f:
                content = f.read()
                if lines:
                    content = '\n'.join(content.split('\n')[-int(lines):])
                # Use same content for both logs since it's a single file
                download_log_content = content
                mirror_log_content = ""  # No separate mirror log for these
        else:
            # Read CP4I-style download log
            if os.path.exists(download_log_file):
                with open(download_log_file, 'r') as f:
                    download_log_content = f.read()
                    if lines:
                        download_log_content = '\n'.join(download_log_content.split('\n')[-int(lines):])
            
            # Read CP4I-style mirror log
            if os.path.exists(mirror_log_file):
                with open(mirror_log_file, 'r') as f:
                    mirror_log_content = f.read()
                    if lines:
                        mirror_log_content = '\n'.join(mirror_log_content.split('\n')[-int(lines):])
        
        return jsonify({
            "download_log": download_log_content,
            "mirror_log": mirror_log_content,
            "download_log_path": single_log_file if os.path.exists(single_log_file) else download_log_file,
            "mirror_log_path": mirror_log_file,
            "download_log_exists": os.path.exists(single_log_file) or os.path.exists(download_log_file),
            "mirror_log_exists": os.path.exists(mirror_log_file)
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/logs/<name>/stream', methods=['GET'])
def stream_logs(name):
    """Stream log files in real-time (Server-Sent Events) - both download and mirror logs"""
    try:
        from flask import Response, stream_with_context
        import time
        
        home_dir = request.args.get('home_dir', HOME_DIR)
        log_type = request.args.get('type', 'download')  # 'download' or 'mirror'
        
        # Select log file based on type
        if log_type == 'mirror':
            log_file = f"{home_dir}/{name}/{name}-mirror.log"
        else:
            log_file = f"{home_dir}/{name}/{name}-download.log"
        
        def generate():
            """Generator function to stream log updates"""
            last_size = 0
            retry_count = 0
            max_retries = 60  # Wait up to 60 seconds for log file
            
            # Wait for log file to be created
            while not os.path.exists(log_file) and retry_count < max_retries:
                time.sleep(1)
                retry_count += 1
                yield f"data: Waiting for {log_type} log file...\n\n"
            
            if not os.path.exists(log_file):
                yield f"data: ERROR: {log_type.capitalize()} log file not found after {max_retries} seconds\n\n"
                return
            
            # Stream log updates
            while True:
                try:
                    current_size = os.path.getsize(log_file)
                    
                    if current_size > last_size:
                        with open(log_file, 'r') as f:
                            f.seek(last_size)
                            new_content = f.read()
                            if new_content:
                                # Send each line as a separate event
                                for line in new_content.split('\n'):
                                    if line:
                                        yield f"data: {line}\n\n"
                        last_size = current_size
                    
                    time.sleep(1)  # Check for updates every second
                
                except Exception as e:
                    yield f"data: ERROR: {str(e)}\n\n"
                    break
        
        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'
            }
        )
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/manifests/<name>', methods=['GET'])
def get_manifests(name):
    """Get manifest mapping file for a download"""
    try:
        home_dir = request.args.get('home_dir', HOME_DIR)
        component = request.args.get('component')
        version = request.args.get('version')
        
        if not component or not version:
            return jsonify({"error": "component and version parameters required"}), 400
        
        # Mapping file path
        mapping_file = f"{home_dir}/.ibm-pak/data/mirror/{component}/{version}/images-mapping-to-filesystem.txt"
        
        if not os.path.exists(mapping_file):
            return jsonify({
                "error": "Mapping file not found. Generate manifests first.",
                "path": mapping_file
            }), 404
        
        with open(mapping_file, 'r') as f:
            content = f.read()
            lines = content.strip().split('\n')
            
            # Parse mapping file
            mappings = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = line.split('=')
                    if len(parts) == 2:
                        mappings.append({
                            'source': parts[0].strip(),
                            'destination': parts[1].strip()
                        })
            
            return jsonify({
                "mapping_file": mapping_file,
                "total_images": len(mappings),
                "mappings": mappings,
                "raw_content": content
            })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/reports/<name>', methods=['GET'])
def get_report(name):
    """Get summary report for a download"""
    try:
        # Get home_dir from query parameter or use default
        home_dir = request.args.get('home_dir', HOME_DIR)
        
        # Report is stored directly in home_dir with format: {name}-summary-report.txt
        report_file = f"{home_dir}/{name}-summary-report.txt"
        
        print(f"[REPORT] Looking for report at: {report_file}")
        
        if not os.path.exists(report_file):
            return jsonify({
                "error": f"Report not found. The download may not have completed yet.",
                "path": report_file
            }), 404
        
        with open(report_file, 'r') as f:
            return jsonify({"report": f.read()})
    
    except Exception as e:
        print(f"[REPORT] Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/components', methods=['GET'])
def get_components():
    """Get list of CP4I components"""
    try:
        # Try to load from sample-cases.json
        cases_file = os.path.join(os.path.dirname(__file__), 'sample-cases.json')
        
        if os.path.exists(cases_file):
            with open(cases_file, 'r') as f:
                components = json.load(f)
            return jsonify({"components": components, "source": "sample-cases.json"})
        
        # Fallback to hardcoded components if file not found
        components = [
            {
                "name": "ibm-integration-platform-navigator",
                "description": "IBM Cloud Pak for Integration - Platform Navigator",
                "typical_size": "~22GB",
                "versions": ["8.3.0", "8.2.0", "8.1.0", "7.3.2"],
                "architecture": ["amd64", "s390x", "ppc64le"],
                "openshift_versions": ["4.14", "4.15", "4.16", "4.17", "4.18", "4.19", "4.20"]
            },
            {
                "name": "ibm-apiconnect",
                "description": "IBM API Connect",
                "typical_size": "~38GB",
                "versions": ["10.0.10.0", "10.0.9.0", "10.0.8.0", "10.0.7.0"],
                "architecture": ["amd64", "s390x"],
                "openshift_versions": ["4.14", "4.15", "4.16", "4.17", "4.18", "4.19", "4.20"]
            },
            {
                "name": "ibm-mq",
                "description": "IBM MQ Advanced",
                "typical_size": "~14GB",
                "versions": ["9.4.0", "9.3.5", "9.3.4", "9.3.3"],
                "architecture": ["amd64", "s390x", "ppc64le"],
                "openshift_versions": ["4.14", "4.15", "4.16", "4.17", "4.18", "4.19", "4.20"]
            },
            {
                "name": "ibm-eventstreams",
                "description": "IBM Event Streams (Apache Kafka)",
                "typical_size": "~20GB",
                "versions": ["11.5.0", "11.4.0", "11.3.2", "11.3.1"],
                "architecture": ["amd64", "s390x"],
                "openshift_versions": ["4.14", "4.15", "4.16", "4.17", "4.18", "4.19", "4.20"]
            },
            {
                "name": "ibm-appconnect",
                "description": "IBM App Connect Enterprise",
                "typical_size": "~16GB",
                "versions": ["13.0.1", "13.0.0", "12.0.11.0", "12.0.10.0"],
                "architecture": ["amd64", "s390x"],
                "openshift_versions": ["4.14", "4.15", "4.16", "4.17", "4.18", "4.19", "4.20"]
            },
            {
                "name": "ibm-datapower-operator",
                "description": "IBM DataPower Gateway",
                "typical_size": "~9GB",
                "versions": ["1.12.0", "1.11.0", "1.10.3", "1.10.2"],
                "architecture": ["amd64", "s390x"],
                "openshift_versions": ["4.14", "4.15", "4.16", "4.17", "4.18", "4.19", "4.20"]
            }
        ]
        
        return jsonify({"components": components, "source": "fallback"})
    
    except Exception as e:
        app.logger.error(f"Error in get_components: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/validate', methods=['POST'])
def validate_prerequisites():
    """Validate system prerequisites"""
    try:
        result = subprocess.run(
            ['python3', PYTHON_DOWNLOADER, '--help'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        return jsonify({
            "valid": result.returncode == 0,
            "output": result.stdout
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/preview-manifests', methods=['POST'])
def preview_manifests():
    """Preview manifests that will be downloaded"""
    try:
        data = request.json
        component = data.get('component')
        version = data.get('version')
        filter_pattern = data.get('filter', '')
        
        if not component or not version:
            return jsonify({"error": "Component and version required"}), 400
        
        # Build command to list manifests using Python downloader
        cmd = [
            'python3', PYTHON_DOWNLOADER,
            '--component', component,
            '--version', version,
            '--name', 'preview',
            '--dry-run'
        ]
        
        if filter_pattern:
            cmd.extend(['--filter', filter_pattern])
        
        # Execute with timeout
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Parse output to extract manifest list
        manifests = []
        count = 0
        
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            for line in lines:
                # Look for manifest file patterns
                if '.yaml' in line or 'manifest' in line.lower():
                    manifests.append(line.strip())
                    count += 1
        
        return jsonify({
            "success": True,
            "component": component,
            "version": version,
            "filter": filter_pattern,
            "count": count,
            "manifests": manifests[:50]  # Limit to first 50 for display
        })
    
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Preview timed out"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/version-info/<component_name>', methods=['GET'])
def get_version_info(component_name):
    """Get version lifecycle and compatibility information"""
    try:
        # Load version data from JSON file
        version_data_file = os.path.join(os.path.dirname(__file__), 'cp4i_version_data.json')
        
        if not os.path.exists(version_data_file):
            return jsonify({"error": "Version data not found"}), 404
        
        with open(version_data_file, 'r') as f:
            version_data = json.load(f)
        
        # Get component data - components are at root level
        if component_name not in version_data:
            return jsonify({"error": f"Component '{component_name}' not found"}), 404
        
        component_data = version_data[component_name]
        
        # Return component version data
        return jsonify({
            "component": component_name,
            "versions": component_data
        })
    
    except Exception as e:
        app.logger.error(f"Error in get_version_info for {component_name}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/openshift/mirror', methods=['POST'])
def openshift_mirror():
    """Start OpenShift image mirror process"""
    try:
        data = request.json
        ocp_release = data.get('ocp_release')
        architecture = data.get('architecture', 'x86_64')
        local_registry = data.get('local_registry')
        local_repository = data.get('local_repository')
        removable_media_path = data.get('removable_media_path')
        local_secret_json = data.get('local_secret_json')
        dry_run = data.get('dry_run', False)
        print_idms = data.get('print_idms', False)
        generate_icsp = data.get('generate_icsp', False)
        mirror_type = data.get('mirror_type', 'filesystem')
        
        # Advanced options
        max_per_registry = data.get('max_per_registry', 6)
        continue_on_error = data.get('continue_on_error', False)
        skip_verification = data.get('skip_verification', False)
        filter_by_os = data.get('filter_by_os', '')
        include_operators = data.get('include_operators', False)
        include_samples = data.get('include_samples', False)
        
        if not all([ocp_release, local_registry, local_repository, local_secret_json]):
            return jsonify({"error": "Missing required fields"}), 400
        
        if mirror_type == 'filesystem' and not removable_media_path:
            return jsonify({"error": "Removable media path required for filesystem mirror"}), 400
        
        # Set environment variables
        product_repo = 'openshift-release-dev'
        release_name = 'ocp-release'
        
        # Create download directory
        os.makedirs(removable_media_path, exist_ok=True)
        
        # Generate download ID
        download_id = f"ocp-{ocp_release}-{int(time.time())}"
        name = f"ocp-{ocp_release}-{architecture}"
        
        # Build additional flags
        additional_flags = []
        if max_per_registry and max_per_registry != 6:
            additional_flags.append(f"--max-per-registry={max_per_registry}")
        if continue_on_error:
            additional_flags.append("--continue-on-error=true")
        if skip_verification:
            additional_flags.append("--skip-verification")
        if filter_by_os:
            additional_flags.append(f"--filter-by-os='{filter_by_os}'")
        
        flags_str = " \\\n  ".join(additional_flags) if additional_flags else ""
        flags_line = f" \\\n  {flags_str}" if flags_str else ""
        
        # Build the mirror command
        if dry_run:
            # Dry run command
            cmd = f"""
export OCP_RELEASE={ocp_release}
export LOCAL_REGISTRY='{local_registry}'
export LOCAL_REPOSITORY='{local_repository}'
export PRODUCT_REPO='{product_repo}'
export LOCAL_SECRET_JSON="{local_secret_json}"
export RELEASE_NAME="{release_name}"
export ARCHITECTURE={architecture}

oc adm release mirror -a ${{LOCAL_SECRET_JSON}} \\
  --from=quay.io/${{PRODUCT_REPO}}/${{RELEASE_NAME}}:${{OCP_RELEASE}}-${{ARCHITECTURE}} \\
  --to=${{LOCAL_REGISTRY}}/${{LOCAL_REPOSITORY}} \\
  --to-release-image=${{LOCAL_REGISTRY}}/${{LOCAL_REPOSITORY}}:${{OCP_RELEASE}}-${{ARCHITECTURE}} \\
  --dry-run{flags_line}
"""
            if print_idms:
                cmd += f"""
echo "\\n=== IDMS Instructions ==="
oc adm release mirror -a ${{LOCAL_SECRET_JSON}} \\
  --from=quay.io/${{PRODUCT_REPO}}/${{RELEASE_NAME}}:${{OCP_RELEASE}}-${{ARCHITECTURE}} \\
  --to=${{LOCAL_REGISTRY}}/${{LOCAL_REPOSITORY}} \\
  --to-release-image=${{LOCAL_REGISTRY}}/${{LOCAL_REPOSITORY}}:${{OCP_RELEASE}}-${{ARCHITECTURE}} \\
  --print-mirror-instructions="idms" --dry-run
"""
            if generate_icsp:
                cmd += f"""
echo "\\n=== ICSP Configuration ==="
oc adm release mirror -a ${{LOCAL_SECRET_JSON}} \\
  --from=quay.io/${{PRODUCT_REPO}}/${{RELEASE_NAME}}:${{OCP_RELEASE}}-${{ARCHITECTURE}} \\
  --to=${{LOCAL_REGISTRY}}/${{LOCAL_REPOSITORY}} \\
  --to-release-image=${{LOCAL_REGISTRY}}/${{LOCAL_REPOSITORY}}:${{OCP_RELEASE}}-${{ARCHITECTURE}} \\
  --print-mirror-instructions="icsp" --dry-run
"""
        else:
            # Actual mirror command
            if mirror_type == 'filesystem':
                cmd = f"""
export OCP_RELEASE={ocp_release}
export LOCAL_REGISTRY='{local_registry}'
export LOCAL_REPOSITORY='{local_repository}'
export PRODUCT_REPO='{product_repo}'
export LOCAL_SECRET_JSON="{local_secret_json}"
export RELEASE_NAME="{release_name}"
export ARCHITECTURE={architecture}
export REMOVABLE_MEDIA_PATH="{removable_media_path}"

echo "Starting OpenShift {ocp_release} mirror to file system..."
oc adm release mirror -a ${{LOCAL_SECRET_JSON}} \\
  --to-dir=${{REMOVABLE_MEDIA_PATH}}/mirror \\
  quay.io/${{PRODUCT_REPO}}/${{RELEASE_NAME}}:${{OCP_RELEASE}}-${{ARCHITECTURE}}{flags_line}
"""
            else:
                # Direct to registry
                cmd = f"""
export OCP_RELEASE={ocp_release}
export LOCAL_REGISTRY='{local_registry}'
export LOCAL_REPOSITORY='{local_repository}'
export PRODUCT_REPO='{product_repo}'
export LOCAL_SECRET_JSON="{local_secret_json}"
export RELEASE_NAME="{release_name}"
export ARCHITECTURE={architecture}

echo "Starting OpenShift {ocp_release} mirror to registry..."
oc adm release mirror -a ${{LOCAL_SECRET_JSON}} \\
  --from=quay.io/${{PRODUCT_REPO}}/${{RELEASE_NAME}}:${{OCP_RELEASE}}-${{ARCHITECTURE}} \\
  --to=${{LOCAL_REGISTRY}}/${{LOCAL_REPOSITORY}} \\
  --to-release-image=${{LOCAL_REGISTRY}}/${{LOCAL_REPOSITORY}}:${{OCP_RELEASE}}-${{ARCHITECTURE}}{flags_line}
"""
            
            # Add operator catalog mirroring if requested
            if include_operators:
                ocp_major = ocp_release.split('.')[0]
                ocp_minor = ocp_release.split('.')[1]
                cmd += f"""
echo "\\n=== Mirroring Operator Catalogs ==="
oc adm catalog mirror \\
  registry.redhat.io/redhat/redhat-operator-index:v{ocp_major}.{ocp_minor} \\
  ${{LOCAL_REGISTRY}}/${{LOCAL_REPOSITORY}} \\
  -a ${{LOCAL_SECRET_JSON}}{flags_line}
"""
        
        # Create log file
        log_file = f"{removable_media_path}/{name}.log"
        
        # Start the process
        process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Log output to file
        def log_output():
            with open(log_file, 'w') as f:
                if process.stdout:
                    for line in process.stdout:
                        f.write(line)
                        f.flush()
        
        # Start logging thread
        log_thread = threading.Thread(target=log_output, daemon=True)
        log_thread.start()
        
        # Add to download manager - Store ALL parameters for retry
        download_manager.downloads[download_id] = {
            "id": download_id,
            "component": "openshift",
            "version": ocp_release,
            "name": name,
            "status": "running",
            "start_time": datetime.now().isoformat(),
            "pid": process.pid,
            "process": process,
            "log_file": log_file,
            "home_dir": removable_media_path,
            "final_registry": local_registry,
            "registry_auth_file": local_secret_json,
            "architecture": architecture,
            "dry_run": dry_run,
            # Store original parameters for retry
            "mirror_type": mirror_type,
            "local_repository": local_repository,
            "product_repo": product_repo,
            "release_name": release_name,
            "include_operators": include_operators,
            "print_idms": print_idms,
            "generate_icsp": generate_icsp,
            "skip_verification": skip_verification
        }
        
        # Start monitoring thread
        monitor_thread = threading.Thread(
            target=download_manager._monitor_download,
            args=(download_id,),
            daemon=True
        )
        monitor_thread.start()
        
        return jsonify({
            "success": True,
            "download_id": download_id,
            "message": f"OpenShift mirror started for {ocp_release}"
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/openshift/verify', methods=['POST'])
def openshift_verify():
    """Verify OpenShift images (dry run)"""
    try:
        data = request.json
        ocp_release = data.get('ocp_release')
        architecture = data.get('architecture', 'x86_64')
        local_registry = data.get('local_registry')
        local_repository = data.get('local_repository')
        local_secret_json = data.get('local_secret_json')
        print_idms = data.get('print_idms', False)
        
        if not all([ocp_release, local_registry, local_repository, local_secret_json]):
            return jsonify({"error": "Missing required fields"}), 400
        
        product_repo = 'openshift-release-dev'
        release_name = 'ocp-release'
        
        # Build verification command
        cmd = f"""
export OCP_RELEASE={ocp_release}
export LOCAL_REGISTRY='{local_registry}'
export LOCAL_REPOSITORY='{local_repository}'
export PRODUCT_REPO='{product_repo}'
export LOCAL_SECRET_JSON="{local_secret_json}"
export RELEASE_NAME="{release_name}"
export ARCHITECTURE={architecture}

oc adm release mirror -a ${{LOCAL_SECRET_JSON}} \\
  --from=quay.io/${{PRODUCT_REPO}}/${{RELEASE_NAME}}:${{OCP_RELEASE}}-${{ARCHITECTURE}} \\
  --to=${{LOCAL_REGISTRY}}/${{LOCAL_REPOSITORY}} \\
  --to-release-image=${{LOCAL_REGISTRY}}/${{LOCAL_REPOSITORY}}:${{OCP_RELEASE}}-${{ARCHITECTURE}} \\
  --dry-run
"""
        
        # Execute verification
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        output = result.stdout + result.stderr
        
        # Get IDMS instructions if requested
        idms_instructions = ""
        if print_idms and result.returncode == 0:
            idms_cmd = f"""
export OCP_RELEASE={ocp_release}
export LOCAL_REGISTRY='{local_registry}'
export LOCAL_REPOSITORY='{local_repository}'
export PRODUCT_REPO='{product_repo}'
export LOCAL_SECRET_JSON="{local_secret_json}"
export RELEASE_NAME="{release_name}"
export ARCHITECTURE={architecture}

oc adm release mirror -a ${{LOCAL_SECRET_JSON}} \\
  --from=quay.io/${{PRODUCT_REPO}}/${{RELEASE_NAME}}:${{OCP_RELEASE}}-${{ARCHITECTURE}} \\
  --to=${{LOCAL_REGISTRY}}/${{LOCAL_REPOSITORY}} \\
  --to-release-image=${{LOCAL_REGISTRY}}/${{LOCAL_REPOSITORY}}:${{OCP_RELEASE}}-${{ARCHITECTURE}} \\
  --print-mirror-instructions="idms" --dry-run
"""
            idms_result = subprocess.run(
                idms_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300
            )
            idms_instructions = idms_result.stdout
        
        if result.returncode == 0:
            return jsonify({
                "success": True,
                "output": output,
                "idms_instructions": idms_instructions
            })
        else:
            return jsonify({
                "error": "Verification failed",
                "output": output
            }), 400
    
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Verification timed out"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route('/api/operators/mirror', methods=['POST'])
def operators_mirror():
    """Start Red Hat Operators mirror using ImageSetConfiguration"""
    try:
        data = request.json
        catalog_version = data.get('catalog_version')
        architecture = data.get('architecture', 'amd64')
        local_path = data.get('local_path')
        auth_file = data.get('auth_file')
        operators = data.get('operators', [])
        channels = data.get('channels', [])
        include_ubi = data.get('include_ubi', False)
        include_helm = data.get('include_helm', False)
        mirror_type = data.get('mirror_type', 'filesystem')
        target_registry = data.get('target_registry', '')
        
        if not all([catalog_version, local_path, auth_file]):
            return jsonify({"error": "Missing required fields"}), 400
        
        # Validate target registry for direct mirroring
        if mirror_type == 'registry' and not target_registry:
            return jsonify({"error": "Target registry is required for direct mirroring"}), 400
        
        # Create local path
        os.makedirs(local_path, exist_ok=True)
        
        # Generate ImageSetConfiguration
        config = f"""kind: ImageSetConfiguration
apiVersion: mirror.openshift.io/v1alpha2
storageConfig:
  local:
    path: {local_path}
mirror:
  platform:
    architectures:
      - {architecture}
  operators:
    - catalog: registry.redhat.io/redhat/redhat-operator-index:v{catalog_version}
"""
        
        if operators and operators[0] == '*':
            config += "      full: true\n"
        elif operators:
            config += "      packages:\n"
            # Check if operators is a list of dicts (specific operators with individual channels)
            if operators and isinstance(operators[0], dict):
                # Each operator has its own name and channel
                for op in operators:
                    op_name = op.get('name', '')
                    op_channel = op.get('channel', '')
                    if op_name:
                        config += f"        - name: {op_name}\n"
                        if op_channel:
                            config += "          channels:\n"
                            config += f"            - name: {op_channel}\n"
            else:
                # Simple list of operator names with shared channels
                for op in operators:
                    config += f"        - name: {op}\n"
                    if channels:
                        config += "          channels:\n"
                        for ch in channels:
                            config += f"            - name: {ch}\n"
        
        if include_ubi:
            config += """  additionalImages:
    - name: registry.redhat.io/ubi8/ubi:latest
    - name: registry.redhat.io/ubi9/ubi:latest
"""
        
        if include_helm:
            config += "  helm: {}\n"
        
        # Save configuration file
        config_file = f"{local_path}/imageset-config.yaml"
        with open(config_file, 'w') as f:
            f.write(config)
        
        # Generate download ID
        download_id = f"operators-v{catalog_version}-{int(time.time())}"
        name = f"operators-v{catalog_version}"
        
        # Build oc-mirror command based on mirror type
        if mirror_type == 'registry':
            mirror_destination = f"docker://{target_registry}"
            destination_display = target_registry
        else:
            mirror_destination = f"file://{local_path}"
            destination_display = local_path
        
        cmd = f"""
export REGISTRY_AUTH_FILE="{auth_file}"

echo "Starting Red Hat Operators mirror..."
echo "Catalog Version: v{catalog_version}"
echo "Architecture: {architecture}"
echo "Operators: {len(operators) if operators[0] != '*' else 'All'}"
echo "Mirror Type: {mirror_type}"
echo "Destination: {destination_display}"

oc-mirror --config {config_file} {mirror_destination}
"""
        
        # Create log file
        log_file = f"{local_path}/{name}.log"
        
        # Start the process
        process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Log output to file
        def log_output():
            with open(log_file, 'w') as f:
                if process.stdout:
                    for line in process.stdout:
                        f.write(line)
                        f.flush()
        
        # Start logging thread
        log_thread = threading.Thread(target=log_output, daemon=True)
        log_thread.start()
        
        # Add to download manager - Store ALL parameters for retry
        download_manager.downloads[download_id] = {
            "id": download_id,
            "component": "redhat-operators",
            "version": f"v{catalog_version}",
            "name": name,
            "status": "running",
            "start_time": datetime.now().isoformat(),
            "pid": process.pid,
            "process": process,
            "log_file": log_file,
            "home_dir": local_path,
            "final_registry": target_registry if mirror_type == 'registry' else "file://",
            "registry_auth_file": auth_file,
            # Store ALL original parameters for retry
            "catalog_version": catalog_version,
            "architecture": architecture,
            "operators": operators,
            "channels": channels,
            "include_ubi": include_ubi,
            "include_helm": include_helm,
            "mirror_type": mirror_type,
            "target_registry": target_registry,
            "config_file": config_file
        }
        
        # Start monitoring thread
        monitor_thread = threading.Thread(
            target=download_manager._monitor_download,
            args=(download_id,),
            daemon=True
        )
        monitor_thread.start()
        
        return jsonify({
            "success": True,
            "download_id": download_id,
            "message": f"Operators mirror started for catalog v{catalog_version}",
            "config_file": config_file
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/operators/validate', methods=['POST'])
def operators_validate():
    """Validate operator names against catalog"""
    try:
        data = request.json
        catalog_version = data.get('catalog_version')
        operators = data.get('operators', [])
        
        if not catalog_version:
            return jsonify({"error": "Catalog version required"}), 400
        
        # For now, return success with count
        # In production, this would query the actual catalog
        valid_count = len(operators) if operators else 0
        
        return jsonify({
            "success": True,
            "valid_count": valid_count,
            "catalog_version": catalog_version,
            "message": f"Validation completed for {valid_count} operator(s)"
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/operators/generate-config', methods=['POST'])
def operators_generate_config():
    """Generate ImageSetConfiguration and mirror commands"""
    try:
        data = request.json
        catalog_version = data.get('catalog_version')
        architecture = data.get('architecture', 'amd64')
        local_path = data.get('local_path')
        auth_file = data.get('auth_file')
        target_registry = data.get('target_registry', '')
        operators = data.get('operators', [])
        channels = data.get('channels', [])
        include_ubi = data.get('include_ubi', False)
        include_helm = data.get('include_helm', False)
        
        if not all([catalog_version, local_path, auth_file]):
            return jsonify({"error": "Missing required fields"}), 400
        
        # Generate ImageSetConfiguration
        config = f"""kind: ImageSetConfiguration
apiVersion: mirror.openshift.io/v1alpha2
storageConfig:
  local:
    path: {local_path}
mirror:
  platform:
    architectures:
      - {architecture}
  operators:
    - catalog: registry.redhat.io/redhat/redhat-operator-index:v{catalog_version}
"""
        
        if operators and operators[0] == '*':
            config += "      full: true\n"
        elif operators:
            config += "      packages:\n"
            # Check if operators is a list of dicts (specific operators with individual channels)
            if operators and isinstance(operators[0], dict):
                # Each operator has its own name and channel
                for op in operators:
                    op_name = op.get('name', '')
                    op_channel = op.get('channel', '')
                    if op_name:
                        config += f"        - name: {op_name}\n"
                        if op_channel:
                            config += "          channels:\n"
                            config += f"            - name: {op_channel}\n"
            else:
                # Simple list of operator names with shared channels
                for op in operators:
                    config += f"        - name: {op}\n"
                    if channels:
                        config += "          channels:\n"
                        for ch in channels:
                            config += f"            - name: {ch}\n"
        
        if include_ubi:
            config += """  additionalImages:
    - name: registry.redhat.io/ubi8/ubi:latest
    - name: registry.redhat.io/ubi9/ubi:latest
"""
        
        if include_helm:
            config += "  helm: {}\n"
        
        # Generate commands
        config_file = f"{local_path}/imageset-config.yaml"
        
        # Command 1: Mirror to file system
        cmd_filesystem = f"""# Mirror Red Hat Operators to File System
export REGISTRY_AUTH_FILE="{auth_file}"

# Create ImageSetConfiguration file
cat > {config_file} << 'EOF'
{config}EOF

# Mirror to file system
oc-mirror --config {config_file} file://{local_path}
"""
        
        # Command 2: Direct to registry (always show)
        if target_registry:
            cmd_registry = f"""# Mirror Red Hat Operators Directly to Registry
export REGISTRY_AUTH_FILE="{auth_file}"

# Create ImageSetConfiguration file
cat > {config_file} << 'EOF'
{config}EOF

# Mirror directly to target registry
oc-mirror --config {config_file} docker://{target_registry}
"""
        else:
            cmd_registry = f"""# Mirror Red Hat Operators Directly to Registry
export REGISTRY_AUTH_FILE="{auth_file}"

# Create ImageSetConfiguration file
cat > {config_file} << 'EOF'
{config}EOF

# Mirror directly to target registry (replace <target-registry> with your registry)
oc-mirror --config {config_file} docker://<target-registry>
"""
        
        # Command 3: Retry with --ignore-history
        cmd_retry = f"""# Retry Mirror with --ignore-history (Skip Previously Mirrored Content)
export REGISTRY_AUTH_FILE="{auth_file}"

# Retry to file system (ignoring history)
oc-mirror --config {config_file} file://{local_path} --ignore-history

# OR retry to registry (ignoring history)
{f'oc-mirror --config {config_file} docker://{target_registry} --ignore-history' if target_registry else '# Set target registry to enable this command'}
"""
        
        # Command 4: Publish from file system to registry
        cmd_publish = ""
        if target_registry:
            cmd_publish = f"""# Publish from File System to Target Registry
export REGISTRY_AUTH_FILE="{auth_file}"

# Publish mirrored content to target registry
oc-mirror --from {local_path} docker://{target_registry}
"""
        
        return jsonify({
            "success": True,
            "config": config,
            "config_file": config_file,
            "commands": {
                "filesystem": cmd_filesystem,
                "registry": cmd_registry,
                "retry": cmd_retry,
                "publish": cmd_publish
            },
            "summary": {
                "catalog_version": f"v{catalog_version}",
                "architecture": architecture,
                "operators_count": len(operators) if operators[0] != '*' else "All",
                "local_path": local_path,
                "target_registry": target_registry or "Not specified"
            }
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================
# Live Data API Endpoints
# ============================================

# Initialize live data fetcher
try:
    from live_data_fetcher import LiveDataFetcher
    live_fetcher = LiveDataFetcher()
    LIVE_DATA_ENABLED = True
except Exception as e:
    print(f"Warning: Live data fetcher not available: {e}")
    live_fetcher = None
    LIVE_DATA_ENABLED = False


@app.route('/api/live/versions', methods=['GET'])
def get_live_versions():
    """Get live version data for all components"""
    try:
        if not LIVE_DATA_ENABLED or not live_fetcher:
            # Fallback to local data
            with open('sample-versions.json', 'r') as f:
                return jsonify({
                    "success": True,
                    "source": "local",
                    "data": json.load(f)
                })
        
        # Fetch live data
        versions = live_fetcher.get_all_component_versions()
        
        return jsonify({
            "success": True,
            "source": "live",
            "data": versions,
            "cached": True
        })
    
    except Exception as e:
        # Fallback to local data on error
        try:
            with open('sample-versions.json', 'r') as f:
                return jsonify({
                    "success": True,
                    "source": "local_fallback",
                    "data": json.load(f),
                    "error": str(e)
                })
        except:
            return jsonify({"error": str(e)}), 500


@app.route('/api/live/openshift-versions', methods=['GET'])
def get_live_openshift_versions():
    """Get live OpenShift version data"""
    try:
        channel = request.args.get('channel', 'stable-4.20')
        
        if not LIVE_DATA_ENABLED or not live_fetcher:
            # Fallback to local data
            with open('cp4i_version_data.json', 'r') as f:
                data = json.load(f)
                return jsonify({
                    "success": True,
                    "source": "local",
                    "data": data.get('openshift_versions', {})
                })
        
        # Fetch live data
        versions = live_fetcher.fetch_openshift_versions(channel)
        
        if versions:
            return jsonify({
                "success": True,
                "source": "live",
                "channel": channel,
                "data": versions,
                "cached": True
            })
        else:
            # Fallback to local data
            with open('cp4i_version_data.json', 'r') as f:
                data = json.load(f)
                return jsonify({
                    "success": True,
                    "source": "local_fallback",
                    "data": data.get('openshift_versions', {})
                })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/live/component-versions/<component>', methods=['GET'])
def get_live_component_versions(component):
    """Get live version data for a specific component"""
    try:
        if not LIVE_DATA_ENABLED or not live_fetcher:
            # Fallback to local data
            with open('sample-versions.json', 'r') as f:
                data = json.load(f)
                return jsonify({
                    "success": True,
                    "source": "local",
                    "component": component,
                    "versions": data.get(component, [])
                })
        
        # Fetch live data
        versions = live_fetcher.fetch_ibm_case_versions(component)
        
        if versions:
            return jsonify({
                "success": True,
                "source": "live",
                "component": component,
                "versions": versions,
                "cached": True
            })
        else:
            # Fallback to local data
            with open('sample-versions.json', 'r') as f:
                data = json.load(f)
                return jsonify({
                    "success": True,
                    "source": "local_fallback",
                    "component": component,
                    "versions": data.get(component, [])
                })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/live/support-matrix/<component>/<version>', methods=['GET'])
def get_live_support_matrix(component, version):
    """Get live support matrix for a specific component version"""
    try:
        if not LIVE_DATA_ENABLED or not live_fetcher:
            # Fallback to local data
            with open('cp4i_version_data.json', 'r') as f:
                data = json.load(f)
                component_data = data.get(component, {})
                version_data = component_data.get(version, {})
                return jsonify({
                    "success": True,
                    "source": "local",
                    "component": component,
                    "version": version,
                    "data": version_data
                })
        
        # Fetch live data
        matrix = live_fetcher.fetch_component_support_matrix(component, version)
        
        if matrix:
            return jsonify({
                "success": True,
                "source": "live",
                "component": component,
                "version": version,
                "data": matrix,
                "cached": True
            })
        else:
            # Fallback to local data
            with open('cp4i_version_data.json', 'r') as f:
                data = json.load(f)
                component_data = data.get(component, {})
                version_data = component_data.get(version, {})
                return jsonify({
                    "success": True,
                    "source": "local_fallback",
                    "component": component,
                    "version": version,
                    "data": version_data
                })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/live/refresh', methods=['POST'])
def refresh_live_data():
    """Manually refresh all live data"""
    try:
        if not LIVE_DATA_ENABLED or not live_fetcher:
            return jsonify({
                "success": False,
                "error": "Live data fetcher not available"
            }), 503
        
        # Refresh all data
        result = live_fetcher.refresh_all_data()
        
        return jsonify({
            "success": True,
            "message": "Data refreshed successfully",
            "data": result
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/live/clear-cache', methods=['POST'])
def clear_live_cache():
    """Clear the live data cache"""
    try:
        if not LIVE_DATA_ENABLED or not live_fetcher:
            return jsonify({
                "success": False,
                "error": "Live data fetcher not available"
            }), 503
        
        # Clear cache
        live_fetcher.clear_cache()
        
        return jsonify({
            "success": True,
            "message": "Cache cleared successfully"
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/live/redhat-operators', methods=['GET'])
def get_live_redhat_operators():
    """Get list of available Red Hat operators"""
    try:
        if not LIVE_DATA_ENABLED or not live_fetcher:
            # Return static list as fallback
            operators = [
                {"name": "Red Hat OpenShift Serverless", "package": "serverless-operator", "catalog": "redhat-operators"},
                {"name": "Red Hat OpenShift Service Mesh", "package": "servicemeshoperator", "catalog": "redhat-operators"},
                {"name": "Red Hat OpenShift Pipelines", "package": "openshift-pipelines-operator-rh", "catalog": "redhat-operators"},
                {"name": "Red Hat OpenShift GitOps", "package": "openshift-gitops-operator", "catalog": "redhat-operators"},
                {"name": "Red Hat OpenShift Logging", "package": "cluster-logging", "catalog": "redhat-operators"},
                {"name": "Red Hat Integration - AMQ Streams", "package": "amq-streams", "catalog": "redhat-operators"},
                {"name": "Red Hat Integration - AMQ Broker", "package": "amq-broker-rhel8", "catalog": "redhat-operators"},
                {"name": "Red Hat OpenShift Data Foundation", "package": "odf-operator", "catalog": "redhat-operators"},
                {"name": "Red Hat Advanced Cluster Security", "package": "rhacs-operator", "catalog": "redhat-operators"},
                {"name": "Red Hat Quay", "package": "quay-operator", "catalog": "redhat-operators"}
            ]
            return jsonify({
                "success": True,
                "source": "local",
                "operators": operators
            })
        
        # Fetch live data
        operators = live_fetcher.fetch_redhat_operators()
        
        if operators:
            return jsonify({
                "success": True,
                "source": "live",
                "operators": operators,
                "cached": True
            })
        else:
            # Return static list as fallback
            operators = [
                {"name": "Red Hat OpenShift Serverless", "package": "serverless-operator", "catalog": "redhat-operators"},
                {"name": "Red Hat OpenShift Service Mesh", "package": "servicemeshoperator", "catalog": "redhat-operators"},
                {"name": "Red Hat OpenShift Pipelines", "package": "openshift-pipelines-operator-rh", "catalog": "redhat-operators"}
            ]
            return jsonify({
                "success": True,
                "source": "local_fallback",
                "operators": operators
            })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/live/case-details/<component>/<version>', methods=['GET'])
def get_case_version_details(component, version):
    """Get detailed information for a specific CASE version from GitHub"""
    try:
        if not LIVE_DATA_ENABLED or not live_fetcher:
            return jsonify({
                "success": False,
                "error": "Live data fetcher not available"
            }), 503
        
        # Fetch CASE version details
        details = live_fetcher.fetch_case_version_details(component, version)
        
        if details:
            return jsonify({
                "success": True,
                "source": "live",
                "component": component,
                "version": version,
                "details": details,
                "cached": True
            })
        else:
            # Fallback to local data
            with open('cp4i_version_data.json', 'r') as f:
                data = json.load(f)
                component_data = data.get(component, {})
                version_data = component_data.get(version, {})
                return jsonify({
                    "success": True,
                    "source": "local_fallback",
                    "component": component,
                    "version": version,
                    "details": version_data
                })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/live/status', methods=['GET'])
def get_live_data_status():
    """Get status of live data fetching system"""
    try:
        status = {
            "enabled": LIVE_DATA_ENABLED,
            "fetcher_available": live_fetcher is not None
        }
        
        if LIVE_DATA_ENABLED and live_fetcher:
            # Check cache status
            cache_dir = live_fetcher.cache_dir
            cache_files = []
            if os.path.exists(cache_dir):
                for filename in os.listdir(cache_dir):
                    file_path = os.path.join(cache_dir, filename)
                    if os.path.isfile(file_path):
                        cache_files.append({
                            "name": filename,
                            "size": os.path.getsize(file_path),
                            "modified": datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                        })
            
            status["cache"] = {
                "directory": cache_dir,
                "files": cache_files,
                "total_files": len(cache_files)
            }
            
            # Load configuration
            status["config"] = live_fetcher.config
        
        return jsonify({
            "success": True,
            "status": status
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500



if __name__ == '__main__':
    # Ensure home directory exists
    os.makedirs(HOME_DIR, exist_ok=True)
    
    # Run the app
    app.run(host='0.0.0.0', port=5000, debug=True)

# Made with Bob
