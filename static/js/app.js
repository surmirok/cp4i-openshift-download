// CP4I Downloader - Web Interface JavaScript

// API Base URL
const API_BASE = '/api';

// Global state
let components = [];
let activeDownloads = [];
let downloadHistory = [];
let refreshInterval = null;

// Utility Functions
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    loadComponents();
    loadDownloads();
    startAutoRefresh();
});

// Tab Management
function showTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Remove active class from all buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected tab
    document.getElementById(tabName).classList.add('active');
    
    // Add active class to clicked button
    event.target.closest('.tab-btn').classList.add('active');
    
    // Reset form when switching to new-download tab
    if (tabName === 'new-download') {
        resetDownloadForm();
    }
    
    // Refresh data for the tab
    if (tabName === 'active-downloads' || tabName === 'history') {
        loadDownloads();
    }
}

// Reset download form to blank state
function resetDownloadForm() {
    const form = document.getElementById('download-form');
    if (form) {
        form.reset();
        // Clear component info display
        document.getElementById('component-info').style.display = 'none';
        // Reset component select to placeholder
        document.getElementById('component').selectedIndex = 0;
    }
}

// Load Components
async function loadComponents() {
    try {
        const response = await fetch(`${API_BASE}/components`);
        const data = await response.json();
        components = data.components;
        
        const select = document.getElementById('component');
        select.innerHTML = '<option value="">Select a component...</option>';
        
        components.forEach(comp => {
            const option = document.createElement('option');
            option.value = comp.name;
            option.textContent = `${comp.description} (${comp.typical_size})`;
            option.dataset.component = JSON.stringify(comp);
            select.appendChild(option);
        });
    } catch (error) {
        showToast('Failed to load components', 'error');
        console.error(error);
    }
}

// Update Versions
async function updateVersions() {
    const componentSelect = document.getElementById('component');
    const versionInput = document.getElementById('version');
    const versionDatalist = document.getElementById('version-list');
    const nameInput = document.getElementById('name');
    const filterInput = document.getElementById('filter');
    const selectedOption = componentSelect.options[componentSelect.selectedIndex];
    
    // Clear all fields when component changes
    versionInput.value = '';
    nameInput.value = '';
    if (filterInput) filterInput.value = '';
    
    if (!selectedOption.dataset.component) {
        versionDatalist.innerHTML = '';
        document.getElementById('component-info').style.display = 'none';
        document.getElementById('version-lifecycle').style.display = 'none';
        document.getElementById('compatibility-matrix').style.display = 'none';
        return;
    }
    
    const component = JSON.parse(selectedOption.dataset.component);
    
    // Show loading indicator
    const infoDiv = document.getElementById('component-info');
    const detailsDiv = document.getElementById('component-details');
    detailsDiv.innerHTML = `
        <div class="info-box" style="text-align: center; padding: 30px;">
            <i class="fas fa-spinner fa-spin" style="font-size: 2rem; color: var(--primary-color);"></i>
            <p style="margin-top: 15px; color: var(--text-secondary);">Fetching latest version information...</p>
        </div>
    `;
    infoDiv.style.display = 'block';
    
    // Fetch CASE versions with instance version details (try live data first)
    try {
        // Try to fetch live data first
        let response = await fetch(`${API_BASE}/live/component-versions/${component.name}`);
        let liveData = null;
        let dataSource = 'local';
        
        if (response.ok) {
            liveData = await response.json();
            if (liveData.success && liveData.versions && liveData.versions.length > 0) {
                dataSource = liveData.source || 'live';
                console.log(`Using ${dataSource} data for ${component.name}`);
            }
        }
        
        // Fetch detailed version info (with lifecycle and compatibility)
        response = await fetch(`${API_BASE}/version-info/${component.name}`);
        const data = await response.json();
        
        if (response.ok && data.versions) {
            // Update version datalist with CASE versions only
            versionDatalist.innerHTML = '';
            
            // Sort versions by release date (newest first)
            const sortedVersions = Object.entries(data.versions)
                .sort((a, b) => new Date(b[1].release_date) - new Date(a[1].release_date));
            
            sortedVersions.forEach(([caseVersion, info]) => {
                const option = document.createElement('option');
                option.value = caseVersion;
                // Add label showing if it's LTS
                const label = info.is_lts ? ` (LTS - ${caseVersion})` : ` (${caseVersion})`;
                option.label = `CASE ${caseVersion}${info.is_lts ? ' ⭐ LTS' : ''}`;
                versionDatalist.appendChild(option);
            });
            
            // Show component info with CASE version details
            const infoDiv = document.getElementById('component-info');
            const detailsDiv = document.getElementById('component-details');
            
            // Determine data source badge
            let sourceBadge = '';
            if (dataSource === 'live') {
                sourceBadge = '<span style="background: var(--success-color); color: white; padding: 3px 8px; border-radius: 3px; font-size: 0.75rem; margin-left: 10px;"><i class="fas fa-cloud"></i> Live Data</span>';
            } else if (dataSource === 'local_fallback') {
                sourceBadge = '<span style="background: var(--warning-color); color: white; padding: 3px 8px; border-radius: 3px; font-size: 0.75rem; margin-left: 10px;"><i class="fas fa-database"></i> Cached Data</span>';
            } else {
                sourceBadge = '<span style="background: var(--info-color); color: white; padding: 3px 8px; border-radius: 3px; font-size: 0.75rem; margin-left: 10px;"><i class="fas fa-database"></i> Local Data</span>';
            }
            
            let caseVersionsHtml = '<div class="info-box">';
            caseVersionsHtml += `<p><strong>Component:</strong> ${component.description} ${sourceBadge}</p>`;
            caseVersionsHtml += `<p><strong>Name:</strong> ${component.name}</p>`;
            caseVersionsHtml += `<p><strong>Typical Size:</strong> ${component.typical_size}</p>`;
            caseVersionsHtml += '<hr style="margin: 15px 0; border: none; border-top: 1px solid var(--border-color);">';
            caseVersionsHtml += '<h4 style="margin-top: 0; color: var(--primary-color);"><i class="fas fa-box"></i> Available CASE Versions</h4>';
            caseVersionsHtml += '<p style="font-size: 0.9rem; color: var(--text-secondary);">Select a CASE version to download. Each CASE version includes specific instance versions.</p>';
            
            // Display CASE versions with instance version details
            caseVersionsHtml += '<table style="width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 0.9rem;">';
            caseVersionsHtml += '<tr style="background: var(--bg-secondary); font-weight: bold;">';
            caseVersionsHtml += '<td style="padding: 8px; border: 1px solid var(--border-color);">CASE Version</td>';
            caseVersionsHtml += '<td style="padding: 8px; border: 1px solid var(--border-color);">Instance Versions</td>';
            caseVersionsHtml += '<td style="padding: 8px; border: 1px solid var(--border-color);">Status</td>';
            caseVersionsHtml += '<td style="padding: 8px; border: 1px solid var(--border-color);">Size</td>';
            caseVersionsHtml += '</tr>';
            
            sortedVersions.forEach(([caseVersion, info]) => {
                const statusColor = info.status === 'supported' ? 'var(--success-color)' : 'var(--danger-color)';
                const statusIcon = info.status === 'supported' ? '<i class="fas fa-check-circle"></i>' : '<i class="fas fa-exclamation-triangle"></i>';
                const ltsIcon = info.is_lts ? ' <i class="fas fa-star" style="color: gold;" title="Long Term Support"></i>' : '';
                
                // Get instance versions (if available in data)
                const instanceVersions = info.instance_versions || [caseVersion];
                const instanceVersionsText = instanceVersions.join(', ');
                
                caseVersionsHtml += `<tr>
                    <td style="padding: 8px; border: 1px solid var(--border-color);"><strong>${caseVersion}</strong>${ltsIcon}</td>
                    <td style="padding: 8px; border: 1px solid var(--border-color);">${instanceVersionsText}</td>
                    <td style="padding: 8px; border: 1px solid var(--border-color); color: ${statusColor};">${statusIcon} ${info.status}</td>
                    <td style="padding: 8px; border: 1px solid var(--border-color);">${info.size_gb || component.typical_size} GB</td>
                </tr>`;
            });
            
            caseVersionsHtml += '</table>';
            caseVersionsHtml += '<p style="margin-top: 15px; font-size: 0.85rem; color: var(--text-secondary);"><i class="fas fa-info-circle"></i> <strong>Note:</strong> CASE versions are used for downloading. Instance versions are the actual component versions included in the CASE bundle.</p>';
            caseVersionsHtml += '</div>';
            
            detailsDiv.innerHTML = caseVersionsHtml;
            infoDiv.style.display = 'block';
            
            // Load and display version lifecycle information
            await loadVersionLifecycle(component.name);
            displayCompatibilityMatrix(data);
        }
    } catch (error) {
        console.error('Failed to load version information:', error);
        // Fallback to basic version list
        versionDatalist.innerHTML = '';
        component.versions.forEach(version => {
            const option = document.createElement('option');
            option.value = version;
            versionDatalist.appendChild(option);
        });
        
        // Show basic component info
        const infoDiv = document.getElementById('component-info');
        const detailsDiv = document.getElementById('component-details');
        detailsDiv.innerHTML = `
            <div class="info-box">
                <p><strong>Component:</strong> ${component.description}</p>
                <p><strong>Name:</strong> ${component.name}</p>
                <p><strong>Typical Size:</strong> ${component.typical_size}</p>
                <p><strong>Available Versions:</strong> ${component.versions.join(', ')}</p>
                <p style="color: var(--warning-color);"><i class="fas fa-exclamation-triangle"></i> Could not load detailed version information</p>
            </div>
        `;
        infoDiv.style.display = 'block';
    }
}

// Load version lifecycle and compatibility information
async function loadVersionLifecycle(componentName) {
    try {
        const response = await fetch(`${API_BASE}/version-info/${componentName}`);
        const data = await response.json();
        
        if (response.ok && data.versions) {
            displayVersionLifecycle(data);
            displayCompatibilityMatrix(data);
        }
    } catch (error) {
        console.error('Failed to load version lifecycle:', error);
    }
}

// Display version lifecycle information
function displayVersionLifecycle(data) {
    const lifecycleDiv = document.getElementById('version-lifecycle');
    const detailsDiv = document.getElementById('lifecycle-details');
    
    let html = '<div class="info-box">';
    
    // Find LTS versions
    const ltsVersions = [];
    const supportedVersions = [];
    const eolVersions = [];
    
    for (const [version, info] of Object.entries(data.versions)) {
        if (info.is_lts) {
            ltsVersions.push({version, ...info});
        }
        if (info.status === 'supported') {
            supportedVersions.push({version, ...info});
        } else if (info.status === 'end_of_life') {
            eolVersions.push({version, ...info});
        }
    }
    
    // Display LTS versions
    if (ltsVersions.length > 0) {
        html += '<h4 style="color: var(--success-color); margin-top: 0;"><i class="fas fa-star"></i> LTS (Long Term Support) Versions</h4>';
        html += '<ul style="margin-left: 20px;">';
        ltsVersions.forEach(v => {
            html += `<li><strong>${v.version}</strong> - Support until ${v.end_of_support}</li>`;
        });
        html += '</ul>';
    }
    
    // Display supported versions
    html += '<h4 style="color: var(--primary-color);"><i class="fas fa-check-circle"></i> Supported Versions</h4>';
    html += '<table style="width: 100%; border-collapse: collapse; margin-top: 10px;">';
    html += '<tr style="background: var(--bg-secondary); font-weight: bold;"><td style="padding: 8px; border: 1px solid var(--border-color);">Version</td><td style="padding: 8px; border: 1px solid var(--border-color);">Release Date</td><td style="padding: 8px; border: 1px solid var(--border-color);">End of Support</td><td style="padding: 8px; border: 1px solid var(--border-color);">Status</td></tr>';
    
    supportedVersions.forEach(v => {
        const statusColor = v.is_lts ? 'var(--success-color)' : 'var(--primary-color)';
        const statusIcon = v.is_lts ? '<i class="fas fa-star"></i>' : '<i class="fas fa-check"></i>';
        html += `<tr>
            <td style="padding: 8px; border: 1px solid var(--border-color);"><strong>${v.version}</strong></td>
            <td style="padding: 8px; border: 1px solid var(--border-color);">${v.release_date}</td>
            <td style="padding: 8px; border: 1px solid var(--border-color);">${v.end_of_support}</td>
            <td style="padding: 8px; border: 1px solid var(--border-color); color: ${statusColor};">${statusIcon} ${v.is_lts ? 'LTS' : 'Supported'}</td>
        </tr>`;
    });
    html += '</table>';
    
    // Display EOL versions if any
    if (eolVersions.length > 0) {
        html += '<h4 style="color: var(--danger-color); margin-top: 20px;"><i class="fas fa-exclamation-triangle"></i> End of Life Versions</h4>';
        html += '<p style="color: var(--danger-color); font-size: 0.9rem;">These versions are no longer supported and should not be used for new deployments.</p>';
        html += '<ul style="margin-left: 20px;">';
        eolVersions.forEach(v => {
            html += `<li style="color: var(--danger-color);"><strong>${v.version}</strong> - Support ended ${v.end_of_support}</li>`;
        });
        html += '</ul>';
    }
    
    html += '</div>';
    detailsDiv.innerHTML = html;
    lifecycleDiv.style.display = 'block';
}

