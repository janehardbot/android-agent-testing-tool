// AATT Dashboard — vanilla JS

async function refreshDevices() {
    const res = await fetch('/api/devices');
    const data = await res.json();
    const el = document.getElementById('devices-list');
    if (data.devices && data.devices.length > 0) {
        el.innerHTML = '<ul>' + data.devices.map(d => `<li class="device">${d}</li>`).join('') + '</ul>';
    } else {
        el.innerHTML = '<p class="muted">No devices connected</p>';
        if (data.error) el.innerHTML += `<p class="muted">Error: ${data.error}</p>`;
    }
}

async function loadSuites() {
    const res = await fetch('/api/suites');
    const data = await res.json();
    const el = document.getElementById('suites-list');
    if (data.suites && data.suites.length > 0) {
        el.innerHTML = data.suites.map(s =>
            `<div class="suite-item">
                <span>${s.name}</span>
                <button class="btn btn-primary" onclick="triggerSuite('${s.path}')">Run</button>
            </div>`
        ).join('');
    } else {
        el.innerHTML = '<p class="muted">No suites found</p>';
    }
}

async function triggerSuite(suitePath) {
    const res = await fetch('/api/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ suite_path: suitePath })
    });
    const result = await res.json();
    if (result.run_id) {
        alert(`Run ${result.run_id}: ${result.status.toUpperCase()} (${result.passed} passed, ${result.failed} failed)`);
        refreshRuns();
    } else {
        alert('Error: ' + (result.detail || JSON.stringify(result)));
    }
}

async function refreshRuns() {
    const res = await fetch('/api/runs');
    const data = await res.json();
    const el = document.getElementById('runs-list');
    if (data.runs && data.runs.length > 0) {
        let html = `<table><tr><th>Run ID</th><th>Suite</th><th>Status</th><th>Passed</th><th>Failed</th><th>Duration</th><th>Actions</th></tr>`;
        data.runs.forEach(r => {
            html += `<tr>
                <td><code>${r.run_id}</code></td>
                <td>${r.suite_name}</td>
                <td class="status-${r.status}">${r.status}</td>
                <td>${r.passed}</td>
                <td>${r.failed}</td>
                <td>${Math.round(r.duration_ms)}ms</td>
                <td><a href="/api/runs/${r.run_id}/report" target="_blank" class="btn btn-small">Report</a></td>
            </tr>`;
        });
        html += '</table>';
        el.innerHTML = html;
    } else {
        el.innerHTML = '<p class="muted">No runs yet</p>';
    }
}

// Auto-load suites on page load
document.addEventListener('DOMContentLoaded', loadSuites);
