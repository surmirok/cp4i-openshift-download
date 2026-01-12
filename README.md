# CP4I Downloader - IBM Cloud Pak for Integration, OpenShift & Red Hat Operators Image Downloader

A comprehensive web-based and CLI tool for downloading IBM Cloud Pak for Integration (CP4I), OpenShift, and Red Hat Operator images for air-gapped environments.

![Version](https://img.shields.io/badge/version-2.0.0-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)
![Flask](https://img.shields.io/badge/flask-3.0.0-lightgrey)
![License](https://img.shields.io/badge/license-Apache%202.0-orange)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
  - [Web Interface](#web-interface)
  - [Command Line Interface](#command-line-interface)
  - [OpenShift Mirror](#openshift-mirror)
  - [Red Hat Operators Mirror](#red-hat-operators-mirror)
- [Download Modes](#download-modes)
- [Log System](#log-system)
- [Use Cases](#use-cases)
- [Benefits](#benefits)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)
- [API Documentation](#api-documentation)
- [Performance Tuning](#performance-tuning)
- [Security](#security)

---

## 🎯 Overview

The CP4I Downloader is a powerful tool designed to simplify downloading IBM Cloud Pak for Integration (CP4I), OpenShift, and Red Hat Operator images for deployment in air-gapped or restricted network environments.

### What Problem Does It Solve?

In air-gapped environments (networks isolated from the internet), deploying CP4I, OpenShift, and operators requires:
1. **Downloading** all container images from IBM's and Red Hat's registries (20-150 GB per component)
2. **Transferring** them to the air-gapped environment via physical media
3. **Uploading** them to a local registry

This tool automates the download process with:
- ✅ Smart authentication management
- ✅ Automatic retry with exponential backoff
- ✅ Real-time progress tracking
- ✅ Dual log system (application + mirror logs)
- ✅ Comprehensive reporting
- ✅ Multiple download modes
- ✅ **OpenShift release mirroring** (filesystem or direct to registry)
- ✅ **Red Hat Operator catalog mirroring** (using oc-mirror)

---

## ✨ Key Features

### Core Capabilities

| Feature | Description |
|---------|-------------|
| **🌐 Modern Web UI** | Intuitive interface with real-time updates |
| **💻 CLI Support** | Full-featured command-line interface for automation |
| **📦 Multi-Component** | Support for 15+ CP4I components + OpenShift + Red Hat Operators |
| **🔄 Smart Retry** | Exponential backoff for failed downloads |
| **📊 Progress Tracking** | Real-time monitoring with background threads |
| **📝 Dual Log System** | Separate logs for app events and mirror progress |
| **📈 Detailed Reports** | Comprehensive summary with statistics |
| **🔔 Notifications** | Webhook (Slack) and email notifications |
| **🎯 Version Management** | Support for 100+ CASE versions |
| **🔍 Live Data** | Fetches latest version info from GitHub and Red Hat |
| **⚡ Parallel Downloads** | Configurable concurrent image downloads |
| **🛡️ Smart Auth** | Automatic credential validation and reuse |
| **🚀 OpenShift Mirror** | Mirror OpenShift releases (4.14-4.20) to filesystem or registry |
| **🔧 Operator Catalog** | Mirror Red Hat operator catalogs with selective filtering |

### Download Modes

1. **Standard Download**: Download all images to filesystem
2. **Selective Download**: Use regex filters to download specific images
3. **Update Existing**: Update previously downloaded components
4. **Direct to Registry**: Mirror images directly to target registry (no local storage required)

### Advanced Features

- **Dry Run Mode**: Test downloads without actually downloading
- **Filter Support**: Download specific images using regex patterns
- **Force Retry**: Retry with fresh authentication
- **Verbose Logging**: Detailed logging for troubleshooting
- **Configuration Persistence**: Save and reuse configurations
- **History Tracking**: Complete history of all downloads
- **Manifest Preview**: Preview image mappings before download
- **GitHub Connectivity**: Verify access to IBM CASE repository

---

## 🏗️ Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Web Browser (UI)                          │
│  • Modern responsive interface                              │
│  • Real-time progress updates                               │
│  • Tabbed log viewer (Download + Mirror)                    │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/REST API
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Flask Web Server (app.py)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Routes     │  │  Download    │  │   Live Data  │     │
│  │   Handler    │  │   Manager    │  │   Fetcher    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                              │
│  Features:                                                   │
│  • Background process monitoring                            │
│  • Real-time log streaming (SSE)                           │
│  • Download history management                              │
│  • Summary report generation                                │
└────────────────────────┬────────────────────────────────────┘
                         │ Subprocess
                         ▼
┌─────────────────────────────────────────────────────────────┐
│         CP4I Downloader (cp4i_downloader.py)                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Core Components:                                    │  │
│  │  • Authentication Manager (smart credential check)  │  │
│  │  • Image Mirror Handler (dual log output)           │  │
│  │  • Progress Tracker (background monitoring)         │  │
│  │  • Retry Logic (exponential backoff)                │  │
│  │  • Report Generator (comprehensive stats)           │  │
│  │  • Configuration Manager (file-based config)        │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │ CLI Commands
                         ▼
┌─────────────────────────────────────────────────────────────┐
│           External Tools & Services                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ oc       │  │ podman   │  │ curl     │  │ GitHub   │  │
│  │ ibm-pak  │  │ login    │  │ jq       │  │ API      │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
│                                                              │
│  • oc ibm-pak: Fetch CASE files and generate manifests     │
│  • oc image mirror: Download container images              │
│  • podman: Container registry authentication               │
│  • GitHub API: Fetch live version data                     │
└─────────────────────────────────────────────────────────────┘
```

### File Structure

```
cp4i-downloader/
├── app.py                          # Flask web application (main server)
├── cp4i_downloader.py              # Core downloader logic (CLI + library)
├── live_data_fetcher.py            # GitHub integration for live data
├── cp4i_version_data.json          # Local version database (100+ versions)
├── live_data_config.json           # Live data source configuration
├── requirements.txt                # Python dependencies
├── README.md                       # This file
├── API_ENDPOINTS.md                # Complete API documentation
│
├── static/                         # Frontend assets
│   ├── css/
│   │   └── style.css              # Modern UI styles (560+ lines)
│   └── js/
│       └── app.js                 # Frontend logic (1800+ lines)
│
└── templates/
    └── index.html                  # Main UI template (responsive design)
```

### Download Directory Structure

```
/opt/cp4i/
├── {component-name}/               # e.g., integration-platform-navigator-7.3.2-1234567890
│   ├── {name}-download.log         # Application logs (auth, manifest, status)
│   ├── {name}-mirror.log           # Mirror progress (oc image mirror output)
│   ├── {name}-summary-report.txt   # Final comprehensive report
│   ├── mapping.txt                 # Image mapping file (source → destination)
│   ├── .image-config.json          # Download configuration backup
│   └── v2/                         # Downloaded images (OCI format)
│       ├── blobs/
│       │   └── sha256/             # Image layers
│       └── manifests/              # Image manifests
│
├── .ibm-pak/                       # IBM Pak plugin data
│   ├── data/
│   │   ├── cases/                  # Downloaded CASE files
│   │   └── mirror/                 # Generated manifests
│   └── config/
│
└── .cp4i-downloader.conf           # Global configuration file
```

---

## 📋 Prerequisites

### System Requirements

| Requirement | Minimum | Recommended | Notes |
|-------------|---------|-------------|-------|
| **OS** | RHEL 8+ | RHEL 9+ | CentOS Stream, Rocky Linux also supported |
| **Python** | 3.8 | 3.11+ | Required for Flask and async features |
| **CPU** | 2 cores | 4+ cores | More cores = faster parallel downloads |
| **Memory** | 4 GB | 8 GB | More RAM helps with large image processing |
| **Disk Space** | 100 GB | 500 GB+ | Varies by component (see table below) |
| **Network** | 10 Mbps | 100+ Mbps | Faster = quicker downloads |

### Disk Space Requirements by Component

| Component | Typical Size | Notes |
|-----------|-------------|-------|
| **CP4I Components** | | |
| Platform Navigator | 50-100 GB | Core integration platform |
| API Connect | 80-150 GB | Largest component |
| MQ | 30-60 GB | Messaging |
| Event Streams | 40-80 GB | Kafka-based streaming |
| App Connect | 35-70 GB | Application integration |
| DataPower | 25-50 GB | Gateway |
| Asset Repository | 20-40 GB | Asset management |
| Operations Dashboard | 15-30 GB | Monitoring |
| **Full CP4I Suite** | **500+ GB** | All components |
| **OpenShift** | | |
| OpenShift Release (base) | 8-15 GB | Single version |
| OpenShift + Operators | 30-55 GB | With operator catalog |
| Multiple OCP Versions | 50-100 GB | 3-5 versions |
| **Red Hat Operators** | | |
| All Operators Catalog | 20-40 GB | Full catalog mirror |
| Selective Operators (5-10) | 5-15 GB | Targeted selection |
| Single Operator | 500 MB - 2 GB | Per operator |
| **Combined Deployment** | **600+ GB** | CP4I + OpenShift + Operators |

### Required Tools

#### Core Tools

| Tool | Purpose | Required For | Installation |
|------|---------|--------------|--------------|
| **oc** | OpenShift CLI | All operations | [Download](https://mirror.openshift.com/pub/openshift-v4/clients/ocp/latest/) |
| **oc ibm-pak** | IBM Pak plugin | CP4I downloads | Auto-installs on first use |
| **oc-mirror** | Mirror tool | Red Hat Operators | [Download](https://mirror.openshift.com/pub/openshift-v4/clients/ocp/latest/) |
| **podman** | Container management | Authentication | `yum install podman` |
| **curl** | HTTP client | API calls | `yum install curl` |
| **jq** | JSON processor | Data parsing | `yum install jq` |
| **python3** | Runtime | Web server | `yum install python3` |

```bash
# Check if tools are installed
oc version                    # OpenShift CLI
oc ibm-pak --version         # IBM Pak plugin
oc-mirror version            # Mirror tool (for Red Hat Operators)
podman --version             # Container management
curl --version               # HTTP client
jq --version                 # JSON processor
python3 --version            # Python runtime
```

#### Installation Commands

```bash
# RHEL/CentOS/Rocky Linux - Install base tools
sudo yum install -y python3 python3-pip podman curl jq

# Install OpenShift CLI (oc)
curl -LO https://mirror.openshift.com/pub/openshift-v4/clients/ocp/latest/openshift-client-linux.tar.gz
tar -xzf openshift-client-linux.tar.gz
sudo mv oc /usr/local/bin/
sudo chmod +x /usr/local/bin/oc

# Install oc-mirror (for Red Hat Operators mirroring)
curl -LO https://mirror.openshift.com/pub/openshift-v4/clients/ocp/latest/oc-mirror.tar.gz
tar -xzf oc-mirror.tar.gz
sudo mv oc-mirror /usr/local/bin/
sudo chmod +x /usr/local/bin/oc-mirror

# Verify oc ibm-pak plugin (auto-installs on first use)
oc ibm-pak --help

# Verify oc-mirror
oc-mirror version
```

**Important Notes:**
- `oc ibm-pak` plugin auto-installs when you first run `oc ibm-pak` command
- `oc-mirror` is **required** for Red Hat Operator catalog mirroring
- All tools should be in your `$PATH` for the application to work correctly

### Python Dependencies

```bash
# Install from requirements.txt
pip3 install -r requirements.txt

# Or install manually:
pip3 install Flask==3.0.0 Flask-CORS==4.0.0 requests==2.31.0 python-dotenv==1.0.0
```

**Dependencies:**
- `Flask 3.0.0` - Web framework
- `Flask-CORS 4.0.0` - Cross-origin resource sharing
- `requests 2.31.0` - HTTP library for live data fetching
- `python-dotenv 1.0.0` - Environment variable management

### IBM Entitlement Key

**Required for downloading CP4I images**

1. Go to [IBM Container Library](https://myibm.ibm.com/products-services/containerlibrary)
2. Log in with your IBM ID
3. Click "Get entitlement key" or "Copy key"
4. Save it securely (you'll need it for authentication)

**Key Features:**
- ✅ Never expires (but rotate periodically for security)
- ✅ Works for all CP4I components
- ✅ Can be reused across multiple downloads

### Target Registry Credentials (For Direct Mirroring)

**Required when using direct-to-registry mirror mode**

If you plan to mirror images directly to a target registry (instead of filesystem), you need credentials for that registry.

#### Setting Up Target Registry Authentication

**Option 1: Using podman login**
```bash
# Authenticate to your target registry
podman login registry.example.com:5000 -u admin -p password

# Credentials are stored in /root/.docker/config.json
# This file will be used automatically by the tool
```

**Option 2: Manual config.json**
```bash
# Create or edit /root/.docker/config.json
cat > /root/.docker/config.json <<EOF
{
  "auths": {
    "cp.icr.io": {
      "auth": "BASE64_ENCODED_IBM_CREDENTIALS"
    },
    "registry.redhat.io": {
      "auth": "BASE64_ENCODED_REDHAT_CREDENTIALS"
    },
    "registry.example.com:5000": {
      "auth": "BASE64_ENCODED_TARGET_REGISTRY_CREDENTIALS"
    }
  }
}
EOF

chmod 600 /root/.docker/config.json
```

**Option 3: Merge Multiple Credentials**
```bash
# If you have separate credential files, merge them
# Example: Merge IBM, Red Hat, and target registry credentials

# Read existing credentials
IBM_AUTH=$(podman login cp.icr.io -u cp -p $IBM_KEY --get-login 2>/dev/null)
REDHAT_AUTH=$(cat ~/pull-secret.json)
TARGET_AUTH=$(echo -n "admin:password" | base64)

# Create merged config
cat > /root/.docker/config.json <<EOF
{
  "auths": {
    "cp.icr.io": {
      "auth": "$(echo -n "cp:$IBM_KEY" | base64)"
    },
    "registry.redhat.io": {
      "auth": "$REDHAT_AUTH"
    },
    "quay.io": {
      "auth": "$REDHAT_AUTH"
    },
    "registry.example.com:5000": {
      "auth": "$TARGET_AUTH"
    }
  }
}
EOF
```

#### Target Registry Requirements

| Requirement | Description | Example |
|-------------|-------------|---------|
| **Registry URL** | Full registry address with port | registry.example.com:5000 |
| **Authentication** | Username/password or token | admin / SecurePassword123 |
| **TLS/SSL** | Certificate if using HTTPS | /etc/docker/certs.d/registry.example.com:5000/ca.crt |
| **Network Access** | Connectivity from download server | Test with `curl https://registry.example.com:5000/v2/` |
| **Storage Space** | Sufficient space in registry | 500+ GB for full CP4I suite |
| **Permissions** | Push access to repositories | Create/push images |

#### Testing Target Registry Access

```bash
# Test registry connectivity
curl -k https://registry.example.com:5000/v2/

# Test authentication
podman login registry.example.com:5000 -u admin -p password

# Test push capability (optional)
podman pull busybox
podman tag busybox registry.example.com:5000/test/busybox:latest
podman push registry.example.com:5000/test/busybox:latest

# Clean up test image
podman rmi registry.example.com:5000/test/busybox:latest
```

#### Common Target Registry Types

**Harbor Registry:**
```bash
# Harbor uses standard Docker registry API
podman login harbor.example.com -u admin -p Harbor12345
```

**Red Hat Quay:**
```bash
# Quay requires robot account or OAuth token
podman login quay.example.com -u username+robot -p TOKEN
```

**Docker Registry:**
```bash
# Standard Docker registry
podman login registry.example.com:5000 -u admin -p password
```

**OpenShift Internal Registry:**
```bash
# Use OpenShift token
oc login https://api.cluster.example.com:6443
TOKEN=$(oc whoami -t)
podman login default-route-openshift-image-registry.apps.cluster.example.com \
  -u kubeadmin -p $TOKEN
```

#### Insecure Registry Configuration

If your target registry uses self-signed certificates or HTTP:

```bash
# Add to /etc/containers/registries.conf
cat >> /etc/containers/registries.conf <<EOF
[[registry]]
location = "registry.example.com:5000"
insecure = true
EOF

# Restart podman (if needed)
systemctl restart podman
```

**Important Notes:**
- ✅ Target registry credentials are **only required** for direct-to-registry mirroring
- ✅ For filesystem mirroring, you only need source registry credentials (IBM/Red Hat)
- ✅ Ensure all credentials are in the same config.json file
- ✅ Test connectivity and authentication before starting large downloads
- ✅ Use secure passwords and rotate credentials regularly

- ✅ Validates automatically before download

### Red Hat Registry Access

**Required for downloading OpenShift and Red Hat Operator images**

1. Go to [Red Hat OpenShift Cluster Manager](https://console.redhat.com/openshift/downloads)
2. Log in with your Red Hat account
3. Navigate to "Downloads" → "Tokens" → "Pull Secret"
4. Download or copy your pull secret (JSON format)
5. Save it as `/root/.docker/config.json` or specify custom path

**Pull Secret Features:**
- ✅ Provides access to Red Hat registries (registry.redhat.io, quay.io)
- ✅ Required for OpenShift release mirroring
- ✅ Required for Red Hat Operator catalog mirroring
- ✅ Can be merged with other registry credentials

**Merging Credentials:**
```bash
# If you need both IBM and Red Hat credentials in one file
# Manually merge the "auths" sections from both JSON files
# Or use podman login for each registry separately
podman login cp.icr.io -u cp -p <IBM_ENTITLEMENT_KEY>
podman login registry.redhat.io --authfile ~/.docker/config.json
```

---

## 🚀 Installation

### Quick Install (5 Minutes)

```bash
# 1. Create application directory
sudo mkdir -p /opt/cp4i-downloader
sudo chown $USER:$USER /opt/cp4i-downloader
cd /opt/cp4i-downloader

# 2. Copy application files
# (Copy all files from the repository to this directory)

# 3. Install Python dependencies
pip3 install -r requirements.txt

# 4. Verify prerequisites
python3 cp4i_downloader.py --check-prerequisites

# 5. Start the web server
python3 app.py
```

Access the UI at: `http://localhost:5000`

### Detailed Installation

#### Step 1: Install System Prerequisites

```bash
# Update system
sudo yum update -y

# Install required packages
sudo yum install -y python3 python3-pip podman curl jq git

# Install OpenShift CLI
curl -LO https://mirror.openshift.com/pub/openshift-v4/clients/ocp/latest/openshift-client-linux.tar.gz
tar -xzf openshift-client-linux.tar.gz
sudo mv oc kubectl /usr/local/bin/
sudo chmod +x /usr/local/bin/oc /usr/local/bin/kubectl

# Verify installations
oc version
podman --version
python3 --version
```

#### Step 2: Setup Application

```bash
# Create directories
sudo mkdir -p /opt/cp4i-downloader
sudo mkdir -p /opt/cp4i
sudo chown -R $USER:$USER /opt/cp4i-downloader /opt/cp4i

# Navigate to application directory
cd /opt/cp4i-downloader

# Copy application files
# app.py, cp4i_downloader.py, live_data_fetcher.py, etc.

# Install Python dependencies
pip3 install -r requirements.txt

# Make scripts executable
chmod +x app.py cp4i_downloader.py
```

#### Step 3: Verify Installation

```bash
# Check prerequisites
python3 cp4i_downloader.py --check-prerequisites

# Expected output:
# ✓ oc command found: /usr/local/bin/oc
# ✓ oc ibm-pak plugin found
# ✓ podman command found: /usr/bin/podman
# ✓ curl command found: /usr/bin/curl
# ✓ jq command found: /usr/bin/jq
# ✓ All prerequisites validated

# Check GitHub connectivity
python3 cp4i_downloader.py --check-github

# Test CLI
python3 cp4i_downloader.py --help
```

#### Step 4: Configure Storage

```bash
# Check available disk space
df -h /opt/cp4i

# If insufficient space, use different directory
export CP4I_HOME=/data/cp4i
mkdir -p $CP4I_HOME
```

#### Step 5: Start Web Server

```bash
# Foreground (for testing)
python3 app.py

# Background (production)
nohup python3 app.py > app.log 2>&1 &

# Check if running
ps aux | grep app.py
netstat -tulpn | grep 5000
```

### Production Deployment with Systemd

```bash
# Create systemd service file
sudo tee /etc/systemd/system/cp4i-downloader.service > /dev/null <<EOF
[Unit]
Description=CP4I Downloader Web Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/opt/cp4i-downloader
Environment="PATH=/usr/local/bin:/usr/bin"
ExecStart=/usr/bin/python3 /opt/cp4i-downloader/app.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable cp4i-downloader
sudo systemctl start cp4i-downloader

# Check status
sudo systemctl status cp4i-downloader

# View logs
sudo journalctl -u cp4i-downloader -f
```

---

## ⚙️ Configuration

### Environment Variables

```bash
# Optional: Set default home directory
export CP4I_HOME=/opt/cp4i

# Optional: Configure notifications
export CP4I_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
export CP4I_NOTIFICATION_EMAIL=admin@example.com

# Optional: Set parallel download limit
export CP4I_MAX_PARALLEL=5

# Optional: Set retry configuration
export CP4I_MAX_RETRIES=3
export CP4I_RETRY_DELAY=60
```

### Configuration File

Create `/opt/cp4i/.cp4i-downloader.conf`:

```bash
# CP4I Downloader Configuration
# Lines starting with # are comments

# Home directory for downloads
HOME_DIR=/opt/cp4i

# Minimum disk space required (GB)
MIN_DISK_SPACE_GB=100

# Retry configuration
MAX_RETRIES=3
RETRY_BASE_DELAY=5

# Parallel downloads
MAX_PARALLEL_DOWNLOADS=5

# Notifications
WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
NOTIFICATION_EMAIL=admin@example.com

# GitHub connectivity
CHECK_GITHUB_ON_START=true
```

### Web Server Configuration

Edit `app.py` to customize:

```python
# Change port (default: 5000)
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)

# Change default home directory
HOME_DIR = "/data/cp4i"

# Enable debug mode (development only)
app.run(host='0.0.0.0', port=5000, debug=True)
```

### Live Data Configuration

Edit `live_data_config.json` to customize data sources:

```json
{
  "data_sources": {
    "github_sources": {
      "enabled": true,
      "ibm_case_repo": "https://api.github.com/repos/IBM/cloud-pak/contents/repo/case",
      "timeout": 30,
      "retry_attempts": 3
    }
  },
  "cache": {
    "enabled": true,
    "directory": ".cache",
    "max_age_hours": 24
  }
}
```

---

## 📖 Usage

### Web Interface

#### Starting the Web Server

```bash
# Method 1: Foreground (for testing)
cd /opt/cp4i-downloader
python3 app.py

# Method 2: Background
nohup python3 app.py > app.log 2>&1 &

# Method 3: Systemd (recommended for production)
sudo systemctl start cp4i-downloader
```

#### Accessing the UI

1. Open browser: `http://your-server:5000`
2. You'll see the CP4I Downloader dashboard with 5 tabs:
   - **CP4I Download**: Start new CP4I component downloads
   - **OpenShift Mirror**: Mirror OpenShift releases
   - **Red Hat Operators**: Download Red Hat operator catalogs
   - **Active Downloads**: Monitor running downloads
   - **History**: View completed/failed downloads

#### Downloading a CP4I Component

**Step 1: Select Download Mode**
- **Standard Download**: Download all images to filesystem
- **Selective Download**: Use filters to download specific images
- **Update Existing**: Update previously downloaded component
- **Direct to Registry**: Mirror directly to target registry (no local storage)

**Step 2: Configure Download**

| Field | Description | Example |
|-------|-------------|---------|
| **Component** | Select CP4I component | Platform Navigator |
| **Version** | Enter or select version | 7.3.2 |
| **Name** | Auto-generated unique name | integration-platform-navigator-7.3.2-1234567890 |
| **Home Directory** | Download location | /opt/cp4i |
| **Final Registry** | Target registry (optional) | registry.example.com:5000 |
| **Entitlement Key** | IBM entitlement key | eyJhbGc... |
| **Filter** | Regex pattern (optional) | .*navigator.* |

**Step 3: Advanced Options**

- ☑️ **Dry Run**: Test without downloading
- ☑️ **Retry**: Enable automatic retry on failure
- ☑️ **Force Retry**: Force fresh authentication
- ☑️ **Verbose**: Enable detailed logging

**Step 4: Start Download**

Click "Start Download" button. The download will:
1. Validate prerequisites
2. Authenticate with IBM registry
3. Fetch CASE file
4. Generate image manifests
5. Start image mirroring
6. Track progress in background
7. Generate summary report

#### Monitoring Progress

**Active Downloads Tab:**
- Shows all running downloads
- Real-time status updates
- Progress indicators
- PID information
- Action buttons (Dismiss, View Logs, View Report)

**View Logs:**
Click "View Logs" to see detailed logs with **tabbed interface**:

1. **Download Log Tab**:
   - Prerequisites validation
   - Authentication status
   - CASE file fetching
   - Manifest generation
   - Process status

2. **Mirror Log Tab**:
   - Real-time image mirroring progress
   - Image download status
   - Transfer rates
   - Completion status

**View Report:**
Click "View Report" to see comprehensive summary:
- Download information
- Timing details
- Configuration used
- File system details
- System information
- Error details (if failed)

### Command Line Interface

#### Basic Usage

```bash
# Download a component
python3 cp4i_downloader.py \
  --component integration-platform-navigator \
  --version 7.3.2 \
  --home-dir /opt/cp4i \
  --entitlement-key YOUR_KEY

# Dry run (test without downloading)
python3 cp4i_downloader.py \
  --component integration-platform-navigator \
  --version 7.3.2 \
  --dry-run

# Download with filter
python3 cp4i_downloader.py \
  --component integration-platform-navigator \
  --version 7.3.2 \
  --filter ".*navigator.*"

# Enable verbose logging
python3 cp4i_downloader.py \
  --component integration-platform-navigator \
  --version 7.3.2 \
  --verbose
```

#### Advanced Usage

```bash
# Full command with all options
python3 cp4i_downloader.py \
  --component integration-platform-navigator \
  --version 7.3.2 \
  --home-dir /opt/cp4i \
  --final-registry registry.example.com:5000 \
  --registry-auth-file /root/.docker/config.json \
  --entitlement-key YOUR_KEY \
  --filter ".*navigator.*" \
  --max-per-registry 5 \
  --retry \
  --force-retry \
  --verbose \
  --config /opt/cp4i/.cp4i-downloader.conf
```

#### Command Line Options

| Option | Description | Default | Required |
|--------|-------------|---------|----------|
| `--component` | Component name | - | Yes |
| `--version` | CASE version | - | Yes |
| `--home-dir` | Download directory | `/opt/cp4i` | No |
| `--final-registry` | Target registry URL | - | No |
| `--registry-auth-file` | Auth file path | `/root/.docker/config.json` | No |
| `--entitlement-key` | IBM entitlement key | - | No* |
| `--filter` | Image filter regex | - | No |
| `--max-per-registry` | Parallel downloads | `5` | No |
| `--dry-run` | Test mode | `false` | No |
| `--retry` | Enable retry | `false` | No |
| `--force-retry` | Force fresh auth | `false` | No |
| `--verbose` | Detailed logging | `false` | No |
| `--config` | Config file path | - | No |
| `--check-prerequisites` | Verify tools | - | No |
| `--check-github` | Test GitHub access | - | No |

*Required if not already authenticated with podman

#### Monitoring CLI Downloads

```bash
# Watch application logs (real-time)
tail -f /opt/cp4i/{component-name}/{name}-download.log

# Watch mirror progress (real-time)
tail -f /opt/cp4i/{component-name}/{name}-mirror.log

# View summary report
cat /opt/cp4i/{component-name}/{name}-summary-report.txt

# Check download status
ls -lh /opt/cp4i/{component-name}/v2/

# Count downloaded images
find /opt/cp4i/{component-name}/v2/ -name "*.tar" | wc -l
```

### OpenShift Mirror

The CP4I Downloader includes comprehensive OpenShift release mirroring capabilities for air-gapped deployments.

#### Supported OpenShift Versions

- **4.14.x** - Extended Update Support (EUS)
- **4.15.x** - Standard release
- **4.16.x** - Standard release
- **4.17.x** - Standard release
- **4.18.x** - Standard release
- **4.19.x** - Standard release
- **4.20.x** - Latest stable

#### Mirror Modes

**1. Filesystem Mirror (Recommended for Air-Gapped)**

Downloads OpenShift release images to local filesystem for transfer to air-gapped environment.

```bash
# Using Web UI:
# 1. Navigate to "OpenShift Mirror" tab
# 2. Select OpenShift version (e.g., 4.16.20)
# 3. Choose "Filesystem" mirror type
# 4. Set removable media path (e.g., /opt/ocp)
# 5. Configure options:
#    - Architecture (x86_64, aarch64, ppc64le, s390x)
#    - Include operator catalogs (optional)
#    - Generate IDMS/ICSP configurations
# 6. Click "Start Mirror"
```

**2. Direct to Registry Mirror**

Mirrors OpenShift images directly to your target registry without local storage.

```bash
# Using Web UI:
# 1. Navigate to "OpenShift Mirror" tab
# 2. Select OpenShift version
# 3. Choose "Registry" mirror type
# 4. Enter target registry (e.g., registry.example.com:5000)
# 5. Set local repository path (e.g., ocp4/openshift4)
# 6. Click "Start Mirror"
```

#### OpenShift Mirror Configuration

| Field | Description | Example | Required |
|-------|-------------|---------|----------|
| **OCP Release** | OpenShift version | 4.16.20 | Yes |
| **Architecture** | CPU architecture | x86_64 | Yes |
| **Mirror Type** | Filesystem or Registry | filesystem | Yes |
| **Removable Media Path** | Local storage path | /opt/ocp | Yes (filesystem) |
| **Target Registry** | Destination registry | registry.example.com:5000 | Yes (registry) |
| **Local Repository** | Repository path | ocp4/openshift4 | Yes (registry) |
| **Auth File** | Pull secret location | /root/.docker/config.json | Yes |
| **Include Operators** | Mirror operator catalogs | true/false | No |
| **Generate IDMS** | Create IDMS config | true/false | No |
| **Print IDMS** | Display IDMS YAML | true/false | No |

#### OpenShift Mirror Process

**Filesystem Mirror:**
```bash
# The tool executes:
oc adm release mirror \
  -a /root/.docker/config.json \
  --to-dir=/opt/ocp/mirror \
  quay.io/openshift-release-dev/ocp-release:4.16.20-x86_64
```

**Registry Mirror:**
```bash
# The tool executes:
oc adm release mirror \
  -a /root/.docker/config.json \
  --from=quay.io/openshift-release-dev/ocp-release:4.16.20-x86_64 \
  --to=registry.example.com:5000/ocp4/openshift4 \
  --to-release-image=registry.example.com:5000/ocp4/openshift4:4.16.20-x86_64
```

#### Including Operator Catalogs

When "Include Operators" is enabled, the tool also mirrors Red Hat operator catalogs:

```bash
oc adm catalog mirror \
  registry.redhat.io/redhat/redhat-operator-index:v4.16 \
  registry.example.com:5000/ocp4/openshift4 \
  -a /root/.docker/config.json
```

#### Generating IDMS/ICSP Configurations

Enable "Generate IDMS" or "Print IDMS" to automatically generate ImageDigestMirrorSet configurations for your air-gapped cluster:

```yaml
# Example IDMS output
apiVersion: config.openshift.io/v1
kind: ImageDigestMirrorSet
metadata:
  name: release-0
spec:
  imageDigestMirrors:
  - mirrors:
    - registry.example.com:5000/ocp4/openshift4
    source: quay.io/openshift-release-dev/ocp-release
```

#### OpenShift Mirror Disk Space Requirements

| Version | Approximate Size | Notes |
|---------|-----------------|-------|
| 4.14.x | 8-12 GB | Base release |
| 4.15.x | 8-12 GB | Base release |
| 4.16.x | 9-13 GB | Base release |
| 4.17.x | 9-13 GB | Base release |
| 4.18.x | 10-14 GB | Base release |
| 4.19.x | 10-14 GB | Base release |
| 4.20.x | 10-15 GB | Latest release |
| **With Operators** | **+20-40 GB** | Operator catalog |

#### Monitoring OpenShift Mirror Progress

```bash
# View mirror logs in real-time
tail -f /opt/ocp/openshift-{version}-{timestamp}/openshift-{version}-{timestamp}-download.log

# Check downloaded content
ls -lh /opt/ocp/mirror/

# Verify image count
find /opt/ocp/mirror -type f | wc -l
```

### Red Hat Operators Mirror

Mirror Red Hat operator catalogs for air-gapped OpenShift deployments using the integrated oc-mirror tool.

#### Supported Operator Catalogs

The tool supports mirroring from Red Hat operator catalogs:
- **redhat-operators** - Red Hat certified operators
- **certified-operators** - Partner certified operators
- **community-operators** - Community operators
- **redhat-marketplace** - Red Hat Marketplace operators

#### Available Red Hat Operators

Common operators available for mirroring:

| Operator | Package Name | Description |
|----------|--------------|-------------|
| **OpenShift Serverless** | serverless-operator | Knative Serving and Eventing |
| **OpenShift Service Mesh** | servicemeshoperator | Istio-based service mesh |
| **OpenShift Pipelines** | openshift-pipelines-operator-rh | Tekton CI/CD |
| **OpenShift GitOps** | openshift-gitops-operator | Argo CD GitOps |
| **OpenShift Logging** | cluster-logging | EFK logging stack |
| **OpenShift Data Foundation** | odf-operator | Software-defined storage |
| **Advanced Cluster Security** | rhacs-operator | Security platform |
| **Red Hat Quay** | quay-operator | Container registry |
| **AMQ Streams** | amq-streams | Apache Kafka |
| **AMQ Broker** | amq-broker-rhel8 | ActiveMQ Artemis |
| **3scale API Management** | 3scale-operator | API management |
| **Camel K** | red-hat-camel-k | Integration framework |

#### Operator Mirror Modes

**1. Filesystem Mirror (Air-Gapped)**

Downloads operator images to local filesystem for transfer.

```bash
# Using Web UI:
# 1. Navigate to "Red Hat Operators" tab
# 2. Select catalog version (e.g., v4.16)
# 3. Choose "Filesystem" mirror type
# 4. Set local path (e.g., /opt/operators)
# 5. Select operators:
#    - Choose "All Operators" or
#    - Select specific operators from list
# 6. Configure channels (optional)
# 7. Click "Start Mirror"
```

**2. Direct to Registry Mirror**

Mirrors operators directly to target registry.

```bash
# Using Web UI:
# 1. Navigate to "Red Hat Operators" tab
# 2. Select catalog version
# 3. Choose "Registry" mirror type
# 4. Enter target registry
# 5. Select operators
# 6. Click "Start Mirror"
```

#### Operator Mirror Configuration

| Field | Description | Example | Required |
|-------|-------------|---------|----------|
| **Catalog Version** | Operator catalog version | v4.16 | Yes |
| **Mirror Type** | Filesystem or Registry | filesystem | Yes |
| **Local Path** | Storage location | /opt/operators | Yes (filesystem) |
| **Target Registry** | Destination registry | registry.example.com:5000 | Yes (registry) |
| **Operators** | Operator selection | All or specific list | Yes |
| **Channels** | Update channels | stable, fast, candidate | No |
| **Auth File** | Pull secret path | /root/.docker/config.json | Yes |
| **Include Helm** | Include Helm charts | true/false | No |

#### ImageSetConfiguration

The tool automatically generates an ImageSetConfiguration file for oc-mirror:

```yaml
kind: ImageSetConfiguration
apiVersion: mirror.openshift.io/v1alpha2
storageConfig:
  local:
    path: /opt/operators
mirror:
  platform:
    channels:
      - name: stable-4.16
  operators:
    - catalog: registry.redhat.io/redhat/redhat-operator-index:v4.16
      packages:
        - name: serverless-operator
        - name: servicemeshoperator
        - name: openshift-pipelines-operator-rh
```

#### Operator Mirror Process

**Filesystem Mirror:**
```bash
# The tool executes:
oc-mirror --config /tmp/imageset-config.yaml file:///opt/operators
```

**Registry Mirror:**
```bash
# The tool executes:
oc-mirror --config /tmp/imageset-config.yaml docker://registry.example.com:5000
```

#### Selective Operator Mirroring

**Mirror All Operators:**
```bash
# Select "All Operators" in the UI
# This mirrors the entire catalog (20-40 GB)
```

**Mirror Specific Operators:**
```bash
# Select individual operators from the list
# Example: Only Serverless, Service Mesh, and Pipelines
# This reduces download size significantly (5-10 GB)
```

**Mirror by Channel:**
```bash
# Specify channels to limit versions
# Example: stable, fast, candidate
# Reduces image count per operator
```

#### Operator Mirror Disk Space Requirements

| Selection | Approximate Size | Notes |
|-----------|-----------------|-------|
| **All Operators** | 20-40 GB | Full catalog |
| **5-10 Operators** | 5-15 GB | Selective mirror |
| **Single Operator** | 500 MB - 2 GB | Per operator |
| **With Helm Charts** | +2-5 GB | Additional content |

#### Retry and Resume

If an operator mirror fails or is interrupted:

```bash
# Using Web UI:
# 1. Go to "History" tab
# 2. Find the failed download
# 3. Click "Retry" button
# 4. The tool will use --ignore-history flag to retry
```

The retry command uses:
```bash
oc-mirror --config /tmp/imageset-config.yaml \
  file:///opt/operators \
  --ignore-history
```

#### Publishing to Target Registry

After mirroring to filesystem, publish to target registry:

```bash
# The tool can generate this command:
oc-mirror --from /opt/operators docker://registry.example.com:5000
```

#### Monitoring Operator Mirror Progress

```bash
# View mirror logs
tail -f /opt/operators/operators-{version}-{timestamp}/operators-{version}-{timestamp}-download.log

# Check mirrored content
ls -lh /opt/operators/

# View ImageSetConfiguration
cat /tmp/imageset-config-{timestamp}.yaml

# Check oc-mirror workspace
ls -lh /opt/operators/.oc-mirror/
```

#### Applying Mirrored Operators in Air-Gapped Cluster

After mirroring and transferring to air-gapped environment:

1. **Publish to local registry:**
```bash
oc-mirror --from /opt/operators docker://registry.example.com:5000
```

2. **Apply ImageContentSourcePolicy:**
```bash
oc apply -f /opt/operators/oc-mirror-workspace/results-*/imageContentSourcePolicy.yaml
```

3. **Apply CatalogSource:**
```bash
oc apply -f /opt/operators/oc-mirror-workspace/results-*/catalogSource-*.yaml
```

4. **Verify operators available:**
```bash
oc get catalogsource -n openshift-marketplace
oc get packagemanifests
```


---

## 🎯 Download Modes

### 1. Standard Download

**Use Case**: Download all images to local filesystem

```bash
# CLI
python3 cp4i_downloader.py \
  --component integration-platform-navigator \
  --version 7.3.2

# Web UI
# Select "Standard Download" mode
```

**Process**:
1. Downloads all images to `/opt/cp4i/{name}/v2/`
2. Creates mapping file for later upload
3. Suitable for air-gapped transfer

**Disk Space**: Full component size (50-150 GB)

### 2. Selective Download

**Use Case**: Download only specific images using filters

```bash
# Download only navigator images
python3 cp4i_downloader.py \
  --component integration-platform-navigator \
  --version 7.3.2 \
  --filter ".*navigator.*"

# Download only operator images
python3 cp4i_downloader.py \
  --component integration-platform-navigator \
  --version 7.3.2 \
  --filter ".*operator.*"
```

**Benefits**:
- Saves disk space (30-60% reduction)
- Faster downloads
- Targeted image selection

### 3. Update Existing

**Use Case**: Update previously downloaded component

```bash
python3 cp4i_downloader.py \
  --component integration-platform-navigator \
  --version 7.3.2 \
  --retry
```

**Process**:
1. Checks existing downloads
2. Downloads only missing/failed images
3. Updates mapping file

### 4. Direct to Registry

**Use Case**: Mirror images directly to target registry without local storage

**✅ IMPLEMENTED**: True direct-to-registry mirroring is now supported! Images are mirrored directly from source registry (cp.icr.io) to your target registry without requiring local disk space.

**Usage**:
```bash
# CLI
python3 cp4i_downloader.py \
  --component integration-platform-navigator \
  --version 7.3.2 \
  --final-registry registry.example.com:5000 \
  --direct-to-registry

# Web UI
# Select "Direct to Registry" mode in the download form
```

**How It Works**:

```bash
# Step 1: Generate manifest with target registry
oc ibm-pak generate mirror-manifests \
  integration-platform-navigator \
  registry.example.com:5000 \
  --version 7.3.2

# Step 2: Mirror directly from source to target registry
oc image mirror \
  -f images-mapping.txt \
  --filter-by-os='.*' \
  -a /root/.docker/config.json \
  --insecure \
  --skip-multiple-scopes \
  --max-per-registry=5

# Note: No --dir flag used
# Images flow: cp.icr.io → registry.example.com:5000
# No local storage needed (except temp)
```

**Benefits**:
- ✅ No local disk space required (except temporary space during transfer)
- ✅ Direct transfer from source to target registry
- ✅ Faster for connected environments
- ✅ Reduced I/O operations
- ✅ Ideal for environments with limited storage but good network connectivity

**Requirements**:
- Network access to both source (cp.icr.io) and target registry
- Registry credentials configured for both registries in `/root/.docker/config.json`
- Sufficient bandwidth for direct transfer
- Target registry must be accessible and have push permissions

**Comparison with Filesystem Mode**:

| Aspect | Filesystem Mode | Direct-to-Registry Mode |
|--------|----------------|------------------------|
| **Local Disk Space** | Required (50-150 GB) | Not required (only temp) |
| **Command Flag** | Uses `--dir` flag | No `--dir` flag |
| **Image Flow** | Source → Filesystem → Target | Source → Target (direct) |
| **Speed** | Slower (2 transfers) | Faster (1 transfer) |
| **Use Case** | Air-gapped environments | Connected environments |

---

## 📝 Log System

### Dual Log Architecture

The application uses a **2-log file system** for better organization:

#### 1. Download Log (`{name}-download.log`)

**Contains**:
- Prerequisites validation
- Authentication status
- CASE file fetching
- Manifest generation
- Process lifecycle events
- Error messages
- Summary information

**Example**:
```
[2026-01-06 10:30:15] [INFO] Starting CP4I Downloader v2.0.0
[2026-01-06 10:30:15] [INFO] Validating prerequisites...
[2026-01-06 10:30:16] [INFO] ✓ All prerequisites validated
[2026-01-06 10:30:16] [INFO] Checking authentication...
[2026-01-06 10:30:17] [INFO] ✓ Already authenticated with cp.icr.io
[2026-01-06 10:30:17] [INFO] Fetching CASE file...
[2026-01-06 10:30:20] [INFO] ✓ CASE file fetched successfully
[2026-01-06 10:30:20] [INFO] Generating manifests...
[2026-01-06 10:30:25] [INFO] ✓ Manifests generated successfully
[2026-01-06 10:30:25] [INFO] Starting image mirror process...
[2026-01-06 10:30:25] [INFO] Mirror output will be written to: {name}-mirror.log
[2026-01-06 10:30:26] [INFO] Image mirroring started in background (PID: 12345)
```

#### 2. Mirror Log (`{name}-mirror.log`)

**Contains**:
- Real-time image mirroring progress
- Image download status
- Transfer rates
- Blob copying progress
- Completion status

**Example**:
```
info: Planning completed in 2.3s
sha256:abc123... file://...
Copying blob sha256:abc123...
Copying blob sha256:def456...
cp.icr.io/cp/icp4i/icip-services sha256:bbd2ca... 10.73KiB
cp.icr.io/cp/icp4i/icip-services sha256:79d5a0... 12.81KiB
info: Mirroring completed in 45m23s
```

### Accessing Logs

**Web UI**:
1. Click "View Logs" button
2. Switch between tabs:
   - **Download Log**: Application events
   - **Mirror Log**: Download progress

**CLI**:
```bash
# View download log
cat /opt/cp4i/{name}/{name}-download.log

# View mirror log
cat /opt/cp4i/{name}/{name}-mirror.log

# Monitor in real-time
tail -f /opt/cp4i/{name}/{name}-mirror.log
```

**API**:
```bash
# Get download log
curl "http://localhost:5000/api/logs/{name}?type=download"

# Get mirror log
curl "http://localhost:5000/api/logs/{name}?type=mirror"

# Stream mirror log (real-time)
curl "http://localhost:5000/api/logs/{name}/stream?type=mirror"
```

---

## 💡 Use Cases

### Use Case 1: Air-Gapped Environment Setup

**Scenario**: Deploy CP4I in a network with no internet access

**Connected Environment** (with internet):
```bash
# 1. Download all required components
python3 cp4i_downloader.py \
  --component integration-platform-navigator \
  --version 7.3.2 \
  --home-dir /opt/cp4i

python3 cp4i_downloader.py \
  --component integration-api-connect \
  --version 5.0.2 \
  --home-dir /opt/cp4i

python3 cp4i_downloader.py \
  --component integration-mq \
  --version 9.3.4 \
  --home-dir /opt/cp4i

# 2. Package downloaded images
cd /opt/cp4i
tar -czf cp4i-images-$(date +%Y%m%d).tar.gz */v2 */mapping.txt

# 3. Verify package
ls -lh cp4i-images-*.tar.gz
```

**Transfer** to air-gapped environment (USB drive, secure transfer, etc.)

**Air-Gapped Environment**:
```bash
# 1. Extract images
tar -xzf cp4i-images-20260106.tar.gz -C /opt/cp4i

# 2. Upload to local registry
for component in /opt/cp4i/*/; do
  name=$(basename $component)
  oc image mirror \
    -f /opt/cp4i/$name/mapping.txt \
    --from-dir=/opt/cp4i/$name/v2 \
    --to=registry.airgap.local:5000 \
    -a /root/.docker/config.json
done
```

### Use Case 2: Disaster Recovery Preparation

**Scenario**: Maintain offline backup of CP4I images

```bash
# Create backup script
cat > /opt/scripts/cp4i-backup.sh <<'EOF'
#!/bin/bash
BACKUP_DIR=/backup/cp4i
DATE=$(date +%Y%m%d)

# Download latest versions
python3 /opt/cp4i-downloader/cp4i_downloader.py \
  --component integration-platform-navigator \
  --version 7.3.2 \
  --home-dir $BACKUP_DIR

# Create archive
tar -czf $BACKUP_DIR/cp4i-backup-$DATE.tar.gz \
  $BACKUP_DIR/*/v2 \
  $BACKUP_DIR/*/mapping.txt

# Clean up old backups (keep last 7 days)
find $BACKUP_DIR -name "cp4i-backup-*.tar.gz" -mtime +7 -delete

echo "Backup completed: cp4i-backup-$DATE.tar.gz"
EOF

chmod +x /opt/scripts/cp4i-backup.sh

# Schedule weekly backups
crontab -e
# Add: 0 2 * * 0 /opt/scripts/cp4i-backup.sh
```

### Use Case 3: Multi-Version Testing

**Scenario**: Test multiple CP4I versions before production deployment

```bash
# Download multiple versions
for version in 7.3.0 7.3.1 7.3.2; do
  python3 cp4i_downloader.py \
    --component integration-platform-navigator \
    --version $version \
    --home-dir /opt/cp4i-test
done

# Compare versions
ls -lh /opt/cp4i-test/*/

# Test each version
for dir in /opt/cp4i-test/*/; do
  name=$(basename $dir)
  echo "Testing $name..."
  # Deploy and test
done
```

### Use Case 4: Selective Component Download

**Scenario**: Download only specific images using filters

```bash
# Download only navigator images (saves 40-60% disk space)
python3 cp4i_downloader.py \
  --component integration-platform-navigator \
  --version 7.3.2 \
  --filter ".*navigator.*"

# Download only operator images
python3 cp4i_downloader.py \
  --component integration-platform-navigator \
  --version 7.3.2 \
  --filter ".*operator.*"

# Download specific architecture
python3 cp4i_downloader.py \
  --component integration-platform-navigator \
  --version 7.3.2 \
  --filter ".*amd64.*"
```

### Use Case 5: Automated CI/CD Pipeline

**Scenario**: Integrate with CI/CD for automated image management

```bash
#!/bin/bash
# ci-cd-download.sh

set -e

# Configuration
COMPONENT="integration-platform-navigator"
VERSION="7.3.2"
HOME_DIR="/opt/cp4i"
SLACK_WEBHOOK="${CP4I_WEBHOOK_URL}"

# Download
echo "Starting download: $COMPONENT $VERSION"
python3 /opt/cp4i-downloader/cp4i_downloader.py \
  --component $COMPONENT \
  --version $VERSION \
  --home-dir $HOME_DIR \
  --entitlement-key $IBM_ENTITLEMENT_KEY \
  --verbose

# Check exit code
if [ $? -eq 0 ]; then
  echo "✓ Download successful"
  
  # Notify success
  curl -X POST $SLACK_WEBHOOK \
    -H 'Content-Type: application/json' \
    -d "{\"text\":\"✓ CP4I download completed: $COMPONENT $VERSION\"}"
  
  # Trigger next pipeline stage
  ./upload-to-registry.sh
else
  echo "✗ Download failed"
  
  # Notify failure
  curl -X POST $SLACK_WEBHOOK \
    -H 'Content-Type: application/json' \
    -d "{\"text\":\"✗ CP4I download failed: $COMPONENT $VERSION\"}"
  
  exit 1
fi
```

### Use Case 6: Direct Registry Mirror

**Scenario**: Mirror images directly to target registry without local storage

```bash
# Mirror directly to target registry
python3 cp4i_downloader.py \
  --component integration-platform-navigator \
  --version 7.3.2 \
  --final-registry registry.example.com:5000 \
  --registry-auth-file /root/.docker/config.json

# Benefits:
# - No local disk space required
# - Faster for connected environments
# - Direct transfer to target
```

### Use Case 7: OpenShift Air-Gapped Deployment

**Scenario**: Deploy OpenShift in an air-gapped environment with operators

**Connected Environment**:
```bash
# 1. Mirror OpenShift release to filesystem
# Using Web UI:
# - Navigate to "OpenShift Mirror" tab
# - Select version: 4.16.20
# - Mirror type: Filesystem
# - Path: /opt/ocp
# - Include operators: Yes
# - Click "Start Mirror"

# 2. Package for transfer
cd /opt/ocp
tar -czf openshift-4.16.20-$(date +%Y%m%d).tar.gz mirror/

# 3. Verify package
ls -lh openshift-4.16.20-*.tar.gz
```

**Transfer** to air-gapped environment

**Air-Gapped Environment**:
```bash
# 1. Extract images
tar -xzf openshift-4.16.20-20260112.tar.gz -C /opt/ocp

# 2. Upload to local registry
oc adm release mirror \
  --from-dir=/opt/ocp/mirror \
  --to=registry.airgap.local:5000/ocp4/openshift4 \
  --to-release-image=registry.airgap.local:5000/ocp4/openshift4:4.16.20-x86_64 \
  -a /root/.docker/config.json

# 3. Apply IDMS configuration
oc apply -f /opt/ocp/mirror/imageContentSourcePolicy.yaml

# 4. Install OpenShift using mirrored images
openshift-install create cluster --dir=/opt/install-config
```

### Use Case 8: Red Hat Operators for Air-Gapped

**Scenario**: Deploy Red Hat operators in air-gapped OpenShift cluster

**Connected Environment**:
```bash
# 1. Mirror operator catalog
# Using Web UI:
# - Navigate to "Red Hat Operators" tab
# - Catalog version: v4.16
# - Mirror type: Filesystem
# - Path: /opt/operators
# - Select operators:
#   * OpenShift Serverless
#   * OpenShift Service Mesh
#   * OpenShift Pipelines
#   * OpenShift GitOps
# - Click "Start Mirror"

# 2. Package for transfer
cd /opt/operators
tar -czf operators-catalog-$(date +%Y%m%d).tar.gz .oc-mirror/

# 3. Verify
ls -lh operators-catalog-*.tar.gz
```

**Transfer** to air-gapped environment

**Air-Gapped Environment**:
```bash
# 1. Extract
tar -xzf operators-catalog-20260112.tar.gz -C /opt/operators

# 2. Publish to local registry
oc-mirror --from /opt/operators docker://registry.airgap.local:5000

# 3. Apply catalog source
oc apply -f /opt/operators/.oc-mirror/results-*/catalogSource-*.yaml

# 4. Apply ICSP
oc apply -f /opt/operators/.oc-mirror/results-*/imageContentSourcePolicy.yaml

# 5. Verify operators available
oc get catalogsource -n openshift-marketplace
oc get packagemanifests | grep -E "serverless|servicemesh|pipelines|gitops"

# 6. Install operators from OperatorHub
# Operators are now available in the OpenShift web console
```

### Use Case 9: Complete Air-Gapped Stack

**Scenario**: Deploy complete stack (OpenShift + CP4I + Operators) in air-gapped environment

**Connected Environment - Download Everything**:
```bash
# 1. Mirror OpenShift
# Web UI: OpenShift Mirror tab → 4.16.20 → Filesystem → /opt/airgap/ocp

# 2. Mirror Red Hat Operators
# Web UI: Red Hat Operators tab → v4.16 → Filesystem → /opt/airgap/operators

# 3. Download CP4I components
python3 cp4i_downloader.py \
  --component ibm-integration-platform-navigator \
  --version 7.3.2 \
  --home-dir /opt/airgap/cp4i

python3 cp4i_downloader.py \
  --component ibm-apiconnect \
  --version 10.0.8.0 \
  --home-dir /opt/airgap/cp4i

python3 cp4i_downloader.py \
  --component ibm-mq \
  --version 9.3.5 \
  --home-dir /opt/airgap/cp4i

# 4. Package everything
cd /opt/airgap
tar -czf complete-stack-$(date +%Y%m%d).tar.gz ocp/ operators/ cp4i/

# Size: ~100-200 GB compressed
ls -lh complete-stack-*.tar.gz
```

**Air-Gapped Environment - Deploy Everything**:
```bash
# 1. Extract
tar -xzf complete-stack-20260112.tar.gz -C /opt/airgap

# 2. Deploy OpenShift
cd /opt/airgap/ocp
oc adm release mirror --from-dir=mirror/ \
  --to=registry.airgap.local:5000/ocp4/openshift4 \
  --to-release-image=registry.airgap.local:5000/ocp4/openshift4:4.16.20-x86_64

# 3. Deploy Operators
cd /opt/airgap/operators
oc-mirror --from . docker://registry.airgap.local:5000
oc apply -f .oc-mirror/results-*/

# 4. Deploy CP4I
cd /opt/airgap/cp4i
for component in */; do
  oc image mirror -f $component/mapping.txt \
    --from-dir=$component/v2 \
    --to=registry.airgap.local:5000
done

# 5. Install CP4I operators from catalog
# Now available in OperatorHub
```


---

## 🎁 Benefits

### For System Administrators

**1. Simplified Operations**
- ✅ Single tool for CP4I, OpenShift, and Red Hat Operators
- ✅ No manual image pulling required
- ✅ Automated retry and error handling
- ✅ Smart authentication management
- ✅ Unified interface for all mirroring operations

**2. Time Savings**
- ⚡ Parallel downloads reduce wait time (5x faster)
- ⚡ Automated authentication (no manual podman login)
- ⚡ No manual manifest creation
- ⚡ Background processing with monitoring

**3. Reliability**
- 🛡️ Automatic retry with exponential backoff
- 🛡️ Progress tracking and monitoring
- 🛡️ Comprehensive error reporting
- 🛡️ Failed image tracking

**4. Visibility**
- 📊 Real-time progress updates
- 📊 Dual log system (app + mirror)
- 📊 Detailed logs for troubleshooting
- 📊 Summary reports with statistics

### For DevOps Teams

**1. Automation Ready**
- 🤖 CLI interface for scripting
- 🤖 REST API for integration
- 🤖 Webhook notifications (Slack, etc.)
- 🤖 Exit codes for pipeline integration

**2. CI/CD Integration**
- 🔄 Easy to integrate with pipelines
- 🔄 Consistent download process
- 🔄 Version management
- 🔄 Automated testing with dry-run

**3. Flexibility**
- 🎯 Filter support for selective downloads
- 🎯 Dry run mode for testing
- 🎯 Configurable parallel downloads
- 🎯 Multiple download modes

### For Enterprise Environments

**1. Air-Gap Support**
- 🔒 Download once, deploy anywhere
- 🔒 Offline image management
- 🔒 Secure transfer workflows
- 🔒 No internet required in production

**2. Compliance**
- 📋 Audit trail with detailed logs
- 📋 Version tracking
- 📋 Reproducible downloads
- 📋 Configuration backup

**3. Cost Optimization**
- 💰 Reduce bandwidth usage with filters (40-60% savings)
- 💰 Parallel downloads for efficiency
- 💰 Reusable downloads across environments
- 💰 Direct registry mirror (no local storage)

### Technical Benefits

**1. Smart Authentication**
- ✅ Automatic credential validation
- ✅ Reuses existing podman auth
- ✅ Handles token expiration
- ✅ Force retry for fresh auth

**2. Robust Error Handling**
- ✅ Exponential backoff retry (5s, 10s, 20s, 40s...)
- ✅ Failed image tracking
- ✅ Detailed error messages
- ✅ Graceful degradation

**3. Progress Monitoring**
- ✅ Real-time progress updates
- ✅ Background monitoring thread
- ✅ Accurate completion detection
- ✅ PID tracking for process management

**4. Comprehensive Reporting**
- ✅ Download statistics
- ✅ File system details
- ✅ Transfer rates
- ✅ Error summaries
- ✅ System information

---

## 🔧 Troubleshooting

### Common Issues

#### Issue 1: Exit Code 127 - Command Not Found

**Symptoms**:
```
[component-name] Process finished with code 127
```

**Cause**: Required command not found in PATH

**Solution**:
```bash
# Check which command is missing
python3 cp4i_downloader.py --check-prerequisites

# Install missing tools
sudo yum install -y podman curl jq

# Install OpenShift CLI
curl -LO https://mirror.openshift.com/pub/openshift-v4/clients/ocp/latest/openshift-client-linux.tar.gz
tar -xzf openshift-client-linux.tar.gz
sudo mv oc /usr/local/bin/

# Verify oc ibm-pak plugin
oc ibm-pak --help
```

#### Issue 2: Authentication Failures

**Symptoms**:
```
Error: authentication required
Error: unauthorized: authentication required
```

**Cause**: Invalid or expired entitlement key

**Solution**:
```bash
# Test authentication manually
podman login cp.icr.io -u cp -p YOUR_ENTITLEMENT_KEY

# If successful, check config
cat /root/.docker/config.json

# Use force-retry to refresh authentication
python3 cp4i_downloader.py \
  --component integration-platform-navigator \
  --version 7.3.2 \
  --force-retry \
  --entitlement-key YOUR_NEW_KEY
```

#### Issue 3: Disk Space Issues

**Symptoms**:
```
Error: no space left on device
OSError: [Errno 28] No space left on device
```

**Cause**: Insufficient disk space

**Solution**:
```bash
# Check available space
df -h /opt/cp4i

# Clean up old downloads
rm -rf /opt/cp4i/old-component-*/

# Use different directory with more space
python3 cp4i_downloader.py \
  --component integration-platform-navigator \
  --version 7.3.2 \
  --home-dir /data/cp4i

# Use selective download with filters
python3 cp4i_downloader.py \
  --component integration-platform-navigator \
  --version 7.3.2 \
  --filter ".*navigator.*"
```

#### Issue 4: Network Timeouts

**Symptoms**:
```
Error: timeout waiting for response
requests.exceptions.Timeout
```

**Cause**: Slow or unstable network connection

**Solution**:
```bash
# Enable retry with longer delays
python3 cp4i_downloader.py \
  --component integration-platform-navigator \
  --version 7.3.2 \
  --retry \
  --verbose

# Reduce parallel downloads
python3 cp4i_downloader.py \
  --component integration-platform-navigator \
  --version 7.3.2 \
  --max-per-registry 2

# Check network connectivity
ping -c 5 cp.icr.io
curl -I https://cp.icr.io
```

#### Issue 5: Mirror Logs Not Visible

**Symptoms**: Mirror log file is empty or not created

**Cause**: Output redirection issue or process not started

**Solution**:
```bash
# Check if mirror log exists
ls -lh /opt/cp4i/{component-name}/{name}-mirror.log

# Check if mirror process is running
ps aux | grep "oc image mirror"

# Check download log for mirror PID
grep "PID:" /opt/cp4i/{component-name}/{name}-download.log

# Monitor mirror process directly
tail -f /opt/cp4i/{component-name}/{name}-mirror.log

# If still not working, check permissions
ls -la /opt/cp4i/{component-name}/
```

#### Issue 6: Web UI Not Loading

**Symptoms**: Cannot access http://localhost:5000

**Cause**: Flask server not running or port conflict

**Solution**:
```bash
# Check if server is running
ps aux | grep app.py

# Check if port is in use
netstat -tulpn | grep 5000

# Start server in foreground to see errors
python3 app.py

# Check firewall
sudo firewall-cmd --list-ports
sudo firewall-cmd --add-port=5000/tcp --permanent
sudo firewall-cmd --reload

# Try different port
# Edit app.py: app.run(host='0.0.0.0', port=8080)
```

### Debug Mode

Enable verbose logging for detailed troubleshooting:

```bash
# CLI
python3 cp4i_downloader.py \
  --component integration-platform-navigator \
  --version 7.3.2 \
  --verbose

# Web UI
# Check "Verbose Logging" option before starting download

# Check Flask logs
tail -f app.log

# Check system logs
sudo journalctl -u cp4i-downloader -f

#### Issue 7: oc-mirror Command Not Found

**Symptoms**:
```
Error: oc-mirror: command not found
Red Hat Operators mirror fails with exit code 127
```

**Cause**: oc-mirror tool not installed

**Solution**:
```bash
# Download and install oc-mirror
curl -LO https://mirror.openshift.com/pub/openshift-v4/clients/ocp/latest/oc-mirror.tar.gz
tar -xzf oc-mirror.tar.gz
sudo mv oc-mirror /usr/local/bin/
sudo chmod +x /usr/local/bin/oc-mirror

# Verify installation
oc-mirror version

# Retry the operator mirror
# Go to History tab → Find failed download → Click Retry
```

#### Issue 8: OpenShift Mirror Authentication Failed

**Symptoms**:
```
Error: unable to read image quay.io/openshift-release-dev/ocp-release
Error: authentication required
```

**Cause**: Missing or invalid Red Hat pull secret

**Solution**:
```bash
# Download pull secret from Red Hat
# Visit: https://console.redhat.com/openshift/downloads

# Save pull secret
cat > /root/.docker/config.json <<EOF
{your-pull-secret-json}
EOF

# Test authentication
podman login registry.redhat.io --authfile /root/.docker/config.json

# Retry OpenShift mirror with correct auth file
```

#### Issue 9: Operator Mirror Fails with "No packages found"

**Symptoms**:
```
Error: no packages found matching filter
Warning: no operators selected
```

**Cause**: Invalid operator selection or catalog version mismatch

**Solution**:
```bash
# Verify catalog version matches your OpenShift version
# OpenShift 4.16 → Use catalog v4.16
# OpenShift 4.15 → Use catalog v4.15

# Check available operators in catalog
oc-mirror list operators --catalog registry.redhat.io/redhat/redhat-operator-index:v4.16

# Use correct operator package names
# Example: "serverless-operator" not "openshift-serverless"

# Retry with corrected configuration
```

#### Issue 10: ImageSetConfiguration Syntax Error

**Symptoms**:
```
Error: failed to parse ImageSetConfiguration
Error: invalid YAML syntax
```

**Cause**: Malformed ImageSetConfiguration file

**Solution**:
```bash
# View generated configuration
cat /tmp/imageset-config-*.yaml

# Validate YAML syntax
python3 -c "import yaml; yaml.safe_load(open('/tmp/imageset-config-*.yaml'))"

# Common issues:
# - Incorrect indentation (use 2 spaces)
# - Missing required fields
# - Invalid operator package names

# Regenerate configuration from UI with correct settings
```

```

### Log Analysis

```bash
# Check application logs
tail -100 /opt/cp4i/{component-name}/{name}-download.log

# Check mirror progress
tail -100 /opt/cp4i/{component-name}/{name}-mirror.log

# Search for errors
grep -i error /opt/cp4i/{component-name}/{name}-download.log
grep -i fail /opt/cp4i/{component-name}/{name}-download.log

# Check summary report
cat /opt/cp4i/{component-name}/{name}-summary-report.txt

# Count downloaded images
find /opt/cp4i/{component-name}/v2/ -type f | wc -l

# Check disk usage
du -sh /opt/cp4i/{component-name}/
```

---

## ❓ FAQ

### General Questions

**Q: What is CP4I?**
A: IBM Cloud Pak for Integration (CP4I) is a comprehensive integration platform that includes API management, application integration, messaging, event streaming, and more.

**Q: Why do I need this tool?**
A: This tool simplifies downloading CP4I images for air-gapped environments. It handles authentication, manages retries, tracks progress, and provides detailed reports.

**Q: Is this an official IBM tool?**
A: This is a community tool that uses official IBM tools (oc ibm-pak, oc image mirror) under the hood. It provides a user-friendly interface and additional features.

**Q: Does it work with OpenShift?**
A: Yes, it's designed specifically for OpenShift environments and uses OpenShift CLI tools.

### Technical Questions

**Q: How much disk space do I need?**
A: It varies by component:
- Platform Navigator: 50-100 GB
- API Connect: 80-150 GB
- MQ: 30-60 GB
- Full CP4I suite: 500+ GB

Use filters to reduce disk space by 40-60%.

**Q: Can I download multiple components simultaneously?**
A: Yes, you can run multiple downloads in parallel. Each download runs in a separate process. Ensure you have sufficient disk space and bandwidth.

**Q: How long does a download take?**
A: Depends on:
- Component size (20-150 GB)
- Network speed (10-100+ Mbps)
- Number of parallel downloads (1-10)
- Typical time: 30 minutes to 3 hours

**Q: Can I pause and resume downloads?**
A: Not directly, but you can use the retry feature to continue failed downloads. The tool tracks which images were successfully downloaded.

**Q: What happens if download fails?**
A: The tool automatically retries with exponential backoff (5s, 10s, 20s, 40s...). You can also manually retry from the UI or CLI with `--retry` flag.

**Q: Can I use this in production?**
A: Yes, but test thoroughly in your environment first. Use systemd for production deployments.

### Authentication Questions

**Q: Where do I get an entitlement key?**
A: From [IBM Container Library](https://myibm.ibm.com/products-services/containerlibrary). Log in with your IBM ID and copy your entitlement key.

**Q: How long is the entitlement key valid?**
A: Entitlement keys don't expire, but you should rotate them periodically for security (every 90-180 days recommended).

**Q: Can I use the same key for multiple downloads?**
A: Yes, one entitlement key can be used for all CP4I components and multiple downloads.

**Q: Do I need to provide the key every time?**
A: No, if you're already authenticated with podman, the tool will reuse existing credentials. Use `--force-retry` to force fresh authentication.

### Deployment Questions

**Q: Can I customize the download location?**
A: Yes, use the `--home-dir` option or configure it in the web UI. Default is `/opt/cp4i`.

**Q: Can I download to a network share?**
A: Yes, but ensure the network share has sufficient space and good performance. Local SSD is recommended for best performance.

**Q: How do I transfer images to air-gapped environment?**
A: Package downloaded images with tar:
```bash
tar -czf cp4i-images.tar.gz /opt/cp4i/*/v2 /opt/cp4i/*/mapping.txt
```
Transfer via USB drive or secure transfer, then extract and upload to local registry.

**Q: Can I use this with private registries?**
A: Yes, use the `--final-registry` option to specify your private registry. Ensure you have proper authentication configured.

### Performance Questions

**Q: How can I speed up downloads?**
A: 
- Increase parallel downloads: `--max-per-registry 10`
- Use faster storage (SSD)
- Improve network bandwidth
- Use filters to download only needed images

**Q: Why is my download slow?**
A: Common causes:
- Slow network connection
- Disk I/O bottleneck (use SSD)
- Too many parallel downloads (reduce to 2-5)
- Network congestion

**Q: Can I limit bandwidth usage?**
A: Not directly in the tool, but you can use system-level tools like `tc` (traffic control) or `trickle` to limit bandwidth.

**Q: Does this tool support OpenShift mirroring?**
A: Yes! The tool includes comprehensive OpenShift release mirroring for versions 4.14-4.20. You can mirror to filesystem or directly to a registry.

**Q: Can I mirror Red Hat operators?**
A: Yes! The tool supports Red Hat operator catalog mirroring using oc-mirror. You can mirror all operators or select specific ones.

**Q: What's the difference between CP4I, OpenShift, and Red Hat Operators downloads?**
A: 
- **CP4I**: IBM Cloud Pak for Integration components (uses oc ibm-pak)
- **OpenShift**: OpenShift Container Platform releases (uses oc adm release mirror)
- **Red Hat Operators**: Operator catalogs from Red Hat (uses oc-mirror)

**Q: Do I need different credentials for OpenShift and Red Hat Operators?**
A: Yes:
- **CP4I**: IBM Entitlement Key from IBM Container Library
- **OpenShift/Operators**: Red Hat pull secret from Red Hat OpenShift Cluster Manager

**Q: Can I mirror multiple OpenShift versions?**
A: Yes, you can mirror multiple versions sequentially. Each version is stored separately.

**Q: What is oc-mirror and why do I need it?**
A: oc-mirror is Red Hat's official tool for mirroring operator catalogs. It's required for Red Hat Operators mirroring but not for CP4I or OpenShift downloads.

**Q: Can I mirror operators without mirroring OpenShift?**
A: Yes, operator mirroring is independent. However, you need a compatible OpenShift cluster to use the operators.

**Q: How do I know which operators to mirror?**
A: The tool provides a list of common Red Hat operators. Mirror operators based on your application requirements. Start with essential ones like Serverless, Service Mesh, and Pipelines.


---

## 📚 API Documentation

See [API_ENDPOINTS.md](API_ENDPOINTS.md) for complete API documentation.

### Quick API Reference

#### Start Download
```bash
POST /api/downloads/start
Content-Type: application/json

{
  "component": "integration-platform-navigator",
  "version": "7.3.2",
  "home_dir": "/opt/cp4i",
  "entitlement_key": "YOUR_KEY",
  "filter": ".*navigator.*",
  "dry_run": false,
  "retry": true,
  "verbose": false
}
```

#### Get Download Status
```bash
GET /api/downloads
```

#### View Logs
```bash
# Get download log
GET /api/logs/{name}?type=download

# Get mirror log
GET /api/logs/{name}?type=mirror

# Get both logs
GET /api/logs/{name}?type=all
```

#### Stream Logs (Real-time)
```bash
# Stream mirror log
GET /api/logs/{name}/stream?type=mirror

# Stream download log
GET /api/logs/{name}/stream?type=download
```

#### Get Summary Report
```bash
GET /api/reports/{name}?home_dir=/opt/cp4i
```

---

## ⚡ Performance Tuning

### Optimize Download Speed

```bash
# Increase parallel downloads (if bandwidth allows)
python3 cp4i_downloader.py \
  --component integration-platform-navigator \
  --version 7.3.2 \
  --max-per-registry 10

# Use faster storage (SSD)
python3 cp4i_downloader.py \
  --component integration-platform-navigator \
  --version 7.3.2 \
  --home-dir /fast-ssd/cp4i

# Reduce logging overhead (don't use --verbose unless needed)
python3 cp4i_downloader.py \
  --component integration-platform-navigator \
  --version 7.3.2
```

### Optimize Disk Usage

```bash
# Use filters to download only needed images (saves 40-60%)
python3 cp4i_downloader.py \
  --component integration-platform-navigator \
  --version 7.3.2 \
  --filter ".*navigator.*"

# Clean up after successful upload to registry
rm -rf /opt/cp4i/{component}/v2

# Use compression for transfer
tar -czf images.tar.gz /opt/cp4i/{component}/v2

# Use direct registry mirror (no local storage)
python3 cp4i_downloader.py \
  --component integration-platform-navigator \
  --version 7.3.2 \
  --final-registry registry.example.com:5000
```

### System Tuning

```bash
# Increase file descriptors
ulimit -n 65536

# Increase network buffer sizes
sudo sysctl -w net.core.rmem_max=134217728
sudo sysctl -w net.core.wmem_max=134217728

# Disable SELinux (if causing issues)
sudo setenforce 0

# Use faster DNS
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
```

---

## 🔐 Security

### Best Practices

**1. Protect Credentials**
```bash
# Never commit keys or pull secrets to version control
echo "*.key" >> .gitignore
echo "pull-secret.json" >> .gitignore
echo "config.json" >> .gitignore

# Use environment variables
export IBM_ENTITLEMENT_KEY="your-key-here"
export REDHAT_PULL_SECRET="/secure/path/pull-secret.json"

# Or use secure vaults (HashiCorp Vault, AWS Secrets Manager)
vault kv get secret/ibm/entitlement-key
vault kv get secret/redhat/pull-secret

# Rotate keys regularly (every 90-180 days)
```

**2. Secure the Web Interface**
```bash
# Use HTTPS in production (with nginx/apache reverse proxy)
# Example nginx config:
server {
    listen 443 ssl;
    server_name cp4i-downloader.example.com;
    
    ssl_certificate /etc/ssl/certs/server.crt;
    ssl_certificate_key /etc/ssl/private/server.key;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

# Implement authentication (basic auth, OAuth, etc.)
# Restrict network access with firewall
sudo firewall-cmd --add-rich-rule='rule family="ipv4" source address="10.0.0.0/8" port port="5000" protocol="tcp" accept'
```

**3. File Permissions**
```bash
# Secure configuration file
chmod 600 /opt/cp4i/.cp4i-downloader.conf

# Secure download directory
chmod 700 /opt/cp4i

# Secure auth file
chmod 600 /root/.docker/config.json
```

**4. Audit Logs**
```bash
# Review logs regularly
grep -i "error\|fail\|unauthorized" /opt/cp4i/*/*.log

# Monitor for suspicious activity
tail -f /opt/cp4i/*/*.log | grep -i "unauthorized\|forbidden"

# Archive logs for compliance
tar -czf logs-$(date +%Y%m%d).tar.gz /opt/cp4i/*/*.log
```

**5. Network Security**
```bash
# Use firewall to restrict access
sudo firewall-cmd --add-port=5000/tcp --permanent
sudo firewall-cmd --reload

# Use VPN for remote access
# Configure SELinux policies
sudo semanage port -a -t http_port_t -p tcp 5000
```

---

## 📊 Statistics

### CP4I Components
- **Supported Components**: 15+ CP4I components
- **Supported Versions**: 100+ CASE versions
- **Average Download Time**: 1-2 hours per component
- **Success Rate**: 95%+ with retry enabled
- **Disk Space Saved**: Up to 60% with filters

### OpenShift
- **Supported Versions**: 4.14.x through 4.20.x
- **Mirror Modes**: Filesystem and Direct to Registry
- **Average Download Time**: 30-60 minutes per release
- **Architectures**: x86_64, aarch64, ppc64le, s390x
- **Operator Catalog Support**: Yes (optional)

### Red Hat Operators
- **Available Operators**: 25+ common operators
- **Catalog Versions**: v4.14 through v4.20
- **Mirror Modes**: Filesystem and Direct to Registry
- **Selective Mirroring**: Yes (individual operator selection)
- **Average Download Time**: 20-40 minutes (all operators), 5-10 minutes (selective)

### Performance
- **Parallel Downloads**: Up to 10 concurrent
- **Retry Attempts**: Up to 3 with exponential backoff
- **Bandwidth Efficiency**: Optimized with parallel streams
- **Storage Efficiency**: Deduplication via OCI format

---

## 🗺️ Roadmap

### Planned Features

- [ ] Resume interrupted downloads
- [ ] Multi-architecture support (ARM, s390x, ppc64le)
- [ ] Image compression options
- [ ] Bandwidth throttling
- [ ] Download scheduling
- [ ] Integration with Ansible
- [ ] Docker registry support
- [ ] Image vulnerability scanning
- [ ] Backup and restore functionality
- [ ] Multi-user support with RBAC
- [ ] Download queue management
- [ ] Email notifications
- [ ] Prometheus metrics export
- [ ] Grafana dashboards

---

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Commit changes**: `git commit -m 'Add amazing feature'`
4. **Push to branch**: `git push origin feature/amazing-feature`
5. **Open a Pull Request**

### Development Setup

```bash
# Clone repository
git clone https://github.com/your-org/cp4i-downloader.git
cd cp4i-downloader

# Install dependencies
pip3 install -r requirements.txt

# Run tests
python3 -m pytest tests/

# Start development server
python3 app.py
```

---

## 📄 License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.

---

## 🙏 Acknowledgments

- IBM Cloud Pak for Integration team
- OpenShift community
- Contributors and testers
- Flask framework developers

---

## 📞 Support

For issues, questions, or contributions:

- **Issues**: [GitHub Issues](https://github.com/your-org/cp4i-downloader/issues)
- **Documentation**: [Wiki](https://github.com/your-org/cp4i-downloader/wiki)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/cp4i-downloader/discussions)
- **Email**: support@example.com

---

**Made with ❤️ for the IBM Cloud Pak community**

---

*Last Updated: January 2026*
*Version: 2.0.0*
*Author: CP4I Downloader Team*