// Display compatibility matrix
function displayCompatibilityMatrix(data) {
    const matrixDiv = document.getElementById('compatibility-matrix');
    const detailsDiv = document.getElementById('compatibility-details');
    
    let html = '<div class="info-box">';
    html += '<h4><i class="fas fa-server"></i> OpenShift Compatibility</h4>';
    html += '<table style="width: 100%; border-collapse: collapse; margin-top: 10px;">';
    html += '<tr style="background: var(--bg-secondary); font-weight: bold;"><td style="padding: 8px; border: 1px solid var(--border-color);">CP4I Version</td><td style="padding: 8px; border: 1px solid var(--border-color);">Compatible OpenShift Versions</td></tr>';
    
    for (const [version, info] of Object.entries(data.versions)) {
        if (info.status === 'supported') {
            const ocpVersions = info.openshift_compatibility.join(', ');
            html += `<tr>
                <td style="padding: 8px; border: 1px solid var(--border-color);"><strong>${version}</strong>${info.is_lts ? ' <span style="color: var(--success-color);"><i class="fas fa-star"></i> LTS</span>' : ''}</td>
                <td style="padding: 8px; border: 1px solid var(--border-color);">${ocpVersions}</td>
            </tr>`;
        }
    }
    html += '</table>';
    
    // Display dependencies if any
    const firstVersion = Object.values(data.versions)[0];
    if (firstVersion && firstVersion.dependencies && Object.keys(firstVersion.dependencies).length > 0) {
        html += '<h4 style="margin-top: 20px;"><i class="fas fa-sitemap"></i> Dependencies</h4>';
        html += '<ul style="margin-left: 20px;">';
        for (const [dep, version] of Object.entries(firstVersion.dependencies)) {
            html += `<li><strong>${dep}:</strong> ${version}</li>`;
        }
        html += '</ul>';
    }
    
    html += '</div>';
    detailsDiv.innerHTML = html;
    matrixDiv.style.display = 'block';
}

// Update name field based on component and version
function updateNameField() {
    const componentSelect = document.getElementById('component');
    const versionInput = document.getElementById('version');
    const nameInput = document.getElementById('name');
    
    const selectedOption = componentSelect.options[componentSelect.selectedIndex];
    if (selectedOption && selectedOption.dataset.component && versionInput.value) {
        const component = JSON.parse(selectedOption.dataset.component);
        const shortName = component.name.replace('ibm-', '').replace('-operator', '');
        nameInput.value = `${shortName}-${versionInput.value}`;
    }
// Show version-specific details when user enters a version
async function showVersionDetails() {
    const componentSelect = document.getElementById('component');
    const versionInput = document.getElementById('version');
    const selectedOption = componentSelect.options[componentSelect.selectedIndex];
    
    if (!selectedOption.dataset.component || !versionInput.value) {
        return;
    }
    
    const component = JSON.parse(selectedOption.dataset.component);
    const enteredVersion = versionInput.value.trim();
    
    if (!enteredVersion) {
        return;
    }
    
    try {
        // First, try to fetch live CASE details from GitHub
        let liveResponse = await fetch(`${API_BASE}/live/case-details/${component.name}/${enteredVersion}`);
        let liveData = null;
        let dataSource = 'local';
        
        if (liveResponse.ok) {
            liveData = await liveResponse.json();
            if (liveData.success && liveData.details) {
                dataSource = liveData.source || 'live';
                console.log(`Using ${dataSource} CASE data for ${component.name} ${enteredVersion}`);
            }
        }
        
        // Fetch version information from local database
        const response = await fetch(`${API_BASE}/version-info/${component.name}`);
        const data = await response.json();
        
        if (response.ok && data.versions && data.versions[enteredVersion]) {
            const versionInfo = data.versions[enteredVersion];
            
            // Merge live data with local data if available
            let mergedInfo = { ...versionInfo };
            if (liveData && liveData.details) {
                mergedInfo = { ...versionInfo, ...liveData.details };
            }
            
            // Create version details section
            let versionDetailsDiv = document.getElementById('version-specific-details');
            if (!versionDetailsDiv) {
                versionDetailsDiv = document.createElement('div');
                versionDetailsDiv.id = 'version-specific-details';
                versionDetailsDiv.style.marginTop = '20px';
                
                const componentInfoDiv = document.getElementById('component-info');
                if (componentInfoDiv) {
                    componentInfoDiv.appendChild(versionDetailsDiv);
                }
            }
            
            // Data source badge
            let sourceBadge = '';
            if (dataSource === 'live') {
                sourceBadge = '<span style="background: var(--success-color); color: white; padding: 3px 8px; border-radius: 3px; font-size: 0.75rem; margin-left: 10px;"><i class="fas fa-cloud"></i> Live from GitHub</span>';
            } else if (dataSource === 'local_fallback') {
                sourceBadge = '<span style="background: var(--warning-color); color: white; padding: 3px 8px; border-radius: 3px; font-size: 0.75rem; margin-left: 10px;"><i class="fas fa-database"></i> Cached Data</span>';
            } else {
                sourceBadge = '<span style="background: var(--info-color); color: white; padding: 3px 8px; border-radius: 3px; font-size: 0.75rem; margin-left: 10px;"><i class="fas fa-database"></i> Local Data</span>';
            }
            
            // Build version details HTML
            let html = '<div class="info-box" style="border-left: 4px solid var(--primary-color);">';
            html += `<h4 style="margin-top: 0; color: var(--primary-color);"><i class="fas fa-info-circle"></i> CASE Version ${enteredVersion} Details ${sourceBadge}</h4>`;
            
            // Show CASE metadata from GitHub if available
            if (mergedInfo.description && mergedInfo.description !== versionInfo.description) {
                html += '<div style="margin: 15px 0; padding: 10px; background: var(--bg-secondary); border-left: 4px solid var(--info-color); border-radius: 4px;">';
                html += `<p style="margin: 0; font-size: 0.9rem;"><i class="fas fa-info-circle"></i> <strong>Description:</strong> ${mergedInfo.description}</p>`;
                if (mergedInfo.webPage) {
                    html += `<p style="margin: 5px 0 0 0; font-size: 0.9rem;"><i class="fas fa-link"></i> <strong>More Info:</strong> <a href="${mergedInfo.webPage}" target="_blank" style="color: var(--primary-color);">${mergedInfo.webPage}</a></p>`;
                }
                html += '</div>';
            }
            
            // Show supports information from CASE if available
            if (mergedInfo.supports) {
                html += '<div style="margin: 15px 0;">';
                html += '<p style="font-weight: bold; margin-bottom: 8px;"><i class="fas fa-check-circle"></i> Support Matrix (from CASE):</p>';
                html += '<table style="width: 100%; font-size: 0.9rem; border-collapse: collapse;">';
                
                if (mergedInfo.supports.k8sVersion) {
                    html += `<tr><td style="padding: 5px 10px; border: 1px solid var(--border-color); background: var(--bg-secondary); width: 40%;">Kubernetes:</td><td style="padding: 5px 10px; border: 1px solid var(--border-color);">${mergedInfo.supports.k8sVersion}</td></tr>`;
                }
                if (mergedInfo.supports.openshift) {
                    html += `<tr><td style="padding: 5px 10px; border: 1px solid var(--border-color); background: var(--bg-secondary);">OpenShift:</td><td style="padding: 5px 10px; border: 1px solid var(--border-color);">${mergedInfo.supports.openshift}</td></tr>`;
                }
                if (mergedInfo.supports.architectures) {
                    const archs = Array.isArray(mergedInfo.supports.architectures) ? mergedInfo.supports.architectures.join(', ') : mergedInfo.supports.architectures;
                    html += `<tr><td style="padding: 5px 10px; border: 1px solid var(--border-color); background: var(--bg-secondary);">Architectures:</td><td style="padding: 5px 10px; border: 1px solid var(--border-color);">${archs}</td></tr>`;
                }
                
                html += '</table>';
                html += '</div>';
            }
            
            // Instance versions
            if (versionInfo.instance_versions && versionInfo.instance_versions.length > 0) {
                html += '<div style="margin: 15px 0;">';
                html += '<p style="font-weight: bold; margin-bottom: 8px;"><i class="fas fa-cube"></i> Included Instance Versions:</p>';
                html += '<ul style="margin-left: 20px; margin-top: 5px;">';
                versionInfo.instance_versions.forEach(instVersion => {
                    html += `<li><code style="background: var(--bg-secondary); padding: 2px 6px; border-radius: 3px;">${instVersion}</code></li>`;
                });
                html += '</ul>';
                if (versionInfo.description) {
                    html += `<p style="font-size: 0.9rem; color: var(--text-secondary); margin-top: 8px;"><i class="fas fa-comment"></i> ${versionInfo.description}</p>`;
                }
                html += '</div>';
            }
            
            // Lifecycle information
            html += '<div style="margin: 15px 0;">';
            html += '<p style="font-weight: bold; margin-bottom: 8px;"><i class="fas fa-calendar-alt"></i> Lifecycle Information:</p>';
            html += '<table style="width: 100%; font-size: 0.9rem; border-collapse: collapse;">';
            
            const statusColor = versionInfo.status === 'supported' ? 'var(--success-color)' : 'var(--danger-color)';
            const statusIcon = versionInfo.status === 'supported' ? '<i class="fas fa-check-circle"></i>' : '<i class="fas fa-exclamation-triangle"></i>';
            const ltsLabel = versionInfo.is_lts ? ' <span style="background: gold; color: black; padding: 2px 6px; border-radius: 3px; font-size: 0.75rem;"><i class="fas fa-star"></i> LTS</span>' : '';
            
            html += `<tr><td style="padding: 5px 10px; border: 1px solid var(--border-color); background: var(--bg-secondary);">Status:</td><td style="padding: 5px 10px; border: 1px solid var(--border-color); color: ${statusColor};">${statusIcon} ${versionInfo.status}${ltsLabel}</td></tr>`;
            html += `<tr><td style="padding: 5px 10px; border: 1px solid var(--border-color); background: var(--bg-secondary);">Release Date:</td><td style="padding: 5px 10px; border: 1px solid var(--border-color);">${versionInfo.release_date || 'N/A'}</td></tr>`;
            html += `<tr><td style="padding: 5px 10px; border: 1px solid var(--border-color); background: var(--bg-secondary);">End of Support:</td><td style="padding: 5px 10px; border: 1px solid var(--border-color);">${versionInfo.end_of_support || 'N/A'}</td></tr>`;
            html += `<tr><td style="padding: 5px 10px; border: 1px solid var(--border-color); background: var(--bg-secondary);">Download Size:</td><td style="padding: 5px 10px; border: 1px solid var(--border-color);">${versionInfo.size_gb || component.typical_size} GB</td></tr>`;
            html += '</table>';
            html += '</div>';
            
            // OpenShift compatibility
            if (versionInfo.openshift_compatibility && versionInfo.openshift_compatibility.length > 0) {
                html += '<div style="margin: 15px 0;">';
                html += '<p style="font-weight: bold; margin-bottom: 8px;"><i class="fas fa-server"></i> Compatible OpenShift Versions:</p>';
                html += '<div style="display: flex; flex-wrap: wrap; gap: 8px;">';
                versionInfo.openshift_compatibility.forEach(ocpVersion => {
                    html += `<span style="background: var(--success-color); color: white; padding: 4px 10px; border-radius: 4px; font-size: 0.85rem;">${ocpVersion}</span>`;
                });
                html += '</div>';
                html += '</div>';
            }
            
            // Architecture support
            if (versionInfo.architecture && versionInfo.architecture.length > 0) {
                html += '<div style="margin: 15px 0;">';
                html += '<p style="font-weight: bold; margin-bottom: 8px;"><i class="fas fa-microchip"></i> Supported Architectures:</p>';
                html += '<div style="display: flex; flex-wrap: wrap; gap: 8px;">';
                versionInfo.architecture.forEach(arch => {
                    html += `<span style="background: var(--info-color); color: white; padding: 4px 10px; border-radius: 4px; font-size: 0.85rem;">${arch}</span>`;
                });
                html += '</div>';
                html += '</div>';
            }
            
            html += '</div>';
            
            versionDetailsDiv.innerHTML = html;
            versionDetailsDiv.style.display = 'block';
            
            // Scroll to the details
            versionDetailsDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            
        } else {
            // Version not found in data
            let versionDetailsDiv = document.getElementById('version-specific-details');
            if (versionDetailsDiv) {
                versionDetailsDiv.innerHTML = `
                    <div class="info-box" style="border-left: 4px solid var(--warning-color);">
                        <p style="color: var(--warning-color);"><i class="fas fa-exclamation-triangle"></i> <strong>Version ${enteredVersion} not found in database.</strong></p>
                        <p style="font-size: 0.9rem; margin-top: 10px;">This version may not be available or validated. Please select from the available versions list.</p>
                    </div>
                `;
                versionDetailsDiv.style.display = 'block';
            }
        }
    } catch (error) {
        console.error('Failed to load version details:', error);
    }
}

}

