# CP4I Downloader API Endpoints

## Log Access Endpoints

### 1. Get Logs (Static)
**Endpoint:** `GET /api/logs/<name>`

**Query Parameters:**
- `home_dir` (optional): Home directory path (default: `/opt/cp4i`)
- `type` (optional): Log type - `download`, `mirror`, or `all` (default: `download`)
- `lines` (optional): Number of lines to return from end of file (tail)

**Response:**
```json
{
  "download_log": "log content...",
  "download_log_path": "/opt/cp4i/name/name-download.log",
  "mirror_log": "log content...",
  "mirror_log_path": "/opt/cp4i/name/name-mirror.log"
}
```

**Examples:**
```bash
# Get download log
curl "http://localhost:5000/api/logs/pn-7.3.2?type=download"

# Get mirror log (shows download progress)
curl "http://localhost:5000/api/logs/pn-7.3.2?type=mirror"

# Get both logs
curl "http://localhost:5000/api/logs/pn-7.3.2?type=all"

# Get last 100 lines of mirror log
curl "http://localhost:5000/api/logs/pn-7.3.2?type=mirror&lines=100"
```

### 2. Stream Logs (Real-time)
**Endpoint:** `GET /api/logs/<name>/stream`

**Query Parameters:**
- `home_dir` (optional): Home directory path (default: `/opt/cp4i`)
- `type` (optional): Log type - `download` or `mirror` (default: `mirror`)

**Response:** Server-Sent Events (SSE) stream

**Example:**
```javascript
// JavaScript example for UI
const eventSource = new EventSource('/api/logs/pn-7.3.2/stream?type=mirror');

eventSource.onmessage = function(event) {
  console.log('New log line:', event.data);
  // Append to UI log viewer
  document.getElementById('log-viewer').innerHTML += event.data + '\n';
};

eventSource.onerror = function(error) {
  console.error('Stream error:', error);
  eventSource.close();
};
```

### 3. Get Manifests
**Endpoint:** `GET /api/manifests/<name>`

**Query Parameters:**
- `home_dir` (optional): Home directory path (default: `/opt/cp4i`)
- `component` (required): Component name
- `version` (required): Component version

**Response:**
```json
{
  "mapping_file": "/opt/cp4i/.ibm-pak/data/mirror/component/version/images-mapping-to-filesystem.txt",
  "total_images": 150,
  "mappings": [
    {
      "source": "cp.icr.io/cp/...",
      "destination": "file://..."
    }
  ],
  "raw_content": "full file content..."
}
```

**Example:**
```bash
curl "http://localhost:5000/api/manifests/pn-7.3.2?component=ibm-integration-platform-navigator&version=7.3.2"
```

## Download Status Endpoint

### Get Download Status
**Endpoint:** `GET /api/downloads/<download_id>`

**Response includes:**
```json
{
  "id": "download-id",
  "component": "ibm-integration-platform-navigator",
  "version": "7.3.2",
  "name": "pn-7.3.2",
  "status": "running",
  "log_file": "/opt/cp4i/pn-7.3.2/pn-7.3.2-download.log",
  "mirror_log": "/opt/cp4i/pn-7.3.2/pn-7.3.2-mirror.log",
  "home_dir": "/opt/cp4i",
  "pid": 12345
}
```

## UI Integration Examples

### 1. Show Download Progress in Real-time

```javascript
function showDownloadProgress(downloadName) {
  const logViewer = document.getElementById('log-viewer');
  const eventSource = new EventSource(`/api/logs/${downloadName}/stream?type=mirror`);
  
  eventSource.onmessage = function(event) {
    const line = event.data;
    
    // Append to log viewer
    logViewer.innerHTML += line + '\n';
    logViewer.scrollTop = logViewer.scrollHeight;
    
    // Parse progress information
    if (line.includes('Copying blob')) {
      // Update progress bar
      updateProgressBar(line);
    }
    
    if (line.includes('Mirroring completed')) {
      // Download finished
      eventSource.close();
      showCompletionMessage();
    }
  };
  
  eventSource.onerror = function() {
    console.error('Stream connection lost');
    eventSource.close();
  };
}
```

### 2. Preview Manifests Before Download

```javascript
async function previewManifests(name, component, version) {
  const response = await fetch(
    `/api/manifests/${name}?component=${component}&version=${version}`
  );
  
  const data = await response.json();
  
  console.log(`Total images to download: ${data.total_images}`);
  
  // Show image list in UI
  data.mappings.forEach(mapping => {
    console.log(`${mapping.source} -> ${mapping.destination}`);
  });
}
```

### 3. Poll for Log Updates (Alternative to SSE)

```javascript
async function pollLogs(downloadName) {
  let lastLines = 0;
  
  setInterval(async () => {
    const response = await fetch(
      `/api/logs/${downloadName}?type=mirror&lines=50`
    );
    
    const data = await response.json();
    
    if (data.mirror_log) {
      const lines = data.mirror_log.split('\n');
      if (lines.length > lastLines) {
        // New content available
        const newLines = lines.slice(lastLines);
        displayNewLines(newLines);
        lastLines = lines.length;
      }
    }
  }, 2000); // Poll every 2 seconds
}
```

## Log File Locations

After starting a download for component `name`:

1. **Main Application Log:** `/opt/cp4i/{name}/{name}-download.log`
   - Contains: Prerequisites checks, authentication, manifest generation
   
2. **Mirror Progress Log:** `/opt/cp4i/{name}/{name}-mirror.log`
   - Contains: Image download progress, blob copying, completion status
   
3. **Summary Report:** `/opt/cp4i/{name}-summary-report.txt`
   - Generated after download completes (success or failure)

## Monitoring Download Progress

The mirror log shows real-time progress:
```
info: Planning completed in 2.3s
sha256:abc123... file://...
Copying blob sha256:abc123...
Copying blob sha256:def456...
...
info: Mirroring completed in 45m23s
```

Monitor this log via:
- SSE stream: `/api/logs/{name}/stream?type=mirror`
- Polling: `/api/logs/{name}?type=mirror&lines=100`
- Direct file: `tail -f /opt/cp4i/{name}/{name}-mirror.log`