#!/usr/bin/env python3
"""
Live Data Fetcher for CP4I Downloader
Fetches real-time version and support matrix data from IBM and Red Hat sources
"""

import json
import os
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LiveDataFetcher:
    """Fetches live version and support data from external sources"""
    
    def __init__(self, config_file='live_data_config.json'):
        """Initialize the live data fetcher"""
        self.config = self._load_config(config_file)
        self.cache_dir = self.config.get('cache', {}).get('directory', '.cache')
        self.cache_enabled = self.config.get('cache', {}).get('enabled', True)
        self.cache_max_age = self.config.get('cache', {}).get('max_age_hours', 24)
        
        # Create cache directory if it doesn't exist
        if self.cache_enabled and not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
    
    def _load_config(self, config_file: str) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {}
    
    def _get_cache_path(self, cache_key: str) -> str:
        """Get cache file path for a given key"""
        return os.path.join(self.cache_dir, f"{cache_key}.json")
    
    def _is_cache_valid(self, cache_path: str) -> bool:
        """Check if cache file is still valid"""
        if not os.path.exists(cache_path):
            return False
        
        file_time = datetime.fromtimestamp(os.path.getmtime(cache_path))
        max_age = timedelta(hours=self.cache_max_age)
        
        return datetime.now() - file_time < max_age
    
    def _read_cache(self, cache_key: str) -> Optional[Dict]:
        """Read data from cache"""
        if not self.cache_enabled:
            return None
        
        cache_path = self._get_cache_path(cache_key)
        
        if self._is_cache_valid(cache_path):
            try:
                with open(cache_path, 'r') as f:
                    logger.info(f"Using cached data for {cache_key}")
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read cache: {e}")
        
        return None
    
    def _write_cache(self, cache_key: str, data: Dict) -> None:
        """Write data to cache"""
        if not self.cache_enabled:
            return
        
        cache_path = self._get_cache_path(cache_key)
        
        try:
            with open(cache_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Cached data for {cache_key}")
        except Exception as e:
            logger.warning(f"Failed to write cache: {e}")
    
    def _make_request(self, url: str, timeout: int = 30, headers: Optional[Dict] = None) -> Optional[Dict]:
        """Make HTTP request with retry logic"""
        retry_attempts = self.config.get('data_sources', {}).get('ibm_registry', {}).get('retry_attempts', 3)
        
        for attempt in range(retry_attempts):
            try:
                logger.info(f"Fetching data from {url} (attempt {attempt + 1}/{retry_attempts})")
                response = requests.get(url, timeout=timeout, headers=headers or {})
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt < retry_attempts - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"All retry attempts failed for {url}")
        
        return None
    
    def fetch_ibm_case_versions(self, component: str) -> Optional[List[str]]:
        """Fetch available versions for an IBM component from GitHub CASE repository"""
        cache_key = f"ibm_case_{component}"
        
        # Check cache first
        cached_data = self._read_cache(cache_key)
        if cached_data:
            return cached_data.get('versions', [])
        
        # Fetch from GitHub API
        github_config = self.config.get('data_sources', {}).get('github_sources', {})
        if not github_config.get('enabled', False):
            return None
        
        component_config = self.config.get('components', {}).get(component, {})
        case_name = component_config.get('case_name', component)
        
        base_url = github_config.get('ibm_case_repo', '')
        url = f"{base_url}/{case_name}"
        
        data = self._make_request(url, timeout=github_config.get('timeout', 30))
        
        if data and isinstance(data, list):
            # Extract version directories
            versions = []
            for item in data:
                if item.get('type') == 'dir':
                    version = item.get('name', '')
                    # Filter out non-version directories
                    if version and version[0].isdigit():
                        versions.append(version)
            
            versions.sort(reverse=True)  # Sort versions in descending order
            
            # Cache the result
            cache_data = {
                'versions': versions,
                'fetched_at': datetime.now().isoformat()
            }
            self._write_cache(cache_key, cache_data)
            
            return versions
        
        return None
    
    def fetch_case_version_details(self, component: str, version: str) -> Optional[Dict]:
        """Fetch detailed information for a specific CASE version from GitHub"""
        cache_key = f"ibm_case_details_{component}_{version}"
        
        # Check cache first
        cached_data = self._read_cache(cache_key)
        if cached_data:
            return cached_data
        
        # Fetch from GitHub API
        github_config = self.config.get('data_sources', {}).get('github_sources', {})
        if not github_config.get('enabled', False):
            return None
        
        component_config = self.config.get('components', {}).get(component, {})
        case_name = component_config.get('case_name', component)
        
        base_url = github_config.get('ibm_case_repo', '')
        
        # Fetch case.yaml file for the version
        case_yaml_url = f"{base_url}/{case_name}/{version}/case.yaml"
        
        try:
            import requests
            response = requests.get(case_yaml_url, timeout=30)
            if response.status_code == 200:
                # Parse YAML content
                import yaml
                case_data = yaml.safe_load(response.text)
                
                # Extract relevant information
                details = {
                    'case_version': version,
                    'name': case_data.get('name', case_name),
                    'description': case_data.get('description', ''),
                    'version': case_data.get('version', version),
                    'appVersion': case_data.get('appVersion', ''),
                    'webPage': case_data.get('webPage', ''),
                    'licenses': case_data.get('licenses', []),
                    'supports': case_data.get('supports', {}),
                    'fetched_at': datetime.now().isoformat()
                }
                
                # Cache the result
                self._write_cache(cache_key, details)
                
                return details
        except Exception as e:
            logger.error(f"Failed to fetch CASE details for {component} {version}: {e}")
        
        return None
    
    def fetch_openshift_versions(self, channel: str = 'stable-4.20') -> Optional[List[Dict]]:
        """Fetch available OpenShift versions from Red Hat API"""
        cache_key = f"openshift_{channel}"
        
        # Check cache first
        cached_data = self._read_cache(cache_key)
        if cached_data:
            return cached_data.get('versions', [])
        
        # Fetch from Red Hat API
        redhat_config = self.config.get('data_sources', {}).get('redhat_registry', {})
        if not redhat_config.get('enabled', False):
            return None
        
        base_url = redhat_config.get('openshift_releases', '')
        url = f"{base_url}?channel={channel}"
        
        data = self._make_request(url, timeout=redhat_config.get('timeout', 30))
        
        if data and 'nodes' in data:
            versions = []
            for node in data['nodes']:
                version_info = {
                    'version': node.get('version', ''),
                    'release_date': node.get('metadata', {}).get('creationTimestamp', ''),
                    'channel': channel
                }
                versions.append(version_info)
            
            # Cache the result
            cache_data = {
                'versions': versions,
                'fetched_at': datetime.now().isoformat()
            }
            self._write_cache(cache_key, cache_data)
            
            return versions
        
        return None
    
    def fetch_redhat_operators(self) -> Optional[List[Dict]]:
        """Fetch available Red Hat operators from catalog"""
        cache_key = "redhat_operators"
        
        # Check cache first
        cached_data = self._read_cache(cache_key)
        if cached_data:
            return cached_data.get('operators', [])
        
        # Fetch from Red Hat Operator Catalog
        redhat_config = self.config.get('data_sources', {}).get('redhat_registry', {})
        if not redhat_config.get('enabled', False):
            return None
        
        # List of common Red Hat operators for OpenShift
        operators = [
            {
                "name": "Red Hat OpenShift Serverless",
                "package": "serverless-operator",
                "catalog": "redhat-operators",
                "description": "Provides Knative Serving and Eventing capabilities"
            },
            {
                "name": "Red Hat OpenShift Service Mesh",
                "package": "servicemeshoperator",
                "catalog": "redhat-operators",
                "description": "Service mesh based on Istio"
            },
            {
                "name": "Red Hat OpenShift Pipelines",
                "package": "openshift-pipelines-operator-rh",
                "catalog": "redhat-operators",
                "description": "CI/CD solution based on Tekton"
            },
            {
                "name": "Red Hat OpenShift GitOps",
                "package": "openshift-gitops-operator",
                "catalog": "redhat-operators",
                "description": "GitOps solution based on Argo CD"
            },
            {
                "name": "Red Hat OpenShift Logging",
                "package": "cluster-logging",
                "catalog": "redhat-operators",
                "description": "Cluster logging based on Elasticsearch, Fluentd, and Kibana"
            },
            {
                "name": "Red Hat OpenShift Elasticsearch Operator",
                "package": "elasticsearch-operator",
                "catalog": "redhat-operators",
                "description": "Elasticsearch cluster management"
            },
            {
                "name": "Red Hat OpenShift distributed tracing platform",
                "package": "jaeger-product",
                "catalog": "redhat-operators",
                "description": "Distributed tracing based on Jaeger"
            },
            {
                "name": "Red Hat OpenShift distributed tracing data collection",
                "package": "opentelemetry-product",
                "catalog": "redhat-operators",
                "description": "OpenTelemetry Collector for distributed tracing"
            },
            {
                "name": "Kiali Operator",
                "package": "kiali-ossm",
                "catalog": "redhat-operators",
                "description": "Service mesh observability"
            },
            {
                "name": "Red Hat Integration - AMQ Streams",
                "package": "amq-streams",
                "catalog": "redhat-operators",
                "description": "Apache Kafka on OpenShift"
            },
            {
                "name": "Red Hat Integration - AMQ Broker",
                "package": "amq-broker-rhel8",
                "catalog": "redhat-operators",
                "description": "ActiveMQ Artemis messaging broker"
            },
            {
                "name": "Red Hat Integration - 3scale",
                "package": "3scale-operator",
                "catalog": "redhat-operators",
                "description": "API management platform"
            },
            {
                "name": "Red Hat Integration - Camel K",
                "package": "red-hat-camel-k",
                "catalog": "redhat-operators",
                "description": "Lightweight integration framework"
            },
            {
                "name": "Red Hat OpenShift Data Foundation",
                "package": "odf-operator",
                "catalog": "redhat-operators",
                "description": "Software-defined storage solution"
            },
            {
                "name": "Red Hat Advanced Cluster Security",
                "package": "rhacs-operator",
                "catalog": "redhat-operators",
                "description": "Kubernetes-native security platform"
            },
            {
                "name": "Red Hat Quay",
                "package": "quay-operator",
                "catalog": "redhat-operators",
                "description": "Container image registry"
            },
            {
                "name": "Red Hat OpenShift Dev Spaces",
                "package": "devspaces",
                "catalog": "redhat-operators",
                "description": "Cloud development environment"
            },
            {
                "name": "Web Terminal",
                "package": "web-terminal",
                "catalog": "redhat-operators",
                "description": "Terminal access from OpenShift console"
            },
            {
                "name": "Red Hat Compliance Operator",
                "package": "compliance-operator",
                "catalog": "redhat-operators",
                "description": "Compliance scanning and remediation"
            },
            {
                "name": "File Integrity Operator",
                "package": "file-integrity-operator",
                "catalog": "redhat-operators",
                "description": "File integrity monitoring"
            },
            {
                "name": "Red Hat OpenShift Local Storage",
                "package": "local-storage-operator",
                "catalog": "redhat-operators",
                "description": "Local storage management"
            },
            {
                "name": "Red Hat OpenShift Virtualization",
                "package": "kubevirt-hyperconverged",
                "catalog": "redhat-operators",
                "description": "Virtual machine management on OpenShift"
            },
            {
                "name": "Red Hat Cost Management Metrics Operator",
                "package": "costmanagement-metrics-operator",
                "catalog": "redhat-operators",
                "description": "Cost management and optimization"
            },
            {
                "name": "Node Maintenance Operator",
                "package": "node-maintenance-operator",
                "catalog": "redhat-operators",
                "description": "Node maintenance and cordoning"
            },
            {
                "name": "Poison Pill Operator",
                "package": "poison-pill-manager",
                "catalog": "redhat-operators",
                "description": "Node remediation for unhealthy nodes"
            }
        ]
        
        # Cache the result
        cache_data = {
            'operators': operators,
            'fetched_at': datetime.now().isoformat()
        }
        self._write_cache(cache_key, cache_data)
        
        return operators
    
    def fetch_component_support_matrix(self, component: str, version: str) -> Optional[Dict]:
        """Fetch support matrix for a specific component version"""
        cache_key = f"support_matrix_{component}_{version}"
        
        # Check cache first
        cached_data = self._read_cache(cache_key)
        if cached_data:
            return cached_data
        
        # In a real implementation, this would fetch from IBM's support matrix API
        # For now, we'll use the local data as fallback
        logger.info(f"Support matrix API not yet available, using local data for {component} {version}")
        
        return None
    
    def get_all_component_versions(self) -> Dict[str, List[str]]:
        """Get all available versions for all components"""
        result = {}
        
        components = self.config.get('components', {})
        for component_name in components.keys():
            versions = self.fetch_ibm_case_versions(component_name)
            if versions:
                result[component_name] = versions
            else:
                # Fallback to local data
                logger.info(f"Using local data for {component_name}")
                result[component_name] = self._get_local_versions(component_name)
        
        return result
    
    def get_all_openshift_versions(self) -> Dict[str, List[Dict]]:
        """Get all available OpenShift versions for all channels"""
        result = {}
        
        channels = self.config.get('openshift', {}).get('channels', [])
        for channel in channels:
            versions = self.fetch_openshift_versions(channel)
            if versions:
                result[channel] = versions
            else:
                # Fallback to local data
                logger.info(f"Using local data for OpenShift {channel}")
                result[channel] = self._get_local_openshift_versions(channel)
        
        return result
    
    def _get_local_versions(self, component: str) -> List[str]:
        """Get versions from local sample-versions.json file"""
        fallback_config = self.config.get('fallback', {})
        local_file = fallback_config.get('local_versions_file', 'sample-versions.json')
        
        try:
            with open(local_file, 'r') as f:
                data = json.load(f)
                return data.get(component, [])
        except Exception as e:
            logger.error(f"Failed to read local versions: {e}")
            return []
    
    def _get_local_openshift_versions(self, channel: str) -> List[Dict]:
        """Get OpenShift versions from local cp4i_version_data.json file"""
        fallback_config = self.config.get('fallback', {})
        local_file = fallback_config.get('local_version_file', 'cp4i_version_data.json')
        
        try:
            with open(local_file, 'r') as f:
                data = json.load(f)
                openshift_data = data.get('openshift_versions', {})
                
                versions = []
                for version, info in openshift_data.items():
                    versions.append({
                        'version': version,
                        'release_date': info.get('release_date', ''),
                        'end_of_support': info.get('end_of_support', ''),
                        'status': info.get('status', ''),
                        'is_eus': info.get('is_eus', False),
                        'channel': channel
                    })
                
                return versions
        except Exception as e:
            logger.error(f"Failed to read local OpenShift versions: {e}")
            return []
    
    def refresh_all_data(self) -> Dict[str, Any]:
        """Refresh all data from live sources"""
        logger.info("Refreshing all data from live sources...")
        
        result = {
            'components': self.get_all_component_versions(),
            'openshift': self.get_all_openshift_versions(),
            'refreshed_at': datetime.now().isoformat()
        }
        
        # Save consolidated data
        consolidated_cache_path = os.path.join(self.cache_dir, 'consolidated_data.json')
        try:
            with open(consolidated_cache_path, 'w') as f:
                json.dump(result, f, indent=2)
            logger.info("Consolidated data saved successfully")
        except Exception as e:
            logger.error(f"Failed to save consolidated data: {e}")
        
        return result
    
    def clear_cache(self) -> None:
        """Clear all cached data"""
        if not self.cache_enabled or not os.path.exists(self.cache_dir):
            return
        
        try:
            for filename in os.listdir(self.cache_dir):
                file_path = os.path.join(self.cache_dir, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            logger.info("Cache cleared successfully")
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")


# CLI interface for testing
if __name__ == '__main__':
    import sys
    
    fetcher = LiveDataFetcher()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'refresh':
            print("Refreshing all data...")
            data = fetcher.refresh_all_data()
            print(json.dumps(data, indent=2))
        
        elif command == 'clear-cache':
            print("Clearing cache...")
            fetcher.clear_cache()
            print("Cache cleared")
        
        elif command == 'component' and len(sys.argv) > 2:
            component = sys.argv[2]
            print(f"Fetching versions for {component}...")
            versions = fetcher.fetch_ibm_case_versions(component)
            print(json.dumps(versions, indent=2))
        
        elif command == 'openshift' and len(sys.argv) > 2:
            channel = sys.argv[2]
            print(f"Fetching OpenShift versions for {channel}...")
            versions = fetcher.fetch_openshift_versions(channel)
            print(json.dumps(versions, indent=2))
        
        else:
            print("Unknown command")
            print("Usage:")
            print("  python live_data_fetcher.py refresh")
            print("  python live_data_fetcher.py clear-cache")
            print("  python live_data_fetcher.py component <component-name>")
            print("  python live_data_fetcher.py openshift <channel>")
    else:
        print("Live Data Fetcher for CP4I Downloader")
        print("Usage:")
        print("  python live_data_fetcher.py refresh")
        print("  python live_data_fetcher.py clear-cache")
        print("  python live_data_fetcher.py component <component-name>")
        print("  python live_data_fetcher.py openshift <channel>")

# Made with Bob