// Auto-fill name field when version is entered
document.addEventListener('DOMContentLoaded', () => {
    const versionInput = document.getElementById('version');
    const componentSelect = document.getElementById('component');
    
    if (versionInput) {
        versionInput.addEventListener('input', updateNameField);
        versionInput.addEventListener('blur', showVersionDetails);
    }
    
    if (componentSelect) {
        componentSelect.addEventListener('change', updateNameField);
    }
    
    // Set up download mode change handler
    const downloadModeRadios = document.querySelectorAll('input[name="download_mode"]');
    if (downloadModeRadios.length > 0) {
        downloadModeRadios.forEach(radio => {
            radio.addEventListener('change', updateDownloadMode);
        });
    }
});

// Update download mode visibility
function updateDownloadMode() {
    const downloadMode = document.querySelector('input[name="download_mode"]:checked')?.value;
    const filterGroup = document.getElementById('filter')?.closest('.form-group');
    const homeDirGroup = document.getElementById('home-dir')?.closest('.form-group');
    
    if (downloadMode === 'selective' && filterGroup) {
        filterGroup.style.display = 'block';
        filterGroup.querySelector('label').innerHTML = '<i class="fas fa-filter"></i> Filter Pattern * (Required for Selective)';
    } else if (filterGroup) {
        filterGroup.style.display = 'block';
        filterGroup.querySelector('label').innerHTML = '<i class="fas fa-filter"></i> Filter (Optional)';
    }
    
    // Show/hide home directory based on mode
    if (downloadMode === 'direct_registry') {
        if (homeDirGroup) {
            homeDirGroup.style.display = 'none';
        }
        showToast('Direct to Registry mode: Images will be mirrored directly to the registry without local storage', 'info');
    } else {
        if (homeDirGroup) {
            homeDirGroup.style.display = 'block';
        }
    }
}

// Toggle CP4I advanced options
function toggleCP4IAdvancedOptions() {
    const advancedOptions = document.getElementById('cp4i-advanced-options');
    const toggleText = document.getElementById('cp4i-advanced-toggle-text');
    
    if (advancedOptions && toggleText) {
        if (advancedOptions.style.display === 'none') {
            advancedOptions.style.display = 'block';
            toggleText.textContent = 'Hide Advanced Options';
        } else {
            advancedOptions.style.display = 'none';
            toggleText.textContent = 'Show Advanced Options';
        }
    }
}

// Load CP4I preset configurations
function loadCP4IPreset(presetType) {
    const form = document.getElementById('download-form');
    if (!form) return;
    
    // Get elements
    const parallelDownloads = document.getElementById('parallel-downloads');
    const retryAttempts = document.getElementById('retry-attempts');
    const skipExisting = document.getElementById('skip-existing');
    const verifyImages = document.getElementById('verify-images');
    const includeDependencies = document.getElementById('include-dependencies');
    const generateCatalog = document.getElementById('generate-catalog');
    const createBackup = document.getElementById('create-backup');
    
    switch(presetType) {
        case 'production':
            if (parallelDownloads) parallelDownloads.value = '3';
            if (retryAttempts) retryAttempts.value = '5';
            if (skipExisting) skipExisting.value = 'true';
            if (verifyImages) verifyImages.value = 'true';
            if (includeDependencies) includeDependencies.checked = true;
            if (generateCatalog) generateCatalog.checked = true;
            if (createBackup) createBackup.checked = true;
            showToast('Loaded production-ready preset (safe & verified)', 'info');
            break;
        case 'development':
            if (parallelDownloads) parallelDownloads.value = '7';
            if (retryAttempts) retryAttempts.value = '2';
            if (skipExisting) skipExisting.value = 'true';
            if (verifyImages) verifyImages.value = 'false';
            if (includeDependencies) includeDependencies.checked = true;
            if (generateCatalog) generateCatalog.checked = false;
            if (createBackup) createBackup.checked = false;
            showToast('Loaded development preset (fast downloads)', 'info');
            break;
        case 'minimal':
            if (parallelDownloads) parallelDownloads.value = '5';
            if (retryAttempts) retryAttempts.value = '3';
            if (skipExisting) skipExisting.value = 'true';
            if (verifyImages) verifyImages.value = 'true';
            if (includeDependencies) includeDependencies.checked = false;
            if (generateCatalog) generateCatalog.checked = false;
            if (createBackup) createBackup.checked = false;
            showToast('Loaded minimal preset (core only)', 'info');
            break;
        case 'complete':
            if (parallelDownloads) parallelDownloads.value = '5';
            if (retryAttempts) retryAttempts.value = '3';
            if (skipExisting) skipExisting.value = 'false';
            if (verifyImages) verifyImages.value = 'true';
            if (includeDependencies) includeDependencies.checked = true;
            if (generateCatalog) generateCatalog.checked = true;
            if (createBackup) createBackup.checked = true;
            showToast('Loaded complete preset (full download)', 'info');
            break;
    }
}

// Estimate CP4I component size
async function estimateCP4ISize() {
    const componentSelect = document.getElementById('component');
    const selectedOption = componentSelect.options[componentSelect.selectedIndex];
    
    if (!selectedOption || !selectedOption.dataset.component) {
        showToast('Please select a component first', 'warning');
        return;
    }
    
    const component = JSON.parse(selectedOption.dataset.component);
    const includeDependencies = document.getElementById('include-dependencies')?.checked || false;
    
    // Parse typical size
    let baseSize = 10; // Default GB
    const sizeMatch = component.typical_size.match(/(\d+)/);
    if (sizeMatch) {
        baseSize = parseInt(sizeMatch[1]);
    }
    
    let estimatedSize = baseSize;
    if (includeDependencies) {
        estimatedSize = Math.round(baseSize * 1.3); // 30% more for dependencies
    }
    
    const modal = document.getElementById('download-details-modal');
    const content = document.getElementById('download-details-content');
    
    modal.classList.add('active');
    content.innerHTML = `
        <h3><i class="fas fa-calculator"></i> Estimated Download Size</h3>
        <div class="info-box">
            <p><strong>Component:</strong> ${component.description}</p>
            <p><strong>Base Size:</strong> ${component.typical_size}</p>
            <p><strong>Include Dependencies:</strong> ${includeDependencies ? 'Yes (+30%)' : 'No'}</p>
            <hr style="margin: 15px 0;">
            <p style="font-size: 1.2rem;"><strong>Estimated Total:</strong> <span style="color: var(--primary-color);">~${estimatedSize} GB</span></p>
            <p style="margin-top: 10px; font-size: 0.9rem; color: var(--text-secondary);">
                <i class="fas fa-info-circle"></i> Actual size may vary based on version and filters.
            </p>
        </div>
    `;
}

// Verify CP4I Images (Dry Run)
async function verifyCP4IImages() {
    const form = document.getElementById('download-form');
    const formData = new FormData(form);
    
    const component = formData.get('component');
    const version = formData.get('version');
    const name = formData.get('name');
    
    if (!component || !version) {
        showToast('Please select component and version first', 'warning');
        return;
    }
    
    if (!name) {
        showToast('Please enter a name for this verification', 'warning');
        return;
    }
    
    showToast('Verifying images (dry run)...', 'info');
    
    try {
        // Create request data - must match backend requirements
        const requestData = {
            component: component,
            version: version,
            name: name + '-verify',
            filter: formData.get('filter') || '',
            home_dir: formData.get('home_dir') || '/opt/cp4i',
            final_registry: formData.get('final_registry') || 'registry.example.com:5000',
            registry_auth_file: formData.get('registry_auth_file') || '/root/.docker/config.json',
            entitlement_key: formData.get('entitlement_key') || '',
            include_dependencies: formData.get('include_dependencies') === 'on',
            verify_images: true,
            skip_existing: true,
            dry_run: true  // Force dry run
        };
        
        const response = await fetch(`${API_BASE}/downloads`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestData)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast('Dry run started successfully', 'success');
            
            // Show modal with download ID and status
            const modal = document.getElementById('download-details-modal');
            const content = document.getElementById('download-details-content');
            
            modal.classList.add('active');
            content.innerHTML = `
                <h3><i class="fas fa-search"></i> Image Verification (Dry Run)</h3>
                <div class="info-box">
                    <p><strong>Component:</strong> ${component}</p>
                    <p><strong>Version:</strong> ${version}</p>
                    <p><strong>Download ID:</strong> ${data.download_id}</p>
                    <p><strong>Status:</strong> <span style="color: var(--info-color);"><i class="fas fa-spinner fa-spin"></i> Running dry run verification...</span></p>
                </div>
                <div class="info-box" style="margin-top: 20px; background: var(--warning-bg, #fff3cd); border-left: 4px solid var(--warning-color, #ffc107);">
                    <p style="margin: 0;"><i class="fas fa-info-circle"></i> <strong>Note:</strong> This is a dry run. No images will be downloaded.</p>
                    <p style="margin: 10px 0 0 0;">Check the "Active Downloads" tab to monitor progress and view logs.</p>
                </div>
            `;
            
            // Switch to active downloads tab after a short delay
            setTimeout(() => {
                showTab('active-downloads');
                closeModal('download-details-modal');
            }, 3000);
        } else {
            showToast(data.error || 'Verification failed', 'error');
        }
    } catch (error) {
        console.error('Verification error:', error);
        showToast('Failed to verify images', 'error');
    }
}

