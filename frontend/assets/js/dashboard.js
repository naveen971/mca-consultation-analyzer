/**
 * Dashboard page logic — loads analysis results from sessionStorage
 * and renders charts, metrics, tables, and word clouds.
 */

document.addEventListener('DOMContentLoaded', () => {
    const rawData = sessionStorage.getItem('analysisResults');
    if (!rawData) {
        // Show empty state
        document.getElementById('empty-state').classList.remove('hidden');
        document.getElementById('dashboard').classList.add('hidden');
        return;
    }

    const data = JSON.parse(rawData);
    document.getElementById('empty-state').classList.add('hidden');
    document.getElementById('dashboard').classList.remove('hidden');

    // Subtitle
    const subtitle = document.getElementById('dashboard-subtitle');
    subtitle.textContent = `${data.filename || 'Analysis'} • ${new Date(data.timestamp).toLocaleString()}`;

    // Render all sections
    renderMetrics(data.sentiment);
    renderPieChart(data.sentiment);
    renderBarChart(data.sentiment);
    renderExecutiveSummary(data.summary);
    renderCommentsTable(data.sentiment, data.summary);

    // Word Cloud
    if (data.wordcloud || data.wordcloudBySentiment) {
        WordCloudManager.init(data.wordcloud, data.wordcloudBySentiment);
    } else {
        document.getElementById('wordcloud-section').classList.add('hidden');
    }

    // Export button
    document.getElementById('btn-export').addEventListener('click', () => exportResults(data));
});


// ── Metrics ──────────────────────────────────────────────────────────────
function renderMetrics(sentiment) {
    if (!sentiment || !sentiment.statistics) return;
    const s = sentiment.statistics;

    animateCounter('metric-total', s.total);
    animateCounter('metric-positive', s.positive_count, `${s.positive_pct}%`);
    animateCounter('metric-negative', s.negative_count, `${s.negative_pct}%`);
    animateCounter('metric-neutral', s.neutral_count, `${s.neutral_pct}%`);
}

function animateCounter(elementId, target, suffix = '') {
    const el = document.getElementById(elementId);
    let current = 0;
    const step = Math.max(1, Math.ceil(target / 30));
    const interval = setInterval(() => {
        current += step;
        if (current >= target) {
            current = target;
            clearInterval(interval);
        }
        el.textContent = current + (suffix ? ` (${suffix})` : '');
    }, 30);
}


// ── Pie Chart ────────────────────────────────────────────────────────────
function renderPieChart(sentiment) {
    if (!sentiment || !sentiment.statistics) return;
    const s = sentiment.statistics;
    const ctx = document.getElementById('sentiment-pie-chart').getContext('2d');

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Positive', 'Negative', 'Neutral'],
            datasets: [{
                data: [s.positive_count, s.negative_count, s.neutral_count],
                backgroundColor: [
                    'rgba(16, 185, 129, 0.85)',
                    'rgba(244, 63, 94, 0.85)',
                    'rgba(99, 102, 241, 0.85)',
                ],
                borderColor: [
                    'rgba(16, 185, 129, 1)',
                    'rgba(244, 63, 94, 1)',
                    'rgba(99, 102, 241, 1)',
                ],
                borderWidth: 2,
                hoverOffset: 8,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            cutout: '60%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#8b95a8',
                        padding: 16,
                        font: { family: 'Inter', size: 13 },
                        usePointStyle: true,
                        pointStyleWidth: 10,
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(15, 20, 36, 0.95)',
                    titleColor: '#e8ecf4',
                    bodyColor: '#8b95a8',
                    borderColor: 'rgba(255,255,255,0.1)',
                    borderWidth: 1,
                    padding: 12,
                    cornerRadius: 8,
                    titleFont: { family: 'Inter', weight: '600' },
                    bodyFont: { family: 'Inter' },
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const pct = ((context.parsed / total) * 100).toFixed(1);
                            return ` ${context.label}: ${context.parsed} (${pct}%)`;
                        }
                    }
                }
            }
        }
    });
}


// ── Bar Chart (by Section) ───────────────────────────────────────────────
function renderBarChart(sentiment) {
    if (!sentiment || !sentiment.results) return;

    // Group by section
    const sections = {};
    sentiment.results.forEach(r => {
        const sec = r.section || 'Unspecified';
        if (!sections[sec]) sections[sec] = { Positive: 0, Negative: 0, Neutral: 0 };
        sections[sec][r.sentiment]++;
    });

    const labels = Object.keys(sections);
    const posData = labels.map(l => sections[l].Positive);
    const negData = labels.map(l => sections[l].Negative);
    const neuData = labels.map(l => sections[l].Neutral);

    const ctx = document.getElementById('section-bar-chart').getContext('2d');

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels.map(l => l.length > 25 ? l.slice(0, 25) + '…' : l),
            datasets: [
                {
                    label: 'Positive',
                    data: posData,
                    backgroundColor: 'rgba(16, 185, 129, 0.75)',
                    borderColor: 'rgba(16, 185, 129, 1)',
                    borderWidth: 1,
                    borderRadius: 4,
                },
                {
                    label: 'Negative',
                    data: negData,
                    backgroundColor: 'rgba(244, 63, 94, 0.75)',
                    borderColor: 'rgba(244, 63, 94, 1)',
                    borderWidth: 1,
                    borderRadius: 4,
                },
                {
                    label: 'Neutral',
                    data: neuData,
                    backgroundColor: 'rgba(99, 102, 241, 0.75)',
                    borderColor: 'rgba(99, 102, 241, 1)',
                    borderWidth: 1,
                    borderRadius: 4,
                },
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            scales: {
                x: {
                    stacked: true,
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { color: '#8b95a8', font: { family: 'Inter', size: 11 } },
                },
                y: {
                    stacked: true,
                    beginAtZero: true,
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: {
                        color: '#8b95a8',
                        font: { family: 'Inter' },
                        stepSize: 1,
                    },
                }
            },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#8b95a8',
                        padding: 16,
                        font: { family: 'Inter', size: 12 },
                        usePointStyle: true,
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(15, 20, 36, 0.95)',
                    titleColor: '#e8ecf4',
                    bodyColor: '#8b95a8',
                    borderColor: 'rgba(255,255,255,0.1)',
                    borderWidth: 1,
                    padding: 12,
                    cornerRadius: 8,
                }
            }
        }
    });
}


