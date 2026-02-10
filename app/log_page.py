"""Log viewer HTML page."""

LOG_HTML = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MeetRecording Logs</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'SF Mono', 'Consolas', 'Monaco', monospace; background: #0d1117; color: #c9d1d9; font-size: 13px; }
  .header { background: #161b22; border-bottom: 1px solid #30363d; padding: 12px 20px; display: flex; align-items: center; gap: 16px; flex-wrap: wrap; position: sticky; top: 0; z-index: 10; }
  .header h1 { font-size: 16px; color: #58a6ff; white-space: nowrap; }
  .controls { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  .controls select, .controls input, .controls button {
    background: #21262d; border: 1px solid #30363d; color: #c9d1d9; padding: 5px 10px;
    border-radius: 6px; font-size: 12px; font-family: inherit;
  }
  .controls input { width: 200px; }
  .controls button { cursor: pointer; }
  .controls button:hover { background: #30363d; }
  .btn-danger { color: #f85149 !important; border-color: #f85149 !important; }
  .btn-primary { color: #58a6ff !important; border-color: #58a6ff !important; }
  .stats { color: #8b949e; font-size: 12px; margin-left: auto; white-space: nowrap; }
  .auto-label { color: #8b949e; font-size: 12px; display: flex; align-items: center; gap: 4px; }
  .auto-label input { width: auto; }
  .log-container { padding: 8px 0; }
  .log-entry { padding: 2px 20px; line-height: 1.6; white-space: pre-wrap; word-break: break-all; }
  .log-entry:hover { background: #161b22; }
  .ts { color: #8b949e; }
  .lvl-DEBUG { color: #8b949e; }
  .lvl-INFO { color: #3fb950; }
  .lvl-WARNING { color: #d29922; }
  .lvl-ERROR { color: #f85149; font-weight: bold; }
  .lvl-CRITICAL { color: #ff7b72; font-weight: bold; background: #3d1214; }
  .tag { color: #d2a8ff; }
  .empty { text-align: center; padding: 60px; color: #484f58; }
</style>
</head>
<body>

<div class="header">
  <h1>📋 Logs</h1>
  <div class="controls">
    <select id="level">
      <option value="">All Levels</option>
      <option value="DEBUG">DEBUG</option>
      <option value="INFO">INFO</option>
      <option value="WARNING">WARNING</option>
      <option value="ERROR">ERROR</option>
    </select>
    <input type="text" id="keyword" placeholder="Filter keyword..." />
    <button onclick="fetchLogs()" class="btn-primary">🔍 Search</button>
    <button onclick="clearLogs()" class="btn-danger">🗑 Clear</button>
  </div>
  <label class="auto-label">
    <input type="checkbox" id="autoRefresh" checked> Auto (3s)
  </label>
  <div class="stats" id="stats"></div>
</div>

<div class="log-container" id="logs">
  <div class="empty">Loading...</div>
</div>

<script>
let timer = null;

function escapeHtml(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function highlightTags(msg) {
  return msg.replace(/\\[(\\w+)\\]/g, '<span class="tag">[$1]</span>');
}

async function fetchLogs() {
  const level = document.getElementById('level').value;
  const keyword = document.getElementById('keyword').value;
  const params = new URLSearchParams();
  if (level) params.set('level', level);
  if (keyword) params.set('keyword', keyword);

  try {
    const resp = await fetch('/logs/api?' + params.toString());
    const data = await resp.json();

    const container = document.getElementById('logs');
    const stats = document.getElementById('stats');
    stats.textContent = `${data.showing} / ${data.total} entries`;

    if (data.logs.length === 0) {
      container.innerHTML = '<div class="empty">No logs found</div>';
      return;
    }

    let html = '';
    for (const log of data.logs) {
      const escaped = escapeHtml(log.message);
      const highlighted = highlightTags(escaped);
      html += `<div class="log-entry"><span class="ts">${log.timestamp}</span> <span class="lvl-${log.level}">${log.level.padEnd(8)}</span> ${highlighted}</div>`;
    }
    container.innerHTML = html;
  } catch (e) {
    document.getElementById('logs').innerHTML = '<div class="empty">Failed to fetch logs: ' + e.message + '</div>';
  }
}

function setupAutoRefresh() {
  if (timer) clearInterval(timer);
  const checkbox = document.getElementById('autoRefresh');
  if (checkbox.checked) {
    timer = setInterval(fetchLogs, 3000);
  }
}

async function clearLogs() {
  if (!confirm('Clear all logs?')) return;
  await fetch('/logs/clear', { method: 'POST' });
  fetchLogs();
}

document.getElementById('autoRefresh').addEventListener('change', setupAutoRefresh);
document.getElementById('keyword').addEventListener('keydown', (e) => { if (e.key === 'Enter') fetchLogs(); });

fetchLogs();
setupAutoRefresh();
</script>

</body>
</html>"""