// Reset CP4I Form
function resetCP4IForm() {
    if (confirm('Are you sure you want to reset the form? All entered data will be cleared.')) {
        const form = document.getElementById('download-form');
        if (form) {
            form.reset();
            
            // Clear component info cards
            document.getElementById('component-info').style.display = 'none';
            document.getElementById('version-lifecycle').style.display = 'none';
            document.getElementById('compatibility-matrix').style.display = 'none';
            
            // Reset version select
            const versionSelect = document.getElementById('version');
            if (versionSelect) {
                versionSelect.innerHTML = '<option value="">Select component first</option>';
            }
            
            showToast('Form reset successfully', 'success');
        }
    }
}

// Preview manifests before download
async function previewManifests() {
    const component = document.getElementById('component').value;
    const version = document.getElementById('version').value;
    const filter = document.getElementById('filter').value;
    
    if (!component || !version) {
        showToast('Please select component and version first', 'warning');
        return;
    }
    
    showToast('Fetching manifest preview...', 'info');
    
    try {
        const response = await fetch(`${API_BASE}/preview-manifests`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ component, version, filter })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            const modal = document.getElementById('download-details-modal');
            const content = document.getElementById('download-details-content');
            
            modal.classList.add('active');
            content.innerHTML = `
                <h3><i class="fas fa-list"></i> Manifest Preview: ${component} v${version}</h3>
                <div class="info-box">
                    <p><strong>Total Manifests:</strong> ${data.count || 'N/A'}</p>
                    ${filter ? `<p><strong>Filter Applied:</strong> ${filter}</p>` : ''}
                </div>
                ${data.manifests ? `
                    <h4 class="mt-20">Manifests to Download:</h4>
                    <div class="code-block" style="max-height: 400px; overflow-y: auto;">
                        ${data.manifests.join('\n')}
                    </div>
                ` : ''}
            `;
        } else {
            showToast(data.error || 'Failed to fetch manifest preview', 'error');
        }
    } catch (error) {
        showToast('Failed to fetch manifest preview', 'error');
        console.error(error);
    }
}