// ── Executive Summary ────────────────────────────────────────────────────
function renderExecutiveSummary(summary) {
    const textEl = document.getElementById('executive-summary-text');
    if (summary && summary.executive_summary) {
        textEl.textContent = summary.executive_summary;
    } else {
        document.getElementById('summary-section').classList.add('hidden');
    }
}


// ── Comments Table ───────────────────────────────────────────────────────
let allRows = [];

function renderCommentsTable(sentiment, summary) {
    if (!sentiment || !sentiment.results) return;

    const tbody = document.getElementById('comments-tbody');
    const summaryMap = {};

    // Map summaries by index
    if (summary && summary.summaries) {
        summary.summaries.forEach((s, i) => {
            summaryMap[i] = s.summary;
        });
    }

    // Build rows
    allRows = sentiment.results.map((r, i) => ({
        index: i + 1,
        stakeholder: r.stakeholder_name || '—',
        section: r.section || '—',
        text: r.text,
        sentiment: r.sentiment,
        confidence: r.confidence,
        reasoning: r.reasoning || '',
        summary: summaryMap[i] || '',
    }));

    renderTableRows(allRows);

    // Search
    document.getElementById('search-input').addEventListener('input', (e) => {
        filterTable();
    });

    // Filter pills
    document.querySelectorAll('#filter-pills .filter-pill').forEach(pill => {
        pill.addEventListener('click', () => {
            document.querySelectorAll('#filter-pills .filter-pill').forEach(p =>
                p.classList.remove('active'));
            pill.classList.add('active');
            filterTable();
        });
    });
}

function filterTable() {
    const query = document.getElementById('search-input').value.toLowerCase();
    const activeFilter = document.querySelector('#filter-pills .filter-pill.active').dataset.filter;

    let filtered = allRows;

    if (activeFilter !== 'all') {
        filtered = filtered.filter(r => r.sentiment === activeFilter);
    }

    if (query) {
        filtered = filtered.filter(r =>
            r.text.toLowerCase().includes(query) ||
            r.stakeholder.toLowerCase().includes(query) ||
            r.section.toLowerCase().includes(query)
        );
    }

    renderTableRows(filtered);
}

function renderTableRows(rows) {
    const tbody = document.getElementById('comments-tbody');
    const info = document.getElementById('table-info');

    tbody.innerHTML = rows.map(r => `
        <tr>
            <td>${r.index}</td>
            <td>${escapeHtml(r.stakeholder)}</td>
            <td>${escapeHtml(r.section)}</td>
            <td class="comment-text" title="Click to see summary"
                onclick="toggleSummary(this, ${r.index})">
                ${escapeHtml(r.text.length > 120 ? r.text.slice(0, 120) + '…' : r.text)}
            </td>
            <td><span class="badge badge-${r.sentiment.toLowerCase()}">${r.sentiment}</span></td>
            <td>${(r.confidence * 100).toFixed(0)}%</td>
        </tr>
        <tr class="comment-summary" id="summary-row-${r.index}">
            <td colspan="6">
                <div style="margin-bottom: 8px;">
                    <strong style="color: var(--accent-blue);">Summary:</strong>
                    ${escapeHtml(r.summary || 'No summary available')}
                </div>
                <div style="font-size: 0.8rem; color: var(--text-muted);">
                    <strong>AI Reasoning:</strong> ${escapeHtml(r.reasoning)}
                </div>
                <div style="margin-top: 8px; font-size: 0.8rem; color: var(--text-muted);">
                    <strong>Full Comment:</strong> ${escapeHtml(r.text)}
                </div>
            </td>
        </tr>
    `).join('');

    info.textContent = `Showing ${rows.length} of ${allRows.length} comments`;
}

function toggleSummary(el, index) {
    const row = document.getElementById(`summary-row-${index}`);
    if (row) {
        row.classList.toggle('visible');
    }
}


// ── Export ────────────────────────────────────────────────────────────────
function exportResults(data) {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `econsult-analysis-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
}


// ── Utilities ────────────────────────────────────────────────────────────
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