// Start Download
async function startDownload(event) {
    event.preventDefault();
    
    const form = event.target;
    const downloadMode = document.querySelector('input[name="download_mode"]:checked')?.value || 'standard';
    
    const formData = {
        component: form.component.value,
        version: form.version.value,
        name: form.name.value,
        filter: form.filter.value || null,
        dry_run: form.dry_run.checked,
        home_dir: form.home_dir.value,
        final_registry: form.final_registry.value,
        registry_auth_file: form.registry_auth_file.value,
        entitlement_key: form.entitlement_key.value,
        download_mode: downloadMode,
        // Set direct_to_registry flag when download mode is direct_registry
        direct_to_registry: downloadMode === 'direct_registry',
        // Advanced options
        parallel_downloads: form.parallel_downloads?.value || 5,
        retry_attempts: form.retry_attempts?.value || 3,
        skip_existing: form.skip_existing?.value === 'true',
        verify_images: form.verify_images?.value === 'true',
        include_dependencies: form.include_dependencies?.checked || false,
        generate_catalog: form.generate_catalog?.checked || false,
        create_backup: form.create_backup?.checked || false
    };
    
    // Validate required fields (entitlement_key is optional)
    if (!formData.home_dir || !formData.final_registry || !formData.registry_auth_file) {
        showToast('Please fill in required configuration fields (home_dir, final_registry, registry_auth_file)', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/downloads`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast(`Download started: ${formData.name}`, 'success');
            
            // Don't reset the form to preserve configuration values
            // Only clear download-specific fields
            try {
                form.component.value = '';
                form.version.value = '';
                form.name.value = '';
                form.filter.value = '';
                form.dry_run.checked = false;
                document.getElementById('component-info').style.display = 'none';
                showTab('active-downloads');
                loadDownloads();
            } catch (uiError) {
                // Log UI update errors but don't show error toast since download started successfully
                console.error('UI update error after successful download start:', uiError);
            }
        } else {
            showToast(data.error || 'Failed to start download', 'error');
        }
    } catch (error) {
        showToast('Failed to start download', 'error');
        console.error(error);
    }
}

// Load Downloads
async function loadDownloads() {
    try {
        const response = await fetch(`${API_BASE}/downloads`);
        const data = await response.json();
        
        activeDownloads = data.active || [];
        downloadHistory = data.history || [];
        
        renderActiveDownloads();
        renderHistory();
        updateActiveCount();
    } catch (error) {
        console.error('Failed to load downloads:', error);
    }
}

// Render Active Downloads
function renderActiveDownloads() {
    const container = document.getElementById('active-downloads-list');
    
    if (activeDownloads.length === 0) {
        container.innerHTML = '<p class="empty-state">No active downloads</p>';
        return;
    }
    
    container.innerHTML = activeDownloads.map(download => `
        <div class="download-item status-${download.status}">
            <div class="download-header">
                <div class="download-title">
                    <i class="fas fa-cube"></i> ${download.component} v${download.version}
                </div>
                <span class="download-status status-${download.status}">
                    ${download.status}
                </span>
            </div>
            
            <div class="download-info">
                <div><i class="fas fa-folder"></i> <strong>Name:</strong> ${download.name}</div>
                <div><i class="fas fa-clock"></i> <strong>Started:</strong> ${formatDateTime(download.start_time)}</div>
                <div><i class="fas fa-hashtag"></i> <strong>PID:</strong> ${download.pid || 'N/A'}</div>
            </div>
            
            ${download.status === 'running' ? `
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${download.progress || 50}%"></div>
                </div>
                <p style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 5px;">
                    Progress: ${download.progress || 50}%
                </p>
            ` : ''}
            
            <div class="download-actions">
                <button class="btn btn-small btn-secondary" onclick="showDownloadDetails('${download.id}')">
                    <i class="fas fa-info-circle"></i> Details
                </button>
                ${download.status === 'running' ? `
                    <button class="btn btn-small btn-danger" onclick="stopDownload('${download.id}')">
                        <i class="fas fa-stop"></i> Stop
                    </button>
                ` : ''}
                ${download.status === 'failed' ? `
                    <button class="btn btn-small btn-primary" onclick="retryDownload('${download.id}')">
                        <i class="fas fa-redo"></i> Retry
                    </button>
                ` : ''}
                ${download.status !== 'running' ? `
                    <button class="btn btn-small btn-secondary" onclick="dismissDownload('${download.id}')">
                        <i class="fas fa-times"></i> Dismiss
                    </button>
                ` : ''}
            </div>
        </div>
    `).join('');
}

// Render History
function renderHistory() {
    const container = document.getElementById('history-list');
    
    if (downloadHistory.length === 0) {
        container.innerHTML = '<p class="empty-state">No download history</p>';
        return;
    }
    
    container.innerHTML = downloadHistory.map(download => `
        <div class="download-item status-${download.status}">
            <div class="download-header">
                <div class="download-title">
                    <i class="fas fa-cube"></i> ${download.component} v${download.version}
                </div>
                <span class="download-status status-${download.status}">
                    ${download.status}
                </span>
            </div>
            
            <div class="download-info">
                <div><i class="fas fa-folder"></i> <strong>Name:</strong> ${download.name}</div>
                <div><i class="fas fa-clock"></i> <strong>Started:</strong> ${formatDateTime(download.start_time)}</div>
                <div><i class="fas fa-check-circle"></i> <strong>Ended:</strong> ${formatDateTime(download.end_time)}</div>
            </div>
            
            <div class="download-actions">
                <button class="btn btn-small btn-secondary" onclick="viewLogs('${download.id}')">
                    <i class="fas fa-file-alt"></i> View Logs
                </button>
                <button class="btn btn-small btn-secondary" onclick="viewReport('${download.id}')">
                    <i class="fas fa-chart-bar"></i> View Report
                </button>
                ${download.status === 'completed' ? `
                    <button class="btn btn-small btn-primary" onclick="retryDownload('${download.id}')">
                        <i class="fas fa-download"></i> Re-download
                    </button>
                ` : ''}
                ${download.status === 'failed' || download.status === 'dismissed' ? `
                    <button class="btn btn-small btn-primary" onclick="retryDownload('${download.id}')">
                        <i class="fas fa-redo"></i> Retry
                    </button>
                ` : ''}
            </div>
        </div>
    `).join('');
}

// Update Active Count Badge
function updateActiveCount() {
    const badge = document.getElementById('active-count');
    const count = activeDownloads.filter(d => d.status === 'running').length;
    badge.textContent = count;
    badge.style.display = count > 0 ? 'inline-block' : 'none';
}

// Show Download Details
async function showDownloadDetails(downloadId) {
    const modal = document.getElementById('download-details-modal');
    const content = document.getElementById('download-details-content');
    
    modal.classList.add('active');
    content.innerHTML = '<div class="loading">Loading...</div>';
    
    try {
        const response = await fetch(`${API_BASE}/downloads/${downloadId}`);
        const data = await response.json();
        
        if (response.ok) {
            content.innerHTML = `
                <div class="info-box">
                    <h3><i class="fas fa-cube"></i> ${data.component} v${data.version}</h3>
                    <p><strong>Status:</strong> <span class="download-status status-${data.status}">${data.status}</span></p>
                    <p><strong>Name:</strong> ${data.name}</p>
                    <p><strong>Started:</strong> ${formatDateTime(data.start_time)}</p>
                    ${data.end_time ? `<p><strong>Ended:</strong> ${formatDateTime(data.end_time)}</p>` : ''}
                    <p><strong>PID:</strong> ${data.pid || 'N/A'}</p>
                </div>
                
                ${data.log_tail && data.log_tail.length > 0 ? `
                    <h3 class="mt-20"><i class="fas fa-terminal"></i> Recent Log Output</h3>
                    <div class="code-block">${data.log_tail.join('')}</div>
                ` : ''}
                
                ${data.progress && data.progress.summary ? `
                    <h3 class="mt-20"><i class="fas fa-chart-line"></i> Progress Summary</h3>
                    <div class="code-block">${data.progress.summary}</div>
                ` : ''}
            `;
        } else {
            content.innerHTML = `<div class="error-box">${data.error}</div>`;
        }
    } catch (error) {
        content.innerHTML = '<div class="error-box">Failed to load download details</div>';
        console.error(error);
    }
}

// Stop Download
async function stopDownload(downloadId) {
    if (!confirm('Are you sure you want to stop this download?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/downloads/${downloadId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast('Download stopped', 'success');
            loadDownloads();
        } else {
            showToast(data.error || 'Failed to stop download', 'error');
        }
    } catch (error) {
        showToast('Failed to stop download', 'error');
        console.error(error);
    }
}

// Retry Download - Use original configuration directly
async function retryDownload(downloadId) {
    try {
        // First try to find in local downloadHistory (faster)
        let download = null;
        for (const hist of downloadHistory) {
            if (hist.id === downloadId) {
                download = hist;
                break;
            }
        }
        
        // If not found locally, fetch from API
        if (!download) {
            const response = await fetch(`${API_BASE}/downloads`);
            const data = await response.json();
            
            for (const hist of data.history) {
                if (hist.id === downloadId) {
                    download = hist;
                    break;
                }
            }
        }
        
        if (!download) {
            showToast('Download not found', 'error');
            console.error('Download not found:', downloadId);
            return;
        }
        
        console.log('Retrying download with original configuration:', download);
        
        // Use original configuration from history
        const retryData = {
            home_dir: download.home_dir || '/opt/cp4i',
            final_registry: download.final_registry || 'registry.example.com:5000',
            registry_auth_file: download.registry_auth_file || '/root/.docker/config.json',
            entitlement_key: download.entitlement_key || ''
        };
        
        // Start retry directly with original configuration
        const response = await fetch(`${API_BASE}/downloads/${downloadId}/retry`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(retryData)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast('Download retry started with original configuration', 'success');
            loadDownloads();
        } else {
            showToast(data.error || 'Failed to retry download', 'error');
        }
    } catch (error) {
        showToast('Failed to retry download', 'error');
        console.error(error);
    }
}

// Dismiss Download
async function dismissDownload(downloadId) {
    if (!confirm('Are you sure you want to dismiss this download from the list?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/downloads/${downloadId}`, {
            method: 'PATCH'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast('Download dismissed', 'success');
            loadDownloads();
        } else {
            showToast(data.error || 'Failed to dismiss download', 'error');
        }
    } catch (error) {
        showToast('Failed to dismiss download', 'error');
        console.error(error);
    }
}

// View Logs
async function viewLogs(downloadId) {
    const modal = document.getElementById('download-details-modal');
    const content = document.getElementById('download-details-content');
    
    modal.classList.add('active');
    content.innerHTML = '<div class="loading">Loading logs...</div>';
    
    try {
        // Find the download in history to get home_dir and name
        let download = null;
        for (const hist of downloadHistory) {
            if (hist.id === downloadId) {
                download = hist;
                break;
            }
        }
        
        if (!download) {
            content.innerHTML = '<div class="error-box">Download not found</div>';
            return;
        }
        
        const homeDir = download.home_dir || '/opt/cp4i';
        const name = download.name;
        
        const response = await fetch(`${API_BASE}/logs/${name}?home_dir=${encodeURIComponent(homeDir)}`);
        const data = await response.json();
        
        if (response.ok) {
            // Create tabs for download and mirror logs
            let tabsHtml = `
                <h3><i class="fas fa-file-alt"></i> Logs: ${name}</h3>
                <div class="log-tabs" style="margin: 15px 0;">
                    <button class="log-tab active" onclick="switchLogTab('download', '${name}', '${homeDir}')">
                        <i class="fas fa-download"></i> Download Log
                    </button>
                    <button class="log-tab" onclick="switchLogTab('mirror', '${name}', '${homeDir}')">
                        <i class="fas fa-images"></i> Mirror Log
                    </button>
                </div>
                <div id="log-content-area">
            `;
            
            // Show download log by default
            if (data.download_log_exists) {
                tabsHtml += `<div class="code-block">${escapeHtml(data.download_log)}</div>`;
            } else {
                tabsHtml += `<div class="info-box">Download log not found</div>`;
            }
            
            tabsHtml += `</div>`;
            
            // Store both logs in data attributes for tab switching
            content.innerHTML = tabsHtml;
            content.dataset.downloadLog = data.download_log || 'Download log not found';
            content.dataset.mirrorLog = data.mirror_log || 'Mirror log not found';
            content.dataset.downloadLogExists = data.download_log_exists;
            content.dataset.mirrorLogExists = data.mirror_log_exists;
        } else {
            content.innerHTML = `<div class="error-box">${data.error}</div>`;
        }
    } catch (error) {
        content.innerHTML = '<div class="error-box">Failed to load logs</div>';
        console.error(error);
    }
}

// Switch between log tabs
function switchLogTab(logType, name, homeDir) {
    const content = document.getElementById('download-details-content');
    const logContentArea = document.getElementById('log-content-area');
    const tabs = document.querySelectorAll('.log-tab');
    
    // Update active tab
    tabs.forEach(tab => tab.classList.remove('active'));
    event.target.closest('.log-tab').classList.add('active');
    
    // Show appropriate log
    if (logType === 'download') {
        const downloadLog = content.dataset.downloadLog;
        const exists = content.dataset.downloadLogExists === 'true';
        if (exists) {
            logContentArea.innerHTML = `<div class="code-block">${escapeHtml(downloadLog)}</div>`;
        } else {
            logContentArea.innerHTML = `<div class="info-box">Download log not found</div>`;
        }
    } else if (logType === 'mirror') {
        const mirrorLog = content.dataset.mirrorLog;
        const exists = content.dataset.mirrorLogExists === 'true';
        if (exists) {
            logContentArea.innerHTML = `<div class="code-block">${escapeHtml(mirrorLog)}</div>`;
        } else {
            logContentArea.innerHTML = `<div class="info-box">Mirror log not found</div>`;
        }
    }
}

// View Report
async function viewReport(downloadId) {
    const modal = document.getElementById('download-details-modal');
    const content = document.getElementById('download-details-content');
    
    modal.classList.add('active');
    content.innerHTML = '<div class="loading">Loading report...</div>';
    
    try {
        // Find the download in history to get home_dir and name
        let download = null;
        for (const hist of downloadHistory) {
            if (hist.id === downloadId) {
                download = hist;
                break;
            }
        }
        
        if (!download) {
            content.innerHTML = '<div class="error-box">Download not found</div>';
            return;
        }
        
        const homeDir = download.home_dir || '/opt/cp4i';
        const name = download.name;
        
        const response = await fetch(`${API_BASE}/reports/${name}?home_dir=${encodeURIComponent(homeDir)}`);
        const data = await response.json();
        
        if (response.ok) {
            content.innerHTML = `
                <h3><i class="fas fa-chart-bar"></i> Summary Report: ${name}</h3>
                <div class="code-block">${data.report}</div>
            `;
        } else {
            content.innerHTML = `<div class="error-box">${data.error}</div>`;
        }
    } catch (error) {
        content.innerHTML = '<div class="error-box">Failed to load report</div>';
        console.error(error);
    }
}

// Show System Info
async function showSystemInfo() {
    const modal = document.getElementById('system-info-modal');
    const content = document.getElementById('system-info-content');

    modal.classList.add('active');
    content.innerHTML = '<div class="loading">Loading system information...</div>';

    try {
        // Get home_dir from form if available
        const homeDirInput = document.getElementById('home-dir');
        const homeDir = homeDirInput ? homeDirInput.value : '/opt/cp4i';
        
        const response = await fetch(`${API_BASE}/system/info?home_dir=${encodeURIComponent(homeDir)}`);
        const data = await response.json();
        
        if (response.ok) {
            const prereqsHtml = Object.entries(data.prerequisites)
                .map(([tool, installed]) => `
                    <div style="display: flex; align-items: center; gap: 10px; margin: 5px 0;">
                        <i class="fas fa-${installed ? 'check-circle' : 'times-circle'}" 
                           style="color: ${installed ? 'var(--success-color)' : 'var(--danger-color)'}"></i>
                        <strong>${tool}:</strong> ${installed ? 'Installed' : 'Not Found'}
                    </div>
                `).join('');
            
            content.innerHTML = `
                <div class="info-box">
                    <h3><i class="fas fa-server"></i> System Configuration</h3>
                    <p><strong>Home Directory:</strong> ${data.home_dir}</p>
                    <p><strong>Script Path:</strong> ${data.script_path}</p>
                </div>
                
                <h3 class="mt-20"><i class="fas fa-hdd"></i> Disk Space</h3>
                <div class="code-block">${data.disk_info}</div>
                
                <h3 class="mt-20"><i class="fas fa-check-circle"></i> Prerequisites</h3>
                <div class="info-box">
                    ${prereqsHtml}
                </div>
            `;
        } else {
            content.innerHTML = `<div class="error-box">${data.error}</div>`;
        }
    } catch (error) {
        content.innerHTML = '<div class="error-box">Failed to load system information</div>';
        console.error(error);
    }
}

// Show Configuration
async function showConfig() {
    const modal = document.getElementById('config-modal');
    modal.classList.add('active');
    loadConfig();
}

// Load Configuration
async function loadConfig() {
    try {
        const response = await fetch(`${API_BASE}/config`);
        const data = await response.json();
        
        document.getElementById('config-content').value = data.config || '';
    } catch (error) {
        showToast('Failed to load configuration', 'error');
        console.error(error);
    }
}

// Save Configuration
async function saveConfig(event) {
    event.preventDefault();
    
    const content = document.getElementById('config-content').value;
    
    try {
        const response = await fetch(`${API_BASE}/config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ config: content })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast('Configuration saved successfully', 'success');
            closeModal('config-modal');
        } else {
            showToast(data.error || 'Failed to save configuration', 'error');
        }
    } catch (error) {
        showToast('Failed to save configuration', 'error');
        console.error(error);
    }
}

// Validate Prerequisites
async function validatePrerequisites() {
    try {
        const response = await fetch(`${API_BASE}/validate`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.valid) {
            showToast('All prerequisites validated successfully', 'success');
        } else {
            showToast('Some prerequisites are missing. Check system info.', 'warning');
        }
    } catch (error) {
        showToast('Failed to validate prerequisites', 'error');
        console.error(error);
    }
}

// Close Modal
function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

// Close modal on background click
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal')) {
        e.target.classList.remove('active');
    }
});

// Show Toast Notification
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icon = {
        success: 'check-circle',
        error: 'exclamation-circle',
        warning: 'exclamation-triangle',
        info: 'info-circle'
    }[type] || 'info-circle';
    
    toast.innerHTML = `
        <i class="fas fa-${icon}"></i>
        <span>${message}</span>
    `;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
// Show OpenShift version details when version is selected
async function showOpenShiftVersionDetails() {
    const detailsDiv = document.getElementById('openshift-version-details');
    const contentDiv = document.getElementById('openshift-version-content');
    
    if (!detailsDiv || !contentDiv) {
        return;
    }
    
    // Get version from either select or custom input
    const versionSelect = document.getElementById('ocp-release-select');
    const customInput = document.getElementById('ocp-release-custom');
    const selectedVersion = customInput.style.display !== 'none' ? customInput.value : versionSelect.value;
    
    if (!selectedVersion) {
        detailsDiv.style.display = 'none';
        return;
    }
    
    // Show loading indicator
    contentDiv.innerHTML = `
        <div style="text-align: center; padding: 20px;">
            <i class="fas fa-spinner fa-spin" style="font-size: 1.5rem; color: var(--primary-color);"></i>
            <p style="margin-top: 10px; color: var(--text-secondary);">Loading version details...</p>
        </div>
    `;
    detailsDiv.style.display = 'block';
    
    try {
        // Fetch OpenShift version information from cp4i_version_data.json
        const response = await fetch(`${API_BASE}/version-info/openshift_versions`);
        const data = await response.json();
        
        if (response.ok && data.versions && data.versions[selectedVersion]) {
            const versionInfo = data.versions[selectedVersion];
            
            // Build version details HTML
            let html = `<h4 style="margin-top: 0; color: var(--primary-color);"><i class="fas fa-info-circle"></i> OpenShift ${selectedVersion} Details</h4>`;
            
            // Version status and lifecycle
            html += '<div style="margin: 15px 0;">';
            html += '<p style="font-weight: bold; margin-bottom: 8px;"><i class="fas fa-calendar-alt"></i> Lifecycle Information:</p>';
            html += '<table style="width: 100%; font-size: 0.9rem; border-collapse: collapse;">';
            
            const statusColor = versionInfo.status === 'supported' ? 'var(--success-color)' : 'var(--danger-color)';
            const statusIcon = versionInfo.status === 'supported' ? '<i class="fas fa-check-circle"></i>' : '<i class="fas fa-exclamation-triangle"></i>';
            const eusLabel = versionInfo.is_eus ? ' <span style="background: var(--info-color); color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.75rem;"><i class="fas fa-shield-alt"></i> EUS</span>' : '';
            
            html += `<tr><td style="padding: 5px 10px; border: 1px solid var(--border-color); background: var(--bg-secondary); width: 40%;">Status:</td><td style="padding: 5px 10px; border: 1px solid var(--border-color); color: ${statusColor};">${statusIcon} ${versionInfo.status}${eusLabel}</td></tr>`;
            html += `<tr><td style="padding: 5px 10px; border: 1px solid var(--border-color); background: var(--bg-secondary);">Release Date:</td><td style="padding: 5px 10px; border: 1px solid var(--border-color);">${versionInfo.release_date || 'N/A'}</td></tr>`;
            html += `<tr><td style="padding: 5px 10px; border: 1px solid var(--border-color); background: var(--bg-secondary);">End of Support:</td><td style="padding: 5px 10px; border: 1px solid var(--border-color);">${versionInfo.end_of_support || 'N/A'}</td></tr>`;
            
            if (versionInfo.kubernetes_version) {
                html += `<tr><td style="padding: 5px 10px; border: 1px solid var(--border-color); background: var(--bg-secondary);">Kubernetes Version:</td><td style="padding: 5px 10px; border: 1px solid var(--border-color);">${versionInfo.kubernetes_version}</td></tr>`;
            }
            
            html += '</table>';
            html += '</div>';
            
            // CP4I Compatibility
            if (versionInfo.cp4i_compatibility && versionInfo.cp4i_compatibility.length > 0) {
                html += '<div style="margin: 15px 0;">';
                html += '<p style="font-weight: bold; margin-bottom: 8px;"><i class="fas fa-puzzle-piece"></i> Compatible CP4I Versions:</p>';
                html += '<div style="display: flex; flex-wrap: wrap; gap: 8px;">';
                versionInfo.cp4i_compatibility.forEach(cp4iVersion => {
                    html += `<span style="background: var(--success-color); color: white; padding: 4px 10px; border-radius: 4px; font-size: 0.85rem;">${cp4iVersion}</span>`;
                });
                html += '</div>';
                html += '</div>';
            }
            
            // Architecture support
            if (versionInfo.architectures && versionInfo.architectures.length > 0) {
                html += '<div style="margin: 15px 0;">';
                html += '<p style="font-weight: bold; margin-bottom: 8px;"><i class="fas fa-microchip"></i> Supported Architectures:</p>';
                html += '<div style="display: flex; flex-wrap: wrap; gap: 8px;">';
                versionInfo.architectures.forEach(arch => {
                    html += `<span style="background: var(--info-color); color: white; padding: 4px 10px; border-radius: 4px; font-size: 0.85rem;">${arch}</span>`;
                });
                html += '</div>';
                html += '</div>';
            }
            
            // Key features or notes
            if (versionInfo.notes) {
                html += '<div style="margin: 15px 0; padding: 10px; background: var(--bg-secondary); border-left: 4px solid var(--info-color); border-radius: 4px;">';
                html += `<p style="margin: 0; font-size: 0.9rem;"><i class="fas fa-info-circle"></i> <strong>Notes:</strong> ${versionInfo.notes}</p>`;
                html += '</div>';
            }
            
            // EUS explanation
            if (versionInfo.is_eus) {
                html += '<div style="margin: 15px 0; padding: 10px; background: var(--bg-secondary); border-left: 4px solid var(--info-color); border-radius: 4px;">';
                html += '<p style="margin: 0; font-size: 0.9rem;"><i class="fas fa-shield-alt"></i> <strong>Extended Update Support (EUS):</strong> This version receives extended support with longer maintenance windows and additional stability updates.</p>';
                html += '</div>';
            }
            
            contentDiv.innerHTML = html;
            
            // Smooth scroll to details
            detailsDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            
        } else {
            // Version not found - show basic info
            contentDiv.innerHTML = `
                <h4 style="margin-top: 0; color: var(--primary-color);"><i class="fas fa-info-circle"></i> OpenShift ${selectedVersion}</h4>
                <p style="color: var(--text-secondary);">Detailed information for this version is being fetched from Red Hat...</p>
                <div style="margin: 15px 0;">
                    <p style="font-weight: bold;"><i class="fas fa-download"></i> Selected for Download:</p>
                    <p style="font-size: 0.9rem;">OpenShift Container Platform ${selectedVersion}</p>
                </div>
                <div style="margin: 15px 0; padding: 10px; background: var(--bg-secondary); border-left: 4px solid var(--warning-color); border-radius: 4px;">
                    <p style="margin: 0; font-size: 0.9rem;"><i class="fas fa-exclamation-triangle"></i> <strong>Note:</strong> Version details will be validated during the mirror process.</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('Failed to load OpenShift version details:', error);
        contentDiv.innerHTML = `
            <h4 style="margin-top: 0; color: var(--primary-color);"><i class="fas fa-info-circle"></i> OpenShift ${selectedVersion}</h4>
            <p style="color: var(--text-secondary);">Selected for download and mirroring.</p>
            <div style="margin: 15px 0; padding: 10px; background: var(--bg-secondary); border-left: 4px solid var(--info-color); border-radius: 4px;">
                <p style="margin: 0; font-size: 0.9rem;"><i class="fas fa-info-circle"></i> Version details will be validated during the mirror process.</p>
            </div>
        `;
    }
}

    }, 5000);
}

// Format DateTime
function formatDateTime(isoString) {
    if (!isoString) return 'N/A';
    const date = new Date(isoString);
    return date.toLocaleString();
}

// Auto-refresh
function startAutoRefresh() {
    refreshInterval = setInterval(() => {
        if (document.querySelector('#active-downloads.active') || 
            document.querySelector('#history.active')) {
            loadDownloads();
        }
    }, 10000); // Refresh every 10 seconds
}

// Stop auto-refresh on page unload
window.addEventListener('beforeunload', () => {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
});

// OpenShift Mirror Functions
// Handle OCP version selection change
function handleOCPVersionChange() {
    const select = document.getElementById('ocp-release-select');
    const customInput = document.getElementById('ocp-release-custom');
    
    if (select.value === 'custom') {
        // Show custom input field and disable select
        customInput.style.display = 'block';
        customInput.required = true;
        select.required = false;
        select.removeAttribute('name'); // Remove name so it's not submitted
        customInput.setAttribute('name', 'ocp_release'); // Add name to custom input
        customInput.focus();
    } else {
        // Hide custom input and use selected value
        customInput.style.display = 'none';
        customInput.required = false;
        select.required = true;
        customInput.removeAttribute('name'); // Remove name from custom input
        select.setAttribute('name', 'ocp_release'); // Add name to select
        
        // Trigger version details if a version is selected
        if (select.value) {
            showOpenShiftVersionDetails();
        }
    }
}

// Load OpenShift versions from live data
async function loadOpenShiftVersions() {
    try {
        const response = await fetch(`${API_BASE}/live/openshift-versions?channel=stable-4.20`);
        const data = await response.json();
        
        if (data.success && data.data) {
            const versionSelect = document.getElementById('ocp-release-select');
            if (versionSelect) {
                // Clear and repopulate select dropdown
                versionSelect.innerHTML = '';
                
                // Add versions from live data
                const versions = Array.isArray(data.data) ? data.data : Object.keys(data.data);
                
                // Sort versions in descending order (newest first)
                const sortedVersions = versions.sort((a, b) => {
                    const versionA = typeof a === 'string' ? a : a.version;
                    const versionB = typeof b === 'string' ? b : b.version;
                    return versionB.localeCompare(versionA, undefined, { numeric: true });
                });
                
                sortedVersions.forEach(versionInfo => {
                    const version = typeof versionInfo === 'string' ? versionInfo : versionInfo.version;
                    const option = document.createElement('option');
                    option.value = version;
                    option.textContent = version;
                    versionSelect.appendChild(option);
                });
                
                // Add "Custom" option at the end
                const customOption = document.createElement('option');
                customOption.value = 'custom';
                customOption.textContent = '── Custom (Enter Manually) ──';
                versionSelect.appendChild(customOption);
                
                // Set default to first version (latest)
                if (sortedVersions.length > 0) {
                    const firstVersion = typeof sortedVersions[0] === 'string' ? sortedVersions[0] : sortedVersions[0].version;
                    versionSelect.value = firstVersion;
                }
                
                console.log(`Loaded ${versions.length} OpenShift versions from ${data.source}`);
                
                // Show data source indicator
                const openshiftTab = document.getElementById('openshift-mirror');
                if (openshiftTab) {
                    let indicator = openshiftTab.querySelector('.openshift-data-source-indicator');
                    if (!indicator) {
                        indicator = document.createElement('div');
                        indicator.className = 'openshift-data-source-indicator';
                        indicator.style.cssText = 'text-align: right; padding: 10px; font-size: 0.85rem;';
                        const form = openshiftTab.querySelector('form');
                        if (form) {
                            form.insertBefore(indicator, form.firstChild);
                        }
                    }
                    
                    const sourceColor = data.source === 'live' ? 'var(--success-color)' : 'var(--info-color)';
                    const sourceIcon = data.source === 'live' ? 'fa-cloud' : 'fa-database';
                    indicator.innerHTML = `<span style="color: ${sourceColor};"><i class="fas ${sourceIcon}"></i> ${data.source === 'live' ? 'Live' : 'Cached'} OpenShift versions (${versions.length} available)</span>`;
                }
            }
        }
    } catch (error) {
        console.error('Failed to load OpenShift versions:', error);
        // Fallback to hardcoded versions in select dropdown
        const versionSelect = document.getElementById('ocp-release-select');
        if (versionSelect && versionSelect.options.length <= 1) {
            versionSelect.innerHTML = '';
            const fallbackVersions = ['4.20.0', '4.19.0', '4.18.0', '4.17.0', '4.16.0', '4.15.56', '4.14.42'];
            fallbackVersions.forEach(version => {
                const option = document.createElement('option');
                option.value = version;
                option.textContent = version;
                versionSelect.appendChild(option);
            });
            
            // Add "Custom" option
            const customOption = document.createElement('option');
            customOption.value = 'custom';
            customOption.textContent = '── Custom (Enter Manually) ──';
            versionSelect.appendChild(customOption);
            
            versionSelect.value = fallbackVersions[0];
        }
    }
}

// Load Red Hat operators from live data
async function loadRedHatOperators() {
    try {
        const response = await fetch(`${API_BASE}/live/redhat-operators`);
        const data = await response.json();
        
        if (data.success && data.operators) {
            const operatorSelect = document.getElementById('operator-packages');
            if (operatorSelect) {
                // Clear and repopulate
                operatorSelect.innerHTML = '';
                
                data.operators.forEach(operator => {
                    const option = document.createElement('option');
                    option.value = operator.package;
                    option.textContent = operator.name;
                    option.dataset.catalog = operator.catalog;
                    option.dataset.description = operator.description || '';
                    operatorSelect.appendChild(option);
                });
                
                console.log(`Loaded ${data.operators.length} Red Hat operators from ${data.source}`);
                
                // Show data source indicator
                const operatorsTab = document.getElementById('operators-mirror');
                if (operatorsTab) {
                    let indicator = operatorsTab.querySelector('.data-source-indicator');
                    if (!indicator) {
                        indicator = document.createElement('div');
                        indicator.className = 'data-source-indicator';
                        indicator.style.cssText = 'text-align: right; padding: 10px; font-size: 0.85rem;';
                        operatorsTab.insertBefore(indicator, operatorsTab.firstChild);
                    }
                    
                    const sourceColor = data.source === 'live' ? 'var(--success-color)' : 'var(--info-color)';
                    const sourceIcon = data.source === 'live' ? 'fa-cloud' : 'fa-database';
                    indicator.innerHTML = `<span style="color: ${sourceColor};"><i class="fas ${sourceIcon}"></i> ${data.source === 'live' ? 'Live' : 'Cached'} operator catalog</span>`;
                }
            }
        }
    } catch (error) {
        console.error('Failed to load Red Hat operators:', error);
    }
}


// Update mirror type visibility
function updateMirrorType() {
    const mirrorType = document.querySelector('input[name="mirror_type"]:checked').value;
    const filesystemRow = document.getElementById('filesystem-path-row');
    const removableMediaPath = document.getElementById('removable-media-path');
    
    if (mirrorType === 'filesystem') {
        filesystemRow.style.display = 'flex';
        removableMediaPath.required = true;
    } else {
        filesystemRow.style.display = 'none';
        removableMediaPath.required = false;
    }
}

// Toggle advanced options
function toggleAdvancedOptions() {
    const advancedOptions = document.getElementById('advanced-options');
    const toggleText = document.getElementById('advanced-toggle-text');
    
    if (advancedOptions.style.display === 'none') {
        advancedOptions.style.display = 'block';
        toggleText.textContent = 'Hide Advanced Options';
    } else {
        advancedOptions.style.display = 'none';
        toggleText.textContent = 'Show Advanced Options';
    }
}

// Load preset configurations
function loadPreset(presetType) {
    const form = document.getElementById('openshift-form');
    
    switch(presetType) {
        case 'latest':
            form.ocp_release.value = '4.15.56';
            form.architecture.value = 'x86_64';
            document.getElementById('include-operators').checked = false;
            document.getElementById('include-samples').checked = false;
            showToast('Loaded latest stable release preset', 'info');
            break;
        case 'lts':
            form.ocp_release.value = '4.14.42';
            form.architecture.value = 'x86_64';
            document.getElementById('include-operators').checked = false;
            document.getElementById('include-samples').checked = false;
            showToast('Loaded LTS version preset', 'info');
            break;
        case 'minimal':
            document.getElementById('include-operators').checked = false;
            document.getElementById('include-samples').checked = false;
            document.getElementById('skip-verification').value = 'false';
            showToast('Loaded minimal mirror preset', 'info');
            break;
        case 'full':
            document.getElementById('include-operators').checked = true;
            document.getElementById('include-samples').checked = true;
            document.getElementById('skip-verification').value = 'false';
            showToast('Loaded full mirror preset', 'info');
            break;
    }
}

// Estimate mirror size
async function estimateSize() {
    const form = document.getElementById('openshift-form');
    const includeOperators = document.getElementById('include-operators').checked;
    const includeSamples = document.getElementById('include-samples').checked;
    const architecture = form.architecture.value;
    
    let estimatedSize = 10; // Base size in GB
    
    if (includeOperators) estimatedSize += 12;
    if (includeSamples) estimatedSize += 8;
    if (architecture === 'multi') estimatedSize *= 3;
    
    const modal = document.getElementById('download-details-modal');
    const content = document.getElementById('download-details-content');
    
    modal.classList.add('active');
    content.innerHTML = `
        <h3><i class="fas fa-calculator"></i> Estimated Mirror Size</h3>
        <div class="info-box">
            <p><strong>Release:</strong> ${form.ocp_release.value}</p>
            <p><strong>Architecture:</strong> ${architecture}</p>
            <p><strong>Include Operators:</strong> ${includeOperators ? 'Yes' : 'No'}</p>
            <p><strong>Include Samples:</strong> ${includeSamples ? 'Yes' : 'No'}</p>
            <hr style="margin: 15px 0;">
            <p style="font-size: 1.2rem;"><strong>Estimated Size:</strong> <span style="color: var(--primary-color);">~${estimatedSize} GB</span></p>
            <p style="margin-top: 10px; font-size: 0.9rem; color: var(--text-secondary);">
                <i class="fas fa-info-circle"></i> This is an approximate estimate. Actual size may vary.
            </p>
        </div>
    `;
}

// Start OpenShift Mirror
async function startOpenShiftMirror(event) {
    event.preventDefault();
    
    const form = event.target;
    const mirrorType = document.querySelector('input[name="mirror_type"]:checked').value;
    
    const formData = {
        ocp_release: form.ocp_release.value,
        architecture: form.architecture.value,
        local_registry: form.local_registry.value,
        local_repository: form.local_repository.value,
        removable_media_path: form.removable_media_path.value,
        local_secret_json: form.local_secret_json.value,
        dry_run: form.dry_run.checked,
        print_idms: form.print_idms.checked,
        generate_icsp: form.generate_icsp.checked,
        mirror_type: mirrorType,
        // Advanced options
        max_per_registry: form.max_per_registry.value || 6,
        continue_on_error: form.continue_on_error.value === 'true',
        skip_verification: form.skip_verification.value === 'true',
        filter_by_os: form.filter_by_os.value || '',
        include_operators: form.include_operators.checked,
        include_samples: form.include_samples.checked
    };
    
    // Validate required fields
    if (!formData.ocp_release || !formData.local_registry || !formData.local_repository ||
        !formData.removable_media_path || !formData.local_secret_json) {
        showToast('Please fill in all required fields', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/openshift/mirror`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast(`OpenShift mirror started: ${formData.ocp_release}`, 'success');
            
            // Wrap UI updates in try-catch to prevent errors from showing error toast
            try {
                showTab('active-downloads');
                loadDownloads();
            } catch (uiError) {
                // Log UI update errors but don't show error toast since mirror started successfully
                console.error('UI update error after successful mirror start:', uiError);
            }
        } else {
            showToast(data.error || 'Failed to start OpenShift mirror', 'error');
        }
    } catch (error) {
        showToast('Failed to start OpenShift mirror', 'error');
        console.error(error);
    }
}

// Verify OCP Images
async function verifyOCPImages() {
    const form = document.getElementById('openshift-form');
    const formData = {
        ocp_release: form.ocp_release.value,
        architecture: form.architecture.value,
        local_registry: form.local_registry.value,
        local_repository: form.local_repository.value,
        local_secret_json: form.local_secret_json.value,
        dry_run: true,
        print_idms: form.print_idms.checked
    };
    
    // Validate required fields
    if (!formData.ocp_release || !formData.local_registry || !formData.local_repository ||
        !formData.local_secret_json) {
        showToast('Please fill in required fields for verification', 'error');
        return;
    }
    
    try {
        showToast('Starting image verification...', 'info');
        
        const response = await fetch(`${API_BASE}/openshift/verify`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast('Image verification completed successfully', 'success');
            
            // Show verification results in a modal
            const modal = document.getElementById('download-details-modal');
            const content = document.getElementById('download-details-content');
            
            modal.classList.add('active');
            content.innerHTML = `
                <h3><i class="fas fa-check-circle"></i> OpenShift Image Verification Results</h3>
                <div class="info-box">
                    <p><strong>Release:</strong> ${formData.ocp_release}</p>
                    <p><strong>Architecture:</strong> ${formData.architecture}</p>
                    <p><strong>Status:</strong> <span style="color: var(--success-color);">Verified</span></p>
                </div>
                ${data.output ? `
                    <h3 class="mt-20"><i class="fas fa-terminal"></i> Verification Output</h3>
                    <div class="code-block">${data.output}</div>
                ` : ''}
                ${data.idms_instructions && formData.print_idms ? `
                    <h3 class="mt-20"><i class="fas fa-cog"></i> IDMS Instructions</h3>
                    <div class="code-block">${data.idms_instructions}</div>
                ` : ''}
            `;
        } else {
            showToast(data.error || 'Image verification failed', 'error');
        }
    } catch (error) {
        showToast('Failed to verify images', 'error');
        console.error(error);
    }
}

// Reset OpenShift Form
function resetOpenShiftForm() {
    const form = document.getElementById('openshift-form');
    if (form) {
        // Reset to default values
        form.ocp_release.value = '4.15.56';
        form.architecture.value = 'x86_64';
        form.local_registry.value = 'registry.example.com:5000';
        form.local_repository.value = 'ocp4/openshift4';
        form.removable_media_path.value = '/opt/ocp15';
        form.local_secret_json.value = '/root/.docker/config.json';
        form.dry_run.checked = false;
        form.print_idms.checked = false;
        
        // Reset generate_icsp if it exists
        const generateIcsp = document.getElementById('generate-icsp');
        if (generateIcsp) generateIcsp.checked = false;
        
        // Reset mirror type
        const filesystemRadio = document.querySelector('input[name="mirror_type"][value="filesystem"]');
        if (filesystemRadio) {
            filesystemRadio.checked = true;
            updateMirrorType();
        }
        
        // Reset advanced options
        const maxPerRegistry = document.getElementById('max-per-registry');
        const continueOnError = document.getElementById('continue-on-error');
        const skipVerification = document.getElementById('skip-verification');
        const filterByOs = document.getElementById('filter-by-os');
        const includeOperators = document.getElementById('include-operators');
        const includeSamples = document.getElementById('include-samples');
        
        if (maxPerRegistry) maxPerRegistry.value = '6';
        if (continueOnError) continueOnError.value = 'false';
        if (skipVerification) skipVerification.value = 'false';
        if (filterByOs) filterByOs.value = '';
        if (includeOperators) includeOperators.checked = false;
        if (includeSamples) includeSamples.checked = false;
        
        // Hide advanced options
        const advancedOptions = document.getElementById('advanced-options');
        const advancedToggleText = document.getElementById('advanced-toggle-text');
        if (advancedOptions) advancedOptions.style.display = 'none';
        if (advancedToggleText) advancedToggleText.textContent = 'Show Advanced Options';
        
        showToast('Form reset to default values', 'info');
    }
}

// Initialize OpenShift tab on load
document.addEventListener('DOMContentLoaded', () => {
    // Load live data for OpenShift versions and Red Hat operators
    loadOpenShiftVersions();
    loadRedHatOperators();
    
    // Set up mirror type change handler
    const mirrorTypeRadios = document.querySelectorAll('input[name="mirror_type"]');
    if (mirrorTypeRadios.length > 0) {
        mirrorTypeRadios.forEach(radio => {
            radio.addEventListener('change', updateMirrorType);
        });
        
        // Initialize mirror type visibility
        updateMirrorType();
    }
});
// Red Hat Operators Functions

// Initialize operators list on page load
document.addEventListener('DOMContentLoaded', function() {
    const container = document.getElementById('operators-list-container');
    if (container && container.children.length === 0) {
        addOperatorEntry();
    }
});

// Update operator mirror type visibility
function updateOperatorMirrorType() {
    const mirrorType = document.querySelector('input[name="operator_mirror_type"]:checked')?.value;
    const targetRegistrySection = document.getElementById('operator-target-registry-section');
    
    if (mirrorType === 'registry') {
        targetRegistrySection.style.display = 'block';
    } else {
        targetRegistrySection.style.display = 'none';
    }
}

// Add operator entry for specific operators
let operatorEntryCounter = 0;
function addOperatorEntry() {
    const container = document.getElementById('operators-list-container');
    if (!container) return;
    
    const entryId = `operator-entry-${operatorEntryCounter++}`;
    const entryDiv = document.createElement('div');
    entryDiv.id = entryId;
    entryDiv.className = 'operator-entry';
    entryDiv.style.cssText = 'display: grid; grid-template-columns: 1fr 1fr auto; gap: 10px; margin-bottom: 10px; padding: 10px; border: 1px solid #ddd; border-radius: 5px; background: #f9f9f9;';
    
    entryDiv.innerHTML = `
        <div>
            <input type="text" class="operator-name" placeholder="Operator name (e.g., openshift-gitops-operator)"
                   style="width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px;">
            <small style="display: block; margin-top: 5px; color: #666;">Package name</small>
        </div>
        <div>
            <input type="text" class="operator-channel" placeholder="Channel (e.g., stable)"
                   style="width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px;">
            <small style="display: block; margin-top: 5px; color: #666;">Optional channel</small>
        </div>
        <div style="display: flex; align-items: center;">
            <button type="button" class="btn btn-danger" onclick="removeOperatorEntry('${entryId}')"
                    style="padding: 8px 12px; background: #dc3545; color: white; border: none; border-radius: 4px; cursor: pointer;">
                <i class="fas fa-trash"></i>
            </button>
        </div>
    `;
    
    container.appendChild(entryDiv);
}

// Remove operator entry
function removeOperatorEntry(entryId) {
    const entry = document.getElementById(entryId);
    if (entry) {
        entry.remove();
    }
    
    // Ensure at least one entry remains
    const container = document.getElementById('operators-list-container');
    if (container && container.children.length === 0) {
        addOperatorEntry();
    }
}

// Start Operators Mirror
async function startOperatorsMirror(event) {
    event.preventDefault();
    
    const form = event.target;
    
    // Get operators from individual entries
    const container = document.getElementById('operators-list-container');
    if (!container || container.children.length === 0) {
        showToast('Please add at least one operator', 'error');
        return;
    }
    
    const operatorEntries = container.querySelectorAll('.operator-entry');
    const operators = [];
    
    operatorEntries.forEach(entry => {
        const nameInput = entry.querySelector('.operator-name');
        const channelInput = entry.querySelector('.operator-channel');
        const name = nameInput?.value.trim();
        const channel = channelInput?.value.trim();
        
        if (name) {
            operators.push({
                name: name,
                channel: channel || ''
            });
        }
    });
    
    if (operators.length === 0) {
        showToast('Please enter at least one operator name', 'error');
        return;
    }
    
    // Get mirror type and target registry
    const mirrorType = document.querySelector('input[name="operator_mirror_type"]:checked')?.value || 'filesystem';
    const targetRegistry = document.getElementById('operator-target-registry')?.value.trim() || '';
    
    // Validate target registry if direct to registry is selected
    if (mirrorType === 'registry' && !targetRegistry) {
        showToast('Please enter target registry for direct mirroring', 'error');
        return;
    }
    
    const formData = {
        catalog_version: form.catalog_version.value,
        architecture: form.architecture.value,
        local_path: form.local_path.value,
        auth_file: form.auth_file.value,
        operators: operators,
        channels: [],
        include_ubi: form.include_ubi.checked,
        include_helm: form.include_helm.checked,
        mirror_type: mirrorType,
        target_registry: targetRegistry
    };
    
    try {
        const response = await fetch(`${API_BASE}/operators/mirror`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast(`Operators mirror started: ${operators.length} operator(s)`, 'success');
            
            // Wrap UI updates in try-catch to prevent errors from showing error toast
            try {
                showTab('active-downloads');
                loadDownloads();
            } catch (uiError) {
                // Log UI update errors but don't show error toast since mirror started successfully
                console.error('UI update error after successful mirror start:', uiError);
            }
        } else {
            showToast(data.error || 'Failed to start operators mirror', 'error');
        }
    } catch (error) {
        showToast('Failed to start operators mirror', 'error');
        console.error(error);
    }
}

// Generate ImageSetConfiguration and Commands
async function generateImageSetConfig() {
    const form = document.getElementById('operators-form');
    
    // Get operators from individual entries
    const container = document.getElementById('operators-list-container');
    if (!container || container.children.length === 0) {
        showToast('Please add at least one operator', 'error');
        return;
    }
    
    const operatorEntries = container.querySelectorAll('.operator-entry');
    const operators = [];
    
    operatorEntries.forEach(entry => {
        const nameInput = entry.querySelector('.operator-name');
        const channelInput = entry.querySelector('.operator-channel');
        const name = nameInput?.value.trim();
        const channel = channelInput?.value.trim();
        
        if (name) {
            operators.push({
                name: name,
                channel: channel || ''
            });
        }
    });
    
    if (operators.length === 0) {
        showToast('Please enter at least one operator name', 'error');
        return;
    }
    
    const catalogVersion = form.catalog_version.value;
    const architecture = form.architecture.value;
    const localPath = form.local_path.value;
    const authFile = form.auth_file.value;
    const targetRegistry = form.target_registry?.value || '';
    const includeUbi = form.include_ubi?.checked || false;
    const includeHelm = form.include_helm?.checked || false;
    
    if (!catalogVersion || !localPath || !authFile) {
        showToast('Please fill in all required fields', 'warning');
        return;
    }
    
    showToast('Generating configuration and commands...', 'info');
    
    try {
        const response = await fetch(`${API_BASE}/operators/generate-config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                catalog_version: catalogVersion,
                architecture: architecture,
                local_path: localPath,
                auth_file: authFile,
                target_registry: targetRegistry,
                operators: operators,
                channels: [],
                include_ubi: includeUbi,
                include_helm: includeHelm
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Display configuration and commands
            const previewDiv = document.getElementById('imageset-config-preview');
            const contentDiv = document.getElementById('imageset-config-content');
            
            contentDiv.innerHTML = `
                <div class="info-box" style="margin-bottom: 20px;">
                    <h4><i class="fas fa-info-circle"></i> Configuration Summary</h4>
                    <p><strong>Catalog Version:</strong> ${data.summary.catalog_version}</p>
                    <p><strong>Architecture:</strong> ${data.summary.architecture}</p>
                    <p><strong>Operators:</strong> ${data.summary.operators_count}</p>
                    <p><strong>Local Path:</strong> ${data.summary.local_path}</p>
                    <p><strong>Target Registry:</strong> ${data.summary.target_registry}</p>
                </div>
                
                <h4><i class="fas fa-file-code"></i> ImageSetConfiguration YAML</h4>
                <div class="code-block" style="white-space: pre-wrap; font-family: monospace; margin-bottom: 20px;">${data.config}</div>
                
                <h4><i class="fas fa-terminal"></i> 1. Mirror to File System</h4>
                <div class="code-block" style="white-space: pre-wrap; font-family: monospace; margin-bottom: 20px;">${data.commands.filesystem}</div>
                
                <h4><i class="fas fa-terminal"></i> 2. Mirror Directly to Registry</h4>
                <div class="code-block" style="white-space: pre-wrap; font-family: monospace; margin-bottom: 20px;">${data.commands.registry}</div>
                
                <h4><i class="fas fa-terminal"></i> 3. Retry with --ignore-history</h4>
                <div class="code-block" style="white-space: pre-wrap; font-family: monospace; margin-bottom: 20px;">${data.commands.retry}</div>
                
                ${data.commands.publish ? `
                <h4><i class="fas fa-terminal"></i> 4. Publish from File System to Registry</h4>
                <div class="code-block" style="white-space: pre-wrap; font-family: monospace; margin-bottom: 20px;">${data.commands.publish}</div>
                ` : ''}
                
                <div style="margin-top: 20px;">
                    <button class="btn btn-secondary btn-small" onclick="copyAllCommands()">
                        <i class="fas fa-copy"></i> Copy All Commands
                    </button>
                    <button class="btn btn-secondary btn-small" onclick="downloadImageSetConfig()">
                        <i class="fas fa-download"></i> Download YAML
                    </button>
                </div>
            `;
            
            previewDiv.style.display = 'block';
            
            // Store config and commands for copy/download
            window.currentImageSetConfig = data.config;
            window.currentCommands = data.commands;
            
            showToast('Configuration and commands generated successfully', 'success');
        } else {
            showToast(data.error || 'Failed to generate configuration', 'error');
        }
    } catch (error) {
        console.error('Error generating config:', error);
        showToast('Failed to generate configuration', 'error');
    }
}

// Copy all commands to clipboard
function copyAllCommands() {
    console.log('copyAllCommands called');
    console.log('window.currentCommands:', window.currentCommands);
    
    if (!window.currentCommands) {
        showToast('No commands available to copy. Please generate configuration first.', 'error');
        console.error('window.currentCommands is not set');
        return;
    }
    
    try {
        const allCommands = [
            '# ===== Mirror to File System =====',
            window.currentCommands.filesystem || '',
            window.currentCommands.registry ? '\n# ===== Mirror Directly to Registry =====' : '',
            window.currentCommands.registry || '',
            '\n# ===== Retry with --ignore-history =====',
            window.currentCommands.retry || '',
            window.currentCommands.publish ? '\n# ===== Publish from File System to Registry =====' : '',
            window.currentCommands.publish || ''
        ].filter(cmd => cmd && cmd.trim()).join('\n');
        
        console.log('Commands to copy length:', allCommands.length);
        console.log('Commands preview:', allCommands.substring(0, 100));
        
        if (!allCommands.trim()) {
            showToast('No commands available to copy', 'error');
            console.error('allCommands is empty after filtering');
            return;
        }
        
        // Check if clipboard API is available
        if (navigator.clipboard && navigator.clipboard.writeText) {
            console.log('Using navigator.clipboard.writeText');
            navigator.clipboard.writeText(allCommands).then(() => {
                console.log('Clipboard write successful');
                showToast('All commands copied to clipboard', 'success');
            }).catch(err => {
                console.error('Clipboard API failed:', err);
                fallbackCopy(allCommands);
            });
        } else {
            console.log('Clipboard API not available, using fallback');
            fallbackCopy(allCommands);
        }
    } catch (error) {
        console.error('Error in copyAllCommands:', error);
        showToast('Failed to copy commands: ' + error.message, 'error');
    }
}

// Fallback copy method
function fallbackCopy(text) {
    try {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.top = '0';
        textArea.style.left = '0';
        textArea.style.width = '2em';
        textArea.style.height = '2em';
        textArea.style.padding = '0';
        textArea.style.border = 'none';
        textArea.style.outline = 'none';
        textArea.style.boxShadow = 'none';
        textArea.style.background = 'transparent';
        
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        
        const successful = document.execCommand('copy');
        document.body.removeChild(textArea);
        
        if (successful) {
            console.log('Fallback copy successful');
            showToast('All commands copied to clipboard', 'success');
        } else {
            console.error('execCommand returned false');
            showToast('Failed to copy. Please copy manually from the page.', 'error');
        }
    } catch (err) {
        console.error('Fallback copy failed:', err);
        showToast('Failed to copy. Please copy manually from the page.', 'error');
    }
}

// Copy ImageSetConfiguration to clipboard
function copyImageSetConfig() {
    if (window.currentImageSetConfig) {
        navigator.clipboard.writeText(window.currentImageSetConfig).then(() => {
            showToast('Configuration copied to clipboard', 'success');
        }).catch(() => {
            showToast('Failed to copy to clipboard', 'error');
        });
    }
}

// Download ImageSetConfiguration as YAML file
function downloadImageSetConfig() {
    if (window.currentImageSetConfig) {
        const blob = new Blob([window.currentImageSetConfig], { type: 'text/yaml' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'imageset-config.yaml';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        showToast('Configuration downloaded', 'success');
    }
}

// Validate operator configuration
async function validateOperatorConfig() {
    const form = document.getElementById('operators-form');
    
    // Collect operators from individual entries
    const operatorEntries = document.querySelectorAll('.operator-entry');
    if (operatorEntries.length === 0) {
        showToast('Please add at least one operator for validation', 'warning');
        return;
    }
    
    const operators = [];
    for (const entry of operatorEntries) {
        const nameInput = entry.querySelector('.operator-name');
        const operatorName = nameInput?.value.trim();
        
        if (!operatorName) {
            showToast('Please fill in all operator names', 'warning');
            return;
        }
        
        operators.push(operatorName);
    }
    
    if (operators.length === 0) {
        showToast('No operators to validate', 'warning');
        return;
    }
    
    showToast('Validating operator configuration...', 'info');
    
    try {
        const response = await fetch(`${API_BASE}/operators/validate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                catalog_version: form.catalog_version.value,
                operators: operators
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast(`Validation successful: ${data.valid_count || 0} operator(s) found`, 'success');
        } else {
            showToast(data.error || 'Validation failed', 'error');
        }
    } catch (error) {
        showToast('Failed to validate configuration', 'error');
        console.error(error);
    }
}

// Reset operators form
function resetOperatorsForm() {
    const form = document.getElementById('operators-form');
    if (form) {
        form.reset();
        document.getElementById('specific-operators-section').style.display = 'none';
        document.getElementById('preset-collection-section').style.display = 'none';
        document.getElementById('imageset-config-preview').style.display = 'none';
        showToast('Form reset to default values', 'info');
    }
}

// Initialize operator selection on load
document.addEventListener('DOMContentLoaded', () => {
    const operatorSelectionRadios = document.querySelectorAll('input[name="operator_selection"]');
    if (operatorSelectionRadios.length > 0) {
        operatorSelectionRadios.forEach(radio => {
            radio.addEventListener('change', updateOperatorSelection);
        });
    }
});


// Made with Bob